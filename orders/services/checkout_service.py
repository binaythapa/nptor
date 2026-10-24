from collections import defaultdict
from decimal import Decimal
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from cart.models import Cart
from cart.services.cart_service import CartService
from cart.services.reservation_service import ReservationService
from orders.models import (
    Order,
    OrderItem,
    OrderPayment,
    ShippingAddress,
    SubOrder,
)
from store.models import Product


class CheckoutService:
    @classmethod
    def prepare_checkout(
        cls,
        *,
        cart: Cart,
        user,
        shipping_address: ShippingAddress = None,
        payment_method: str = Order.PAYMENT_METHOD_ONLINE,
        idempotency_key: str = None,
    ) -> Order:
        """
        Validate cart, reserve stock, enforce geographical and COD restrictions,
        split orders across vendors, and generate the master Order and SubOrders.
        """
        # 1. Idempotency Check: if order with this key already exists, return it
        if idempotency_key:
            existing_order = Order.objects.filter(idempotency_key=idempotency_key).first()
            if existing_order:
                return existing_order

        # 2. Server-side validation of cart products & price changes
        cart_analysis = CartService.validate_cart(cart)
        has_physical = cart_analysis["has_physical"]
        has_digital = cart_analysis["has_digital"]
        is_mixed = cart_analysis["is_mixed"]

        # 3. Geographical Gating: Nepal delivery for physical products
        if has_physical:
            if not shipping_address:
                raise ValidationError("Shipping address is required for orders containing physical products.")
            if shipping_address.country != "NP":
                raise ValidationError("Physical product delivery is currently supported only within Nepal.")

        # 4. Payment Method & Cart Constraints
        if payment_method == Order.PAYMENT_METHOD_COD:
            if has_digital and not has_physical:
                raise ValidationError("Cash on Delivery cannot be used for digital downloads.")
            if is_mixed:
                raise ValidationError(
                    "Cash on Delivery cannot be used for mixed carts containing digital downloads. "
                    "Please checkout digital items separately using online payment."
                )
            if not cart_analysis["is_cod_eligible"]:
                raise ValidationError(
                    "One or more products or sellers in your cart are not eligible for Cash on Delivery."
                )

        # Demonstration catalog restriction: public checkout rejects demonstration items
        has_demo = any(
            getattr(it.variant.product, "is_demo", False)
            for it in cart.items.select_related("variant__product")
        )
        if has_demo and not (user and getattr(user, "is_staff", False)):
            raise ValidationError(
                "Your cart contains demonstration showcase products. "
                "Demonstration products cannot be ordered through live public checkout."
            )

        # 5. Atomic Stock Reservation (locks inventory rows)
        if has_physical:
            ReservationService.reserve_cart_stock(cart)

        # 6. Group items by vendor (None denotes NPTOR-owned)
        items = list(cart.items.select_related("variant", "variant__product", "variant__product__vendor"))
        vendor_groups = defaultdict(list)
        for it in items:
            vendor_groups[it.variant.product.vendor].append(it)

        total_items_amount = sum(it.total_price for it in items)
        shipping_amount = Decimal("0.00")  # MVP baseline; configurable per seller in Phase 7
        grand_total = total_items_amount + shipping_amount

        # 7. Generate Master Order and SubOrders inside atomic transaction
        with transaction.atomic():
            order_number = f"NPTOR-ORD-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

            cod_status = Order.COD_STATUS_PENDING_DELIVERY if payment_method == Order.PAYMENT_METHOD_COD else Order.COD_STATUS_NOT_APPLICABLE
            online_status = Order.ONLINE_STATUS_UNPAID if payment_method == Order.PAYMENT_METHOD_ONLINE else Order.ONLINE_STATUS_NOT_APPLICABLE

            order = Order.objects.create(
                order_number=order_number,
                user=user,
                payment_method=payment_method,
                total_items_amount=total_items_amount,
                shipping_amount=shipping_amount,
                grand_total=grand_total,
                currency="NPR",
                shipping_address=shipping_address,
                order_status=Order.ORDER_STATUS_PENDING,
                online_payment_status=online_status,
                cod_collection_status=cod_status,
                idempotency_key=idempotency_key,
            )

            # Create SubOrders for each vendor
            for idx, (vendor, group_items) in enumerate(vendor_groups.items(), 1):
                suborder_number = f"{order.order_number}-{idx:02d}"
                subtotal = sum(it.total_price for it in group_items)

                # Commission rate baseline
                comm_rate = vendor.commission_rate if vendor else Decimal("0.00")
                platform_comm = (subtotal * comm_rate / Decimal("100.00")).quantize(Decimal("0.01"))
                vendor_payout = subtotal - platform_comm

                suborder = SubOrder.objects.create(
                    master_order=order,
                    suborder_number=suborder_number,
                    vendor=vendor,
                    items_subtotal=subtotal,
                    platform_commission=platform_comm,
                    vendor_payout_amount=vendor_payout,
                    fulfillment_status=SubOrder.FULFILLMENT_PENDING,
                    seller_payable_status=SubOrder.PAYABLE_HOLDING,
                )

                for it in group_items:
                    OrderItem.objects.create(
                        suborder=suborder,
                        variant=it.variant,
                        product_title_snapshot=it.variant.product.title,
                        sku_snapshot=it.variant.sku,
                        unit_price=it.unit_price_snapshot,
                        quantity=it.quantity,
                        total_price=it.total_price,
                        commission_rate_snapshot=comm_rate,
                    )

            # Create pending OrderPayment record
            OrderPayment.objects.create(
                order=order,
                payment_method=payment_method,
                amount=grand_total,
                currency="NPR",
                status=OrderPayment.STATUS_PENDING,
                gateway_name="dummy" if payment_method == Order.PAYMENT_METHOD_ONLINE else "cod",
                idempotency_key=f"PAY-{order.order_number}",
            )

            # Clear cart items after successful order creation
            cart.items.all().delete()

        return order
