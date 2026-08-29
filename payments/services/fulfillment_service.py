# payments/services/fulfillment_service.py

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from payments.models import (
    PaymentOrder,
    PaymentTransaction,
)

from organizations.models import ResourceAccess

from quiz.services.coupon_service import CouponService

from subscriptions.models import SubscriptionEntitlement

from subscriptions.services.plan_service import (
    get_plan_for_exam,
    get_plan_for_track,
)

from subscriptions.services.subscription_service import (
    SubscriptionService,
)


class PaymentFulfillmentService:
    """
    Fulfill successfully verified payments.

    Architecture:

        PaymentOrder
            ↓
        PaymentTransaction
            ↓
        SubscriptionService
            ↓
        Subscription
            ↓
        SubscriptionEntitlement
            ↓
        ResourceAccess
            ↓
        Coupon redemption

    IMPORTANT:

        Payment verification and payment fulfillment are separate.

        A payment must be successfully verified before this
        service is called.

        Coupon usage is consumed only after successful
        resource fulfillment.
    """

    # =========================================================
    # MAIN FULFILLMENT
    # =========================================================

    @staticmethod
    @transaction.atomic
    def fulfill(transaction_obj):
        """
        Fulfill a successfully verified payment.

        The entire operation is atomic.

        If subscription/access/coupon fulfillment fails,
        the transaction is rolled back.
        """

        # -----------------------------------------------------
        # VALIDATION
        # -----------------------------------------------------

        if not transaction_obj:
            raise ValidationError(
                "Payment transaction is required."
            )

        # -----------------------------------------------------
        # LOCK PAYMENT TRANSACTION
        # -----------------------------------------------------

        transaction_obj = (
            PaymentTransaction.objects
            .select_for_update()
            .select_related(
                "order",
                "order__user",
                "order__exam",
                "order__track",
                "order__course",
            )
            .get(
                pk=transaction_obj.pk
            )
        )

        order = transaction_obj.order

        # -----------------------------------------------------
        # IDEMPOTENCY
        # -----------------------------------------------------

        if (
            transaction_obj.status
            == PaymentTransaction.STATUS_SUCCESS
            and order.status
            == PaymentOrder.STATUS_PAID
        ):
            return {
                "success": True,
                "already_fulfilled": True,
                "order": order,
                "transaction": transaction_obj,
                "coupon_redemption": None,
            }

        # -----------------------------------------------------
        # PAYMENT MUST BE SUCCESSFUL
        # -----------------------------------------------------

        if (
            transaction_obj.status
            != PaymentTransaction.STATUS_SUCCESS
        ):
            raise ValidationError(
                "Only successful payments can be fulfilled."
            )

        # -----------------------------------------------------
        # RESOURCE
        # -----------------------------------------------------

        resource = order.get_resource()

        if not resource:
            raise ValidationError(
                "Payment order has no valid resource."
            )

        # -----------------------------------------------------
        # RESOURCE FULFILLMENT
        #
        # Do NOT mark order PAID before fulfillment.
        # -----------------------------------------------------

        if (
            order.resource_type
            == PaymentOrder.RESOURCE_EXAM
        ):

            result = (
                PaymentFulfillmentService._fulfill_exam(
                    order=order,
                    transaction_obj=transaction_obj,
                    exam=resource,
                )
            )

        elif (
            order.resource_type
            == PaymentOrder.RESOURCE_TRACK
        ):

            result = (
                PaymentFulfillmentService._fulfill_track(
                    order=order,
                    transaction_obj=transaction_obj,
                    track=resource,
                )
            )

        elif (
            order.resource_type
            == PaymentOrder.RESOURCE_COURSE
        ):

            raise ValidationError(
                "Course payment fulfillment is not implemented yet."
            )

        else:

            raise ValidationError(
                "Unsupported payment resource type."
            )

        # -----------------------------------------------------
        # MARK ORDER PAID
        #
        # Only after resource fulfillment succeeds.
        # -----------------------------------------------------

        order.status = PaymentOrder.STATUS_PAID

        if not order.paid_at:
            order.paid_at = timezone.now()

        order.save(
            update_fields=[
                "status",
                "paid_at",
                "updated_at",
            ]
        )

        # -----------------------------------------------------
        # COUPON REDEMPTION
        #
        # Coupon is consumed only after successful payment
        # fulfillment.
        # -----------------------------------------------------

        coupon_redemption = (
            CouponService.redeem_order_coupon(
                order
            )
        )

        # -----------------------------------------------------
        # RESULT
        # -----------------------------------------------------

        result["success"] = True
        result["already_fulfilled"] = False
        result["order"] = order
        result["transaction"] = transaction_obj
        result["coupon_redemption"] = (
            coupon_redemption
        )

        return result

    # =========================================================
    # EXAM FULFILLMENT
    # =========================================================

    @staticmethod
    def _fulfill_exam(
        *,
        order,
        transaction_obj,
        exam,
    ):
        """
        Fulfill an individual exam purchase.

        Buying an individual exam grants access to that exam.

        It does not automatically grant the parent track.
        """

        # -----------------------------------------------------
        # FIND PLAN
        # -----------------------------------------------------

        plan = get_plan_for_exam(
            exam,
            None,
        )

        if not plan:
            raise ValidationError(
                "No active subscription plan is configured "
                "for this exam."
            )

        # -----------------------------------------------------
        # CREATE / REACTIVATE SUBSCRIPTION
        #
        # SubscriptionService is responsible for:
        #
        #   Subscription
        #       ↓
        #   SubscriptionEntitlement
        #       ↓
        #   ResourceAccess
        # -----------------------------------------------------

        subscription, entitlement = (
            SubscriptionService
            .create_or_reactivate_subscription(
                user=order.user,
                resource_type=(
                    SubscriptionEntitlement.RESOURCE_EXAM
                ),
                resource=exam,
                plan=plan,
                granted_by=None,
                notes=(
                    f"Online exam payment: "
                    f"{order.order_number}"
                ),
            )
        )

        # -----------------------------------------------------
        # UPDATE PAYMENT INFORMATION
        # -----------------------------------------------------

        subscription.amount = order.amount
        subscription.currency = order.currency
        subscription.payment_status = "paid"

        subscription.payment_id = (
            order.gateway_payment_id
            or transaction_obj.gateway_transaction_id
            or order.order_number
        )

        subscription.subscribed_by_admin = False
        subscription.granted_by = None

        subscription.save(
            update_fields=[
                "amount",
                "currency",
                "payment_status",
                "payment_id",
                "subscribed_by_admin",
                "granted_by",
                "updated_at",
            ]
        )

        # -----------------------------------------------------
        # GET ACCESS
        #
        # create_or_reactivate_subscription() already grants
        # ResourceAccess through AccessService.
        #
        # We therefore do NOT create a second access record.
        # -----------------------------------------------------

        access = (
            ResourceAccess.objects
            .filter(
                user=order.user,
                resource_type=(
                    SubscriptionEntitlement.RESOURCE_EXAM
                ),
                exam=exam,
                subscription=subscription,
            )
            .first()
        )

        return {
            "subscription": subscription,
            "entitlement": entitlement,
            "access": access,
            "access_created": access is not None,
        }

    # =========================================================
    # TRACK FULFILLMENT
    # =========================================================

    @staticmethod
    def _fulfill_track(
        *,
        order,
        transaction_obj,
        track,
    ):
        """
        Fulfill an individual track purchase.

        Buying a track grants access to the track.

        It does not create individual exam subscriptions.
        """

        # -----------------------------------------------------
        # FIND PLAN
        # -----------------------------------------------------

        plan = get_plan_for_track(
            track,
            None,
        )

        if not plan:
            raise ValidationError(
                "No active subscription plan is configured "
                "for this track."
            )

        # -----------------------------------------------------
        # CREATE / REACTIVATE SUBSCRIPTION
        # -----------------------------------------------------

        subscription, entitlement = (
            SubscriptionService
            .create_or_reactivate_subscription(
                user=order.user,
                resource_type=(
                    SubscriptionEntitlement.RESOURCE_TRACK
                ),
                resource=track,
                plan=plan,
                granted_by=None,
                notes=(
                    f"Online track payment: "
                    f"{order.order_number}"
                ),
            )
        )

        # -----------------------------------------------------
        # UPDATE PAYMENT INFORMATION
        # -----------------------------------------------------

        subscription.amount = order.amount
        subscription.currency = order.currency
        subscription.payment_status = "paid"

        subscription.payment_id = (
            order.gateway_payment_id
            or transaction_obj.gateway_transaction_id
            or order.order_number
        )

        subscription.subscribed_by_admin = False
        subscription.granted_by = None

        subscription.save(
            update_fields=[
                "amount",
                "currency",
                "payment_status",
                "payment_id",
                "subscribed_by_admin",
                "granted_by",
                "updated_at",
            ]
        )

        # -----------------------------------------------------
        # GET ACCESS
        #
        # SubscriptionService already grants ResourceAccess.
        # -----------------------------------------------------

        access = (
            ResourceAccess.objects
            .filter(
                user=order.user,
                resource_type=(
                    SubscriptionEntitlement.RESOURCE_TRACK
                ),
                track=track,
                subscription=subscription,
            )
            .first()
        )

        return {
            "subscription": subscription,
            "entitlement": entitlement,
            "access": access,
            "access_created": access is not None,
        }