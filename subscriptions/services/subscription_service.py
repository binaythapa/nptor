import calendar
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from organizations.models.access import ResourceAccess
from subscriptions.models import (
    Payment,
    Subscription,
    SubscriptionEntitlement,
    SubscriptionPlan,
)
from subscriptions.services.access_service import AccessService


class SubscriptionService:
    """Centralized subscription lifecycle and billing logic."""

    @staticmethod
    def calculate_expiry(plan, starts_at):
        """Calculate an expiry timestamp from a plan's billing interval.

        Calendar months and years are handled as calendar periods rather than
        approximated day counts. Legacy plans continue to fall back to
        ``duration_days`` until they are migrated to an explicit interval.
        """
        if plan.interval_unit == SubscriptionPlan.INTERVAL_LIFETIME:
            return None

        if plan.interval_unit:
            count = plan.interval_count
            if not count or count <= 0:
                raise ValueError("A time-based subscription plan requires a positive interval count.")

            if plan.interval_unit == SubscriptionPlan.INTERVAL_DAY:
                return starts_at + timedelta(days=count)
            if plan.interval_unit == SubscriptionPlan.INTERVAL_WEEK:
                return starts_at + timedelta(weeks=count)
            if plan.interval_unit == SubscriptionPlan.INTERVAL_MONTH:
                total_months = (starts_at.year * 12 + starts_at.month - 1) + count
                year = total_months // 12
                month = total_months % 12 + 1
                day = min(starts_at.day, calendar.monthrange(year, month)[1])
                return starts_at.replace(year=year, month=month, day=day)
            if plan.interval_unit == SubscriptionPlan.INTERVAL_YEAR:
                target_year = starts_at.year + count
                day = min(starts_at.day, calendar.monthrange(target_year, starts_at.month)[1])
                return starts_at.replace(year=target_year, day=day)

        if plan.duration_days is None:
            return None
        return starts_at + timedelta(days=plan.duration_days)

    @staticmethod
    @transaction.atomic
    def create_subscription(
        *,
        plan,
        user=None,
        organization=None,
        granted_by=None,
        subscribed_by_admin=False,
        payment_status=Payment.STATUS_PENDING,
        payment_provider=Payment.PROVIDER_MANUAL,
        transaction_id="",
        order_id="",
        notes="",
        start_at=None,
    ):
        if not plan:
            raise ValueError("A subscription plan is required.")
        if not plan.is_active:
            raise ValueError("The selected subscription plan is inactive.")
        if user is not None and organization is not None:
            raise ValueError("A subscription cannot belong to both a user and an organization.")
        if user is None and organization is None:
            raise ValueError("A subscription must belong to either a user or an organization.")

        starts_at = start_at or timezone.now()
        expires_at = SubscriptionService.calculate_expiry(plan, starts_at)

        subscription = Subscription.objects.create(
            plan=plan,
            user=user,
            organization=organization,
            status=Subscription.STATUS_ACTIVE,
            starts_at=starts_at,
            expires_at=expires_at,
            amount=plan.price,
            currency=plan.currency,
            payment_status=(
                "not_required"
                if plan.price == 0
                else ("paid" if payment_status == Payment.STATUS_SUCCESS else "pending")
            ),
            subscribed_by_admin=subscribed_by_admin,
            granted_by=granted_by,
            notes=notes or "",
        )

        if plan.price > 0:
            Payment.objects.create(
                subscription=subscription,
                amount=plan.price,
                currency=plan.currency,
                status=payment_status,
                provider=payment_provider,
                transaction_id=transaction_id or "",
                order_id=order_id or "",
                user=user,
                organization=organization,
                paid_at=starts_at if payment_status == Payment.STATUS_SUCCESS else None,
                notes=notes or "",
            )

        return subscription

    @staticmethod
    @transaction.atomic
    def activate(subscription):
        if subscription.has_expired():
            subscription.mark_expired()
            raise ValueError("An expired subscription cannot be activated.")
        subscription.activate()
        return subscription

    @staticmethod
    @transaction.atomic
    def suspend(subscription):
        if subscription.status in (Subscription.STATUS_CANCELLED, Subscription.STATUS_EXPIRED):
            raise ValueError("Cancelled or expired subscriptions cannot be suspended.")
        subscription.suspend()
        return subscription

    @staticmethod
    @transaction.atomic
    def cancel(subscription, reason=""):
        if subscription.status == Subscription.STATUS_CANCELLED:
            return subscription
        subscription.cancel(reason=reason)
        return subscription

    @staticmethod
    @transaction.atomic
    def expire_if_needed(subscription):
        if subscription.status == Subscription.STATUS_ACTIVE and subscription.has_expired():
            subscription.mark_expired()
        return subscription

    @staticmethod
    @transaction.atomic
    def renew(
        *,
        subscription,
        plan=None,
        granted_by=None,
        payment_status=Payment.STATUS_PENDING,
        payment_provider=Payment.PROVIDER_MANUAL,
        transaction_id="",
        order_id="",
        notes="",
    ):
        return SubscriptionService.create_subscription(
            plan=plan or subscription.plan,
            user=subscription.user,
            organization=subscription.organization,
            granted_by=granted_by,
            subscribed_by_admin=True,
            payment_status=payment_status,
            payment_provider=payment_provider,
            transaction_id=transaction_id,
            order_id=order_id,
            notes=notes,
            start_at=timezone.now(),
        )

    @staticmethod
    def get_expiring_subscriptions(days):
        now = timezone.now()
        start = now + timedelta(days=days)
        end = start + timedelta(days=1)
        return (
            Subscription.objects
            .select_related("user", "organization", "plan")
            .prefetch_related("entitlements__track", "entitlements__exam", "entitlements__course")
            .filter(
                user__isnull=False,
                status=Subscription.STATUS_ACTIVE,
                expires_at__isnull=False,
                expires_at__gte=start,
                expires_at__lt=end,
            )
            .order_by("expires_at")
        )

    @staticmethod
    @transaction.atomic
    def activate_subscription(subscription):
        now = timezone.now()
        if subscription.has_expired():
            subscription.mark_expired()
            raise ValueError("An expired subscription cannot be activated.")
        subscription.status = Subscription.STATUS_ACTIVE
        if not subscription.starts_at:
            subscription.starts_at = now
        subscription.cancelled_at = None
        subscription.save(update_fields=["status", "starts_at", "cancelled_at", "updated_at"])
        return subscription

    @staticmethod
    def get_user_resource_subscription(*, user, resource_type, resource):
        filters = {
            "subscription__user": user,
            "subscription__status": Subscription.STATUS_ACTIVE,
            "resource_type": resource_type,
            "is_active": True,
        }
        if resource_type == SubscriptionEntitlement.RESOURCE_EXAM:
            filters["exam"] = resource
        elif resource_type == SubscriptionEntitlement.RESOURCE_TRACK:
            filters["track"] = resource
        else:
            return None
        return (
            SubscriptionEntitlement.objects
            .select_related("subscription", "subscription__plan", "exam", "track")
            .filter(**filters)
            .order_by("-subscription__created_at")
            .first()
        )

    @staticmethod
    @transaction.atomic
    def create_or_reactivate_subscription(
        *,
        user,
        resource_type,
        resource,
        plan,
        granted_by=None,
        notes="",
    ):
        if not user:
            raise ValueError("User is required.")
        if not plan or not plan.is_active:
            raise ValueError("An active subscription plan is required.")
        if resource_type not in (
            SubscriptionEntitlement.RESOURCE_EXAM,
            SubscriptionEntitlement.RESOURCE_TRACK,
        ):
            raise ValueError("Invalid resource type.")
        if not resource:
            raise ValueError("Resource is required.")

        now = timezone.now()
        subscription = (
            Subscription.objects
            .filter(
                user=user,
                plan=plan,
                status=Subscription.STATUS_ACTIVE,
                starts_at__lte=now,
            )
            .filter(
                expires_at__isnull=True
            )
            .order_by("-created_at")
            .first()
        )
        if not subscription:
            subscription = (
                Subscription.objects
                .filter(
                    user=user,
                    plan=plan,
                    status=Subscription.STATUS_ACTIVE,
                    starts_at__lte=now,
                    expires_at__gt=now,
                )
                .order_by("-created_at")
                .first()
            )

        if not subscription:
            subscription = SubscriptionService.create_subscription(
                plan=plan,
                user=user,
                organization=None,
                granted_by=granted_by,
                subscribed_by_admin=True,
                payment_status="not_required",
                notes=notes,
                start_at=now,
            )
        else:
            SubscriptionService.activate_subscription(subscription)

        entitlement_filters = {
            "subscription": subscription,
            "resource_type": resource_type,
        }
        if resource_type == SubscriptionEntitlement.RESOURCE_EXAM:
            entitlement_filters["exam"] = resource
        else:
            entitlement_filters["track"] = resource

        entitlement = SubscriptionEntitlement.objects.filter(**entitlement_filters).first()
        if entitlement:
            if not entitlement.is_active:
                entitlement.is_active = True
                entitlement.save(update_fields=["is_active", "updated_at"])
        else:
            entitlement = SubscriptionEntitlement(
                subscription=subscription,
                resource_type=resource_type,
                is_active=True,
            )
            if resource_type == SubscriptionEntitlement.RESOURCE_EXAM:
                entitlement.exam = resource
            else:
                entitlement.track = resource
            entitlement.full_clean()
            entitlement.save()

        AccessService.grant_access(
            user=user,
            resource_type=resource_type,
            resource=resource,
            source=ResourceAccess.SOURCE_INDIVIDUAL,
            subscription=subscription,
            expires_at=subscription.expires_at,
        )
        return subscription, entitlement
