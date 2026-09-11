from django.db import transaction

from organizations.models.access import ResourceAccess
from subscriptions.models import (
    Payment,
    Subscription,
    SubscriptionEntitlement,
)
from subscriptions.services.access_service import AccessService
from subscriptions.services.plan_service import get_plan_for_course
from subscriptions.services.subscription_service import SubscriptionService


class CourseAccessService:
    """Centralized lifecycle operations for direct course entitlements."""

    RESOURCE_TYPE = SubscriptionEntitlement.RESOURCE_COURSE

    @staticmethod
    def has_access(user, course):
        return AccessService.has_access(
            student=user,
            resource_type=CourseAccessService.RESOURCE_TYPE,
            resource=course,
        )

    @staticmethod
    @transaction.atomic
    def grant_admin_access(*, user, course, plan=None, granted_by=None):
        if not user:
            raise ValueError("User is required.")
        if not course:
            raise ValueError("Course is required.")

        plan = plan or get_plan_for_course(course)
        if not plan:
            raise ValueError("No active subscription plan is attached to this course.")
        if not plan.is_active or plan.is_all_access():
            raise ValueError("The selected course plan is inactive or is an all-access plan.")
        if not course.subscription_plans.filter(
            pk=plan.pk,
            is_active=True,
            scope=plan.SCOPE_RESOURCE,
        ).exists():
            raise ValueError("The selected plan is not attached to this course.")

        entitlement = (
            SubscriptionEntitlement.objects
            .select_related("subscription", "subscription__plan")
            .filter(
                subscription__user=user,
                resource_type=self.RESOURCE_TYPE if False else SubscriptionEntitlement.RESOURCE_COURSE,
                course=course,
                is_active=True,
                subscription__status=Subscription.STATUS_ACTIVE,
            )
            .order_by("-subscription__created_at")
            .first()
        )

        if entitlement and entitlement.subscription.plan_id != plan.id:
            entitlement.is_active = False
            entitlement.save(update_fields=["is_active", "updated_at"])
            entitlement = None

        if not entitlement:
            subscription = SubscriptionService.create_subscription(
                plan=plan,
                user=user,
                granted_by=granted_by,
                subscribed_by_admin=True,
                payment_status=Payment.STATUS_SUCCESS,
                payment_provider=Payment.PROVIDER_MANUAL,
                notes="Admin manual course access",
            )
            entitlement = SubscriptionEntitlement(
                subscription=subscription,
                resource_type=SubscriptionEntitlement.RESOURCE_COURSE,
                course=course,
                is_active=True,
            )
            entitlement.full_clean()
            entitlement.save()
        else:
            subscription = SubscriptionService.activate_subscription(entitlement.subscription)

        AccessService.grant_access(
            user=user,
            resource_type=ResourceAccess.RESOURCE_COURSE,
            resource=course,
            source=ResourceAccess.SOURCE_ADMIN,
            subscription=subscription,
            expires_at=subscription.expires_at,
        )

        return subscription, entitlement

    @staticmethod
    def get_user_course_entitlement(*, user, course):
        return (
            SubscriptionEntitlement.objects
            .select_related("subscription", "subscription__plan", "course")
            .filter(
                subscription__user=user,
                resource_type=SubscriptionEntitlement.RESOURCE_COURSE,
                course=course,
                is_active=True,
                subscription__status=Subscription.STATUS_ACTIVE,
            )
            .order_by("-subscription__created_at")
            .first()
        )

    @staticmethod
    @transaction.atomic
    def revoke_admin_access(*, user, course):
        entitlement = CourseAccessService.get_user_course_entitlement(user=user, course=course)
        if not entitlement:
            raise ValueError("Course entitlement not found.")

        subscription = entitlement.subscription
        entitlement.is_active = False
        entitlement.save(update_fields=["is_active", "updated_at"])
        result = AccessService.revoke_access(
            user=user,
            resource_type=ResourceAccess.RESOURCE_COURSE,
            resource=course,
            source=ResourceAccess.SOURCE_ADMIN,
            subscription=subscription,
        )

        if not SubscriptionEntitlement.objects.filter(
            subscription=subscription,
            is_active=True,
        ).exists():
            subscription.status = Subscription.STATUS_CANCELLED
            subscription.cancelled_at = subscription.cancelled_at or __import__("django.utils.timezone", fromlist=["timezone"]).timezone.now()
            subscription.save(update_fields=["status", "cancelled_at", "updated_at"])

        return result
