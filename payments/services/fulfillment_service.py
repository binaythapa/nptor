from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from payments.models import PaymentOrder, PaymentTransaction
from organizations.models import ResourceAccess
from quiz.services.coupon_service import CouponService
from subscriptions.models import Subscription, SubscriptionEntitlement
from subscriptions.services.plan_service import (
    get_plan_for_course,
    get_plan_for_exam,
    get_plan_for_track,
)
from subscriptions.services.subscription_service import SubscriptionService


class PaymentFulfillmentService:
    """Fulfill successfully verified payments and grant resource access."""

    @staticmethod
    @transaction.atomic
    def fulfill(transaction_obj):
        if not transaction_obj:
            raise ValidationError("Payment transaction is required.")

        transaction_obj = (
            PaymentTransaction.objects
            .select_for_update()
            .select_related(
                "order", "order__user", "order__exam",
                "order__track", "order__course",
            )
            .get(pk=transaction_obj.pk)
        )
        order = transaction_obj.order

        if (
            transaction_obj.status == PaymentTransaction.STATUS_SUCCESS
            and order.status == PaymentOrder.STATUS_PAID
        ):
            return {
                "success": True,
                "already_fulfilled": True,
                "order": order,
                "transaction": transaction_obj,
                "coupon_redemption": None,
            }

        if transaction_obj.status != PaymentTransaction.STATUS_SUCCESS:
            raise ValidationError("Only successful payments can be fulfilled.")

        resource = order.get_resource()
        if not resource:
            raise ValidationError("Payment order has no valid resource.")

        if order.resource_type == PaymentOrder.RESOURCE_EXAM:
            result = PaymentFulfillmentService._fulfill_exam(
                order=order, transaction_obj=transaction_obj, exam=resource
            )
        elif order.resource_type == PaymentOrder.RESOURCE_TRACK:
            result = PaymentFulfillmentService._fulfill_track(
                order=order, transaction_obj=transaction_obj, track=resource
            )
        elif order.resource_type == PaymentOrder.RESOURCE_COURSE:
            result = PaymentFulfillmentService._fulfill_course(
                order=order, transaction_obj=transaction_obj, course=resource
            )
        else:
            raise ValidationError("Unsupported payment resource type.")

        order.status = PaymentOrder.STATUS_PAID
        if not order.paid_at:
            order.paid_at = timezone.now()
        order.save(update_fields=["status", "paid_at", "updated_at"])

        coupon_redemption = CouponService.redeem_order_coupon(order)
        result.update({
            "success": True,
            "already_fulfilled": False,
            "order": order,
            "transaction": transaction_obj,
            "coupon_redemption": coupon_redemption,
        })
        return result

    @staticmethod
    def _update_paid_subscription(subscription, order, transaction_obj):
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
        subscription.save(update_fields=[
            "amount", "currency", "payment_status", "payment_id",
            "subscribed_by_admin", "granted_by", "updated_at",
        ])

    @staticmethod
    def _access_result(*, user, resource_type, resource, subscription):
        access = (
            ResourceAccess.objects
            .filter(
                user=user,
                resource_type=resource_type,
                subscription=subscription,
                **{
                    resource_type: resource,
                },
            )
            .first()
        )
        return {
            "subscription": subscription,
            "access": access,
            "access_created": access is not None,
        }

    @staticmethod
    def _fulfill_exam(*, order, transaction_obj, exam):
        plan = get_plan_for_exam(exam, None)
        if not plan:
            raise ValidationError(
                "No active subscription plan is configured for this exam."
            )

        subscription, entitlement = SubscriptionService.create_or_reactivate_subscription(
            user=order.user,
            resource_type=SubscriptionEntitlement.RESOURCE_EXAM,
            resource=exam,
            plan=plan,
            granted_by=None,
            notes=f"Online exam payment: {order.order_number}",
        )
        PaymentFulfillmentService._update_paid_subscription(
            subscription, order, transaction_obj
        )
        result = PaymentFulfillmentService._access_result(
            user=order.user,
            resource_type=SubscriptionEntitlement.RESOURCE_EXAM,
            resource=exam,
            subscription=subscription,
        )
        result["entitlement"] = entitlement
        return result

    @staticmethod
    def _fulfill_track(*, order, transaction_obj, track):
        plan = get_plan_for_track(track, None)
        if not plan:
            raise ValidationError(
                "No active subscription plan is configured for this track."
            )

        subscription, entitlement = SubscriptionService.create_or_reactivate_subscription(
            user=order.user,
            resource_type=SubscriptionEntitlement.RESOURCE_TRACK,
            resource=track,
            plan=plan,
            granted_by=None,
            notes=f"Online track payment: {order.order_number}",
        )
        PaymentFulfillmentService._update_paid_subscription(
            subscription, order, transaction_obj
        )
        result = PaymentFulfillmentService._access_result(
            user=order.user,
            resource_type=SubscriptionEntitlement.RESOURCE_TRACK,
            resource=track,
            subscription=subscription,
        )
        result["entitlement"] = entitlement
        return result

    @staticmethod
    @transaction.atomic
    def _fulfill_course(*, order, transaction_obj, course):
        plan = get_plan_for_course(course, None)
        if not plan:
            raise ValidationError(
                "No active subscription plan is configured for this course."
            )

        now = timezone.now()
        subscription = (
            Subscription.objects
            .filter(
                user=order.user,
                plan=plan,
                status=Subscription.STATUS_ACTIVE,
                starts_at__lte=now,
            )
            .filter(
                expires_at__isnull=True,
            )
            .order_by("-created_at")
            .first()
        )
        if not subscription:
            subscription = (
                Subscription.objects
                .filter(
                    user=order.user,
                    plan=plan,
                    status=Subscription.STATUS_ACTIVE,
                    starts_at__lte=now,
                    expires_at__gt=now,
                )
                .order_by("-created_at")
                .first()
            )

        if subscription:
            SubscriptionService.activate_subscription(subscription)
        else:
            subscription = SubscriptionService.create_subscription(
                plan=plan,
                user=order.user,
                organization=None,
                granted_by=None,
                subscribed_by_admin=False,
                payment_status="success",
                order_id=order.order_number,
                notes=f"Online course payment: {order.order_number}",
                start_at=now,
            )

        entitlement = (
            SubscriptionEntitlement.objects
            .filter(
                subscription=subscription,
                resource_type=SubscriptionEntitlement.RESOURCE_COURSE,
                course=course,
            )
            .first()
        )
        if entitlement:
            if not entitlement.is_active:
                entitlement.is_active = True
                entitlement.save(update_fields=["is_active", "updated_at"])
        else:
            entitlement = SubscriptionEntitlement(
                subscription=subscription,
                resource_type=SubscriptionEntitlement.RESOURCE_COURSE,
                course=course,
                is_active=True,
            )
            entitlement.full_clean()
            entitlement.save()

        AccessService = __import__(
            "subscriptions.services.access_service",
            fromlist=["AccessService"],
        ).AccessService
        AccessService.grant_access(
            user=order.user,
            resource_type=AccessService.RESOURCE_COURSE,
            resource=course,
            source=ResourceAccess.SOURCE_INDIVIDUAL,
            subscription=subscription,
            expires_at=subscription.expires_at,
        )
        PaymentFulfillmentService._update_paid_subscription(
            subscription, order, transaction_obj
        )
        result = PaymentFulfillmentService._access_result(
            user=order.user,
            resource_type=SubscriptionEntitlement.RESOURCE_COURSE,
            resource=course,
            subscription=subscription,
        )
        result["entitlement"] = entitlement
        return result
