# payments/services/payment_service.py


from django.db import transaction
from django.core.exceptions import ValidationError

from payments.models import (
    PaymentOrder,
    PaymentTransaction,
)

from payments.gateways.factory import PaymentGatewayFactory


class PaymentService:
    """
    Central service for online payment processing.

    Architecture:

        PaymentOrder
             ↓
        PaymentTransaction
             ↓
        Payment Gateway
             ↓
        Payment verification
             ↓
        PaymentFulfillmentService
             ↓
        Subscription
             ↓
        SubscriptionEntitlement
             ↓
        ResourceAccess

    IMPORTANT:

    This service handles payment processing only.

    It does NOT directly create subscriptions or resource access.

    Fulfillment is handled separately by:

        PaymentFulfillmentService.fulfill()
    """

    # =========================================================
    # INITIATE PAYMENT
    # =========================================================

    @staticmethod
    @transaction.atomic
    def initiate_payment(
        *,
        order,
        gateway_name,
    ):
        """
        Initiate payment for an existing PaymentOrder.

        Flow:

            PaymentOrder
                ↓
            Payment Gateway
                ↓
            PaymentTransaction = pending

        Returns:

            {
                "success": True/False,
                "order": PaymentOrder,
                "transaction": PaymentTransaction,
                "gateway_response": dict,
            }
        """

        # -----------------------------------------------------
        # Validate order
        # -----------------------------------------------------

        if not order:
            raise ValidationError(
                "Payment order is required."
            )

        # -----------------------------------------------------
        # Validate order status
        # -----------------------------------------------------

        if order.status not in (
            PaymentOrder.STATUS_PENDING,
            PaymentOrder.STATUS_PROCESSING,
        ):
            raise ValidationError(
                "This order cannot be paid."
            )

        # -----------------------------------------------------
        # Validate gateway
        # -----------------------------------------------------

        if not gateway_name:
            raise ValidationError(
                "Payment gateway is required."
            )

        # -----------------------------------------------------
        # Get gateway
        # -----------------------------------------------------

        gateway = PaymentGatewayFactory.get(
            gateway_name
        )

        # -----------------------------------------------------
        # Mark order as processing
        # -----------------------------------------------------

        order.status = (
            PaymentOrder.STATUS_PROCESSING
        )

        order.gateway = gateway_name

        order.save(
            update_fields=[
                "status",
                "gateway",
                "updated_at",
            ]
        )

        # -----------------------------------------------------
        # Create payment transaction
        # -----------------------------------------------------

        transaction_obj = (
            PaymentTransaction.objects.create(
                order=order,
                gateway=gateway_name,
                amount=order.amount,
                currency=order.currency,
                status=(
                    PaymentTransaction.STATUS_CREATED
                ),
            )
        )

        # -----------------------------------------------------
        # Ask gateway to create payment
        # -----------------------------------------------------

        result = gateway.create_payment(
            order=order
        )

        # -----------------------------------------------------
        # Gateway initialization failed
        # -----------------------------------------------------

        if not result.get("success"):

            transaction_obj.status = (
                PaymentTransaction.STATUS_FAILED
            )

            transaction_obj.failure_reason = (
                result.get(
                    "error",
                    "Payment initialization failed.",
                )
            )

            transaction_obj.raw_response = result

            transaction_obj.save(
                update_fields=[
                    "status",
                    "failure_reason",
                    "raw_response",
                    "updated_at",
                ]
            )

            order.status = (
                PaymentOrder.STATUS_FAILED
            )

            order.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )

            return {
                "success": False,
                "order": order,
                "transaction": transaction_obj,
                "gateway_response": result,
            }

        # -----------------------------------------------------
        # Gateway initialization successful
        # -----------------------------------------------------

        gateway_order_id = result.get(
            "gateway_order_id"
        )

        transaction_obj.status = (
            PaymentTransaction.STATUS_PENDING
        )

        transaction_obj.raw_response = result

        transaction_obj.save(
            update_fields=[
                "status",
                "raw_response",
                "updated_at",
            ]
        )

        # -----------------------------------------------------
        # Store gateway order ID
        # -----------------------------------------------------

        if gateway_order_id:

            order.gateway_order_id = (
                gateway_order_id
            )

            order.save(
                update_fields=[
                    "gateway_order_id",
                    "updated_at",
                ]
            )

        # -----------------------------------------------------
        # Return
        # -----------------------------------------------------

        return {
            "success": True,
            "order": order,
            "transaction": transaction_obj,
            "gateway_response": result,
        }

    # =========================================================
    # VERIFY PAYMENT
    # =========================================================

    @staticmethod
    @transaction.atomic
    def verify_payment(
        *,
        transaction_obj,
        data,
    ):
        """
        Verify a payment using the configured gateway.

        IMPORTANT:

        This method only changes the transaction to SUCCESS
        after gateway verification succeeds.

        It does NOT create subscriptions or access.

        Fulfillment is handled separately by:

            PaymentFulfillmentService.fulfill()
        """

        # -----------------------------------------------------
        # Validate transaction
        # -----------------------------------------------------

        if not transaction_obj:
            raise ValidationError(
                "Payment transaction is required."
            )

        # -----------------------------------------------------
        # Lock transaction
        #
        # Prevent two simultaneous requests from processing
        # the same transaction.
        # -----------------------------------------------------

        transaction_obj = (
            PaymentTransaction.objects
            .select_for_update()
            .select_related(
                "order",
            )
            .get(
                pk=transaction_obj.pk
            )
        )

        order = transaction_obj.order

        # -----------------------------------------------------
        # Idempotency
        #
        # If already successful, don't verify again.
        # -----------------------------------------------------

        if (
            transaction_obj.status
            == PaymentTransaction.STATUS_SUCCESS
        ):

            return {
                "success": True,
                "already_verified": True,
                "transaction": transaction_obj,
                "order": order,
            }

        # -----------------------------------------------------
        # Failed/refunded transactions cannot be verified
        # again.
        # -----------------------------------------------------

        if transaction_obj.status in (
            PaymentTransaction.STATUS_FAILED,
            PaymentTransaction.STATUS_REFUNDED,
        ):

            raise ValidationError(
                "This payment transaction cannot be verified."
            )

        # -----------------------------------------------------
        # Get gateway
        # -----------------------------------------------------

        gateway = PaymentGatewayFactory.get(
            transaction_obj.gateway
        )

        # -----------------------------------------------------
        # Verify with gateway
        # -----------------------------------------------------

        result = gateway.verify_payment(
            data=data
        )

        # -----------------------------------------------------
        # Verification failed
        # -----------------------------------------------------

        if not result.get("success"):

            transaction_obj.status = (
                PaymentTransaction.STATUS_FAILED
            )

            transaction_obj.failure_reason = (
                result.get(
                    "error",
                    "Payment verification failed.",
                )
            )

            transaction_obj.raw_response = result

            transaction_obj.save(
                update_fields=[
                    "status",
                    "failure_reason",
                    "raw_response",
                    "updated_at",
                ]
            )

            order.status = (
                PaymentOrder.STATUS_FAILED
            )

            order.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )

            return {
                "success": False,
                "transaction": transaction_obj,
                "order": order,
                "gateway_response": result,
            }

        # -----------------------------------------------------
        # Successful verification
        # -----------------------------------------------------

        gateway_payment_id = result.get(
            "gateway_payment_id",
            "",
        )

        transaction_obj.status = (
            PaymentTransaction.STATUS_SUCCESS
        )

        transaction_obj.gateway_transaction_id = (
            gateway_payment_id
        )

        transaction_obj.raw_response = result

        transaction_obj.save(
            update_fields=[
                "status",
                "gateway_transaction_id",
                "raw_response",
                "updated_at",
            ]
        )

        # -----------------------------------------------------
        # Store gateway payment ID on order
        # -----------------------------------------------------

        order.gateway_payment_id = (
            gateway_payment_id
        )

        order.save(
            update_fields=[
                "gateway_payment_id",
                "updated_at",
            ]
        )

        # -----------------------------------------------------
        # IMPORTANT
        #
        # DO NOT mark the order as PAID here.
        #
        # Verification and fulfillment are separate.
        #
        # The next step is:
        #
        #     PaymentFulfillmentService.fulfill(
        #         transaction_obj
        #     )
        #
        # Fulfillment will:
        #
        #     PaymentOrder → PAID
        #     Subscription
        #     Entitlement
        #     ResourceAccess
        #
        # -----------------------------------------------------

        return {
            "success": True,
            "already_verified": False,
            "transaction": transaction_obj,
            "order": order,
            "gateway_response": result,
        }