from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
import secrets
from typing import Optional

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from cart.services.reservation_service import ReservationService
from orders.models import (
    DigitalDelivery,
    Order,
    OrderItem,
    OrderPayment,
    SubOrder,
)
from store.models import Product
from vendors.models import VendorLedger


class OrderWorkflowService:
    SETTLEMENT_HOLD_DAYS = 14

    @classmethod
    def calculate_suborder_commission(
        cls,
        *,
        items_subtotal: Decimal,
        commission_rate: Decimal,
        discount_amount: Decimal = Decimal("0.00"),
    ) -> Decimal:
        """
        Calculate platform commission:
        Commissionable Base = max(0.00, items_subtotal - discount_amount)
        Commission = quantize(Base * rate / 100, 0.01)
        """
        base = max(Decimal("0.00"), items_subtotal - discount_amount)
        commission = (base * (commission_rate / Decimal("100.00"))).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        return commission

    @classmethod
    def confirm_online_payment(
        cls,
        order_payment: OrderPayment,
        gateway_payment_id: str,
        raw_response: dict = None,
    ) -> Order:
        """
        Transition order and suborders to processing upon verified online payment.
        Permanently consumes inventory reservations, creates digital delivery tokens,
        and posts holding ledger credits for vendors.
        Idempotent: safe to invoke on duplicate gateway callbacks.
        """
        with transaction.atomic():
            # Lock payment and master order
            payment = OrderPayment.objects.select_for_update().get(id=order_payment.id)
            order = Order.objects.select_for_update().get(id=payment.order_id)

            if payment.status == OrderPayment.STATUS_SUCCESSFUL:
                # Already processed idempotently
                return order

            payment.status = OrderPayment.STATUS_SUCCESSFUL
            payment.gateway_payment_id = gateway_payment_id
            payment.raw_response = raw_response or {}
            payment.save(update_fields=["status", "gateway_payment_id", "raw_response", "updated_at"])

            order.online_payment_status = Order.ONLINE_STATUS_PAID
            order.order_status = Order.ORDER_STATUS_PROCESSING
            order.save(update_fields=["online_payment_status", "order_status", "updated_at"])

            # 1. Permanently consume stock reservations
            ReservationService.consume_reservations_for_order(order)

            # 2. Process suborders and vendor ledgers
            unlock_timestamp = timezone.now() + timedelta(days=cls.SETTLEMENT_HOLD_DAYS)
            suborders = order.suborders.select_related("vendor").prefetch_related("items", "items__variant", "items__variant__product")

            for suborder in suborders:
                suborder.fulfillment_status = SubOrder.FULFILLMENT_PROCESSING
                suborder.settlement_hold_until = unlock_timestamp
                suborder.seller_payable_status = SubOrder.PAYABLE_HOLDING
                suborder.save(update_fields=["fulfillment_status", "settlement_hold_until", "seller_payable_status", "updated_at"])

                # Vendor ledger entries for 3rd party sellers
                if suborder.vendor:
                    # Credit gross merchandise sale
                    VendorLedger.objects.get_or_create(
                        idempotency_key=f"ledger-sale-{suborder.suborder_number}",
                        defaults={
                            "vendor": suborder.vendor,
                            "suborder": suborder,
                            "entry_type": VendorLedger.ENTRY_CREDIT_ORDER_SALE,
                            "amount": suborder.items_subtotal,
                            "currency": order.currency,
                            "is_settled": False,
                            "unlocks_at": unlock_timestamp,
                            "reference_id": f"ORD-PAY-{payment.id}",
                            "notes": f"Gross sale for suborder {suborder.suborder_number}",
                        },
                    )

                    # Debit platform commission
                    if suborder.platform_commission > Decimal("0.00"):
                        VendorLedger.objects.get_or_create(
                            idempotency_key=f"ledger-comm-{suborder.suborder_number}",
                            defaults={
                                "vendor": suborder.vendor,
                                "suborder": suborder,
                                "entry_type": VendorLedger.ENTRY_DEBIT_COMMISSION,
                                "amount": -suborder.platform_commission,
                                "currency": order.currency,
                                "is_settled": False,
                                "unlocks_at": unlock_timestamp,
                                "reference_id": f"ORD-PAY-{payment.id}",
                                "notes": f"Platform commission deduction ({suborder.vendor.commission_rate}%)",
                            },
                        )

                # Generate digital delivery access tokens for digital products
                for item in suborder.items.all():
                    if item.variant.product.product_type == Product.TYPE_DIGITAL:
                        asset = getattr(item.variant.product, "digital_asset", None)
                        if asset:
                            token = secrets.token_hex(32)
                            DigitalDelivery.objects.get_or_create(
                                order_item=item,
                                defaults={
                                    "user": order.user,
                                    "digital_asset": asset,
                                    "download_token": token,
                                    "expires_at": timezone.now() + timedelta(days=30),
                                    "max_downloads": 5,
                                },
                            )

            return order

    @classmethod
    def confirm_cod_order(cls, order: Order) -> Order:
        """
        Transition COD order and suborders to processing.
        Stock reservations are consumed permanently.
        NOTE: Vendor ledger credit is NOT posted at this stage, because
        cash has not yet been collected or remitted by the courier.
        """
        with transaction.atomic():
            ord_obj = Order.objects.select_for_update().get(id=order.id)

            if ord_obj.payment_method != Order.PAYMENT_METHOD_COD:
                raise ValidationError("Only Cash on Delivery orders can be confirmed via confirm_cod_order.")

            if ord_obj.order_status != Order.ORDER_STATUS_PENDING:
                return ord_obj

            ord_obj.order_status = Order.ORDER_STATUS_PROCESSING
            ord_obj.cod_collection_status = Order.COD_STATUS_PENDING_DELIVERY
            ord_obj.save(update_fields=["order_status", "cod_collection_status", "updated_at"])

            # Consume physical stock
            ReservationService.consume_reservations_for_order(ord_obj)

            for suborder in ord_obj.suborders.all():
                suborder.fulfillment_status = SubOrder.FULFILLMENT_PROCESSING
                suborder.save(update_fields=["fulfillment_status", "updated_at"])

            return ord_obj

    @classmethod
    def update_suborder_fulfillment(
        cls,
        suborder: SubOrder,
        new_status: str,
        carrier: str = "",
        tracking_number: str = "",
    ) -> SubOrder:
        """
        Transitions suborder through fulfillment states:
        processing -> shipped -> delivered.
        Updates master order status when all suborders reach delivered.
        """
        with transaction.atomic():
            sub = SubOrder.objects.select_for_update().get(id=suborder.id)
            master = Order.objects.select_for_update().get(id=sub.master_order_id)

            if sub.fulfillment_status == SubOrder.FULFILLMENT_CANCELLED:
                raise ValidationError("Cannot update fulfillment on a cancelled suborder.")

            sub.fulfillment_status = new_status
            if carrier:
                sub.shipping_carrier = carrier
            if tracking_number:
                sub.tracking_number = tracking_number

            now = timezone.now()
            if new_status == SubOrder.FULFILLMENT_SHIPPED and not sub.shipped_at:
                sub.shipped_at = now
            elif new_status == SubOrder.FULFILLMENT_DELIVERED:
                if not sub.delivered_at:
                    sub.delivered_at = now
                if master.payment_method == Order.PAYMENT_METHOD_COD:
                    master.cod_collection_status = Order.COD_STATUS_COLLECTED_BY_COURIER
                    master.save(update_fields=["cod_collection_status", "updated_at"])

            sub.save()

            # If all suborders for master order are delivered, mark order completed
            all_delivered = not master.suborders.exclude(fulfillment_status=SubOrder.FULFILLMENT_DELIVERED).exists()
            if all_delivered:
                master.order_status = Order.ORDER_STATUS_COMPLETED
                master.save(update_fields=["order_status", "updated_at"])

            return sub

    @classmethod
    def reconcile_cod_remittance(
        cls,
        suborder: SubOrder,
        courier_remittance_ref: str,
        courier_fee: Decimal = Decimal("0.00"),
    ) -> SubOrder:
        """
        Reconcile cash collected by courier and remitted to platform bank account.
        Transitions master payment to successful and posts vendor ledger entries with
        settlement hold window.
        Idempotent via unique idempotency keys.
        """
        with transaction.atomic():
            sub = SubOrder.objects.select_for_update().get(id=suborder.id)
            master = Order.objects.select_for_update().get(id=sub.master_order_id)

            if master.payment_method != Order.PAYMENT_METHOD_COD:
                raise ValidationError("Only COD suborders require courier remittance reconciliation.")

            if sub.fulfillment_status != SubOrder.FULFILLMENT_DELIVERED:
                raise ValidationError("Cannot reconcile COD remittance for undelivered suborder.")

            # Update master COD status
            master.cod_collection_status = Order.COD_STATUS_RECONCILED
            master.save(update_fields=["cod_collection_status", "updated_at"])

            # Mark payment record successful
            payment = master.payments.first()
            if payment:
                payment.status = OrderPayment.STATUS_SUCCESSFUL
                payment.gateway_payment_id = courier_remittance_ref
                payment.save(update_fields=["status", "gateway_payment_id", "updated_at"])

            unlock_timestamp = timezone.now() + timedelta(days=cls.SETTLEMENT_HOLD_DAYS)
            sub.seller_payable_status = SubOrder.PAYABLE_HOLDING
            sub.settlement_hold_until = unlock_timestamp
            sub.save(update_fields=["seller_payable_status", "settlement_hold_until", "updated_at"])

            # Post balanced vendor ledger entries
            if sub.vendor:
                # Credit merchandise amount remitted
                VendorLedger.objects.get_or_create(
                    idempotency_key=f"cod-remit-sale-{sub.suborder_number}-{courier_remittance_ref}",
                    defaults={
                        "vendor": sub.vendor,
                        "suborder": sub,
                        "entry_type": VendorLedger.ENTRY_CREDIT_COD_REMITTED,
                        "amount": sub.items_subtotal,
                        "currency": master.currency,
                        "is_settled": False,
                        "unlocks_at": unlock_timestamp,
                        "reference_id": courier_remittance_ref,
                        "notes": f"COD remittance collected for {sub.suborder_number}",
                    },
                )

                # Debit platform commission
                if sub.platform_commission > Decimal("0.00"):
                    VendorLedger.objects.get_or_create(
                        idempotency_key=f"cod-remit-comm-{sub.suborder_number}-{courier_remittance_ref}",
                        defaults={
                            "vendor": sub.vendor,
                            "suborder": sub,
                            "entry_type": VendorLedger.ENTRY_DEBIT_COMMISSION,
                            "amount": -sub.platform_commission,
                            "currency": master.currency,
                            "is_settled": False,
                            "unlocks_at": unlock_timestamp,
                            "reference_id": courier_remittance_ref,
                            "notes": f"Platform commission deduction on COD order ({sub.vendor.commission_rate}%)",
                        },
                    )

                # Optional courier deduction if seller bears courier cost
                if courier_fee > Decimal("0.00"):
                    VendorLedger.objects.get_or_create(
                        idempotency_key=f"cod-remit-fee-{sub.suborder_number}-{courier_remittance_ref}",
                        defaults={
                            "vendor": sub.vendor,
                            "suborder": sub,
                            "entry_type": VendorLedger.ENTRY_DEBIT_COURIER_SHIPPING,
                            "amount": -courier_fee,
                            "currency": master.currency,
                            "is_settled": False,
                            "unlocks_at": unlock_timestamp,
                            "reference_id": courier_remittance_ref,
                            "notes": f"Courier delivery charge on COD order",
                        },
                    )

            return sub

    @classmethod
    def cancel_suborder(
        cls,
        suborder: SubOrder,
        reason: str = "",
        cancelled_by=None,
    ) -> SubOrder:
        """
        Cancel a suborder prior to delivery.
        Restores physical inventory, forfeits payable balance, reverses ledger entries
        if already posted, and updates order status.
        """
        with transaction.atomic():
            sub = SubOrder.objects.select_for_update().get(id=suborder.id)
            master = Order.objects.select_for_update().get(id=sub.master_order_id)

            if sub.fulfillment_status == SubOrder.FULFILLMENT_CANCELLED:
                return sub  # Idempotent return

            if sub.fulfillment_status == SubOrder.FULFILLMENT_DELIVERED:
                raise ValidationError("Delivered suborders cannot be cancelled; initiate a return request instead.")

            # 1. Restore physical inventory
            items = list(sub.items.select_related("variant", "variant__product"))
            ReservationService.restore_inventory_for_items(items)

            # 2. Reverse vendor ledger entries if online payment was already completed
            if sub.vendor and master.online_payment_status == Order.ONLINE_STATUS_PAID:
                # Debit customer refund
                VendorLedger.objects.get_or_create(
                    idempotency_key=f"cancel-refund-{sub.suborder_number}",
                    defaults={
                        "vendor": sub.vendor,
                        "suborder": sub,
                        "entry_type": VendorLedger.ENTRY_DEBIT_REFUND,
                        "amount": -sub.items_subtotal,
                        "currency": master.currency,
                        "is_settled": True,
                        "reference_id": f"CANCEL-{sub.suborder_number}",
                        "notes": f"Customer refund on cancelled suborder {sub.suborder_number}",
                    },
                )
                # Credit commission reversal
                if sub.platform_commission > Decimal("0.00"):
                    VendorLedger.objects.get_or_create(
                        idempotency_key=f"cancel-comm-rev-{sub.suborder_number}",
                        defaults={
                            "vendor": sub.vendor,
                            "suborder": sub,
                            "entry_type": VendorLedger.ENTRY_CREDIT_COMMISSION_REVERSAL,
                            "amount": sub.platform_commission,
                            "currency": master.currency,
                            "is_settled": True,
                            "reference_id": f"CANCEL-{sub.suborder_number}",
                            "notes": f"Platform commission reversal on cancelled suborder",
                        },
                    )

            # 3. Revoke any digital delivery access tokens
            for item in sub.items.all():
                if hasattr(item, "digital_delivery"):
                    item.digital_delivery.is_revoked = True
                    item.digital_delivery.save(update_fields=["is_revoked"])

            sub.fulfillment_status = SubOrder.FULFILLMENT_CANCELLED
            sub.seller_payable_status = SubOrder.PAYABLE_FORFEITED
            sub.cancellation_reason = reason
            sub.cancelled_by = cancelled_by
            sub.cancelled_at = timezone.now()
            sub.save()

            # Check if all suborders in master order are cancelled
            all_cancelled = not master.suborders.exclude(fulfillment_status=SubOrder.FULFILLMENT_CANCELLED).exists()
            if all_cancelled:
                master.order_status = Order.ORDER_STATUS_CANCELLED
                master.save(update_fields=["order_status", "updated_at"])

            return sub

    @classmethod
    def handle_failed_delivery_rto(
        cls,
        suborder: SubOrder,
        rto_penalty: Decimal = Decimal("0.00"),
        reason: str = "",
    ) -> SubOrder:
        """
        Handle Return-to-Origin (RTO) for failed or refused physical deliveries.
        Restores physical inventory, forfeits payable balance, and applies optional RTO penalty.
        """
        with transaction.atomic():
            sub = SubOrder.objects.select_for_update().get(id=suborder.id)
            master = Order.objects.select_for_update().get(id=sub.master_order_id)

            if sub.fulfillment_status == SubOrder.FULFILLMENT_DELIVERED:
                raise ValidationError("Cannot mark delivered suborder as failed delivery.")

            # Restore inventory
            items = list(sub.items.select_related("variant", "variant__product"))
            ReservationService.restore_inventory_for_items(items)

            sub.fulfillment_status = SubOrder.FULFILLMENT_FAILED_RTO
            sub.seller_payable_status = SubOrder.PAYABLE_FORFEITED
            sub.actual_rto_cost = rto_penalty
            sub.save()

            if master.payment_method == Order.PAYMENT_METHOD_COD:
                master.cod_collection_status = Order.COD_STATUS_DELIVERY_REFUSED
                master.save(update_fields=["cod_collection_status", "updated_at"])

            # Debit RTO penalty to vendor ledger if applicable
            if sub.vendor and rto_penalty > Decimal("0.00"):
                VendorLedger.objects.get_or_create(
                    idempotency_key=f"rto-fee-{sub.suborder_number}",
                    defaults={
                        "vendor": sub.vendor,
                        "suborder": sub,
                        "entry_type": VendorLedger.ENTRY_DEBIT_RTO_SHIPPING,
                        "amount": -rto_penalty,
                        "currency": master.currency,
                        "is_settled": False,
                        "reference_id": f"RTO-{sub.suborder_number}",
                        "notes": f"RTO courier freight penalty for failed delivery ({reason})",
                    },
                )

            return sub
