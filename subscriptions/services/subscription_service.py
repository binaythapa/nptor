# subscriptions/services/subscription_service.py

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from subscriptions.models import (
    Payment,
    Subscription,
    SubscriptionEntitlement,
    SubscriptionPlan,
)

from subscriptions.services.access_service import AccessService
from organizations.models.access import ResourceAccess

class SubscriptionService:
    """
    Centralized subscription lifecycle service.

    Views should call this service instead of directly
    manipulating Subscription objects.

    This keeps subscription/business logic independent
    from Django views, admin pages, APIs, payment gateways,
    payment providers, etc.
    """

    # =========================================================
    # CREATE SUBSCRIPTION
    # =========================================================

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
        """
        Create a subscription for either:

            user
        OR
            organization

        Exactly one owner is required.

        The plan's price and currency are copied into the
        subscription as a historical snapshot.

        A Payment record is created when appropriate.
        """

        # -----------------------------------------------------
        # Validate plan
        # -----------------------------------------------------

        if not plan:
            raise ValueError(
                "A subscription plan is required."
            )

        if not plan.is_active:
            raise ValueError(
                "The selected subscription plan is inactive."
            )

        # -----------------------------------------------------
        # Validate owner
        # -----------------------------------------------------

        if user is not None and organization is not None:
            raise ValueError(
                "A subscription cannot belong to both "
                "a user and an organization."
            )

        if user is None and organization is None:
            raise ValueError(
                "A subscription must belong to either "
                "a user or an organization."
            )

        # -----------------------------------------------------
        # Start time
        # -----------------------------------------------------

        starts_at = (
            start_at
            or timezone.now()
        )

        # -----------------------------------------------------
        # Calculate expiry
        # -----------------------------------------------------

        if plan.duration_days is None:

            # Lifetime subscription
            expires_at = None

        else:

            expires_at = (
                starts_at
                + timedelta(
                    days=plan.duration_days
                )
            )

        # -----------------------------------------------------
        # Create subscription
        # -----------------------------------------------------

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
                else (
                    "paid"
                    if payment_status
                    == Payment.STATUS_SUCCESS
                    else "pending"
                )
            ),

            subscribed_by_admin=(
                subscribed_by_admin
            ),

            granted_by=granted_by,

            notes=notes or "",
        )

        # -----------------------------------------------------
        # Create payment record
        # -----------------------------------------------------

        if plan.price > 0:

            Payment.objects.create(
                subscription=subscription,

                amount=plan.price,

                currency=plan.currency,

                status=payment_status,

                provider=payment_provider,

                transaction_id=(
                    transaction_id
                    or ""
                ),

                order_id=(
                    order_id
                    or ""
                ),

                user=user,

                organization=organization,

                paid_at=(
                    starts_at
                    if payment_status
                    == Payment.STATUS_SUCCESS
                    else None
                ),

                notes=notes or "",
            )

        return subscription

    # =========================================================
    # ACTIVATE
    # =========================================================

    @staticmethod
    @transaction.atomic
    def activate(subscription):
        """
        Activate an existing subscription.
        """

        if subscription.has_expired():

            subscription.mark_expired()

            raise ValueError(
                "An expired subscription cannot be activated."
            )

        subscription.activate()

        return subscription

    # =========================================================
    # SUSPEND
    # =========================================================

    @staticmethod
    @transaction.atomic
    def suspend(subscription):
        """
        Temporarily suspend a subscription.
        """

        if subscription.status in (
            Subscription.STATUS_CANCELLED,
            Subscription.STATUS_EXPIRED,
        ):
            raise ValueError(
                "Cancelled or expired subscriptions "
                "cannot be suspended."
            )

        subscription.suspend()

        return subscription

    # =========================================================
    # CANCEL
    # =========================================================

    @staticmethod
    @transaction.atomic
    def cancel(
        subscription,
        reason="",
    ):
        """
        Cancel a subscription.
        """

        if subscription.status == (
            Subscription.STATUS_CANCELLED
        ):
            return subscription

        subscription.cancel(
            reason=reason
        )

        return subscription

    # =========================================================
    # EXPIRE
    # =========================================================

    @staticmethod
    @transaction.atomic
    def expire_if_needed(
        subscription,
    ):
        """
        Mark an active subscription as expired when
        its expiration time has passed.
        """

        if (
            subscription.status
            == Subscription.STATUS_ACTIVE
            and subscription.has_expired()
        ):

            subscription.mark_expired()

        return subscription

    # =========================================================
    # RENEW
    # =========================================================

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
        """
        Create a new subscription for a renewal.

        The old subscription is preserved for historical
        and billing purposes.

        If no new plan is supplied, the existing plan is used.
        """

        renewal_plan = (
            plan
            or subscription.plan
        )

        # -----------------------------------------------------
        # Renewal should begin now
        # -----------------------------------------------------

        starts_at = timezone.now()

        # -----------------------------------------------------
        # Create new subscription
        # -----------------------------------------------------

        renewed_subscription = (
            SubscriptionService.create_subscription(
                plan=renewal_plan,

                user=subscription.user,

                organization=(
                    subscription.organization
                ),

                granted_by=granted_by,

                subscribed_by_admin=True,

                payment_status=payment_status,

                payment_provider=payment_provider,

                transaction_id=transaction_id,

                order_id=order_id,

                notes=notes,

                start_at=starts_at,
            )
        )

        return renewed_subscription

    # =========================================================
    # EXPIRING SUBSCRIPTIONS
    # =========================================================

    @staticmethod
    def get_expiring_subscriptions(days):
        """
        Return active user subscriptions that expire
        within the specified day window.

        Only user subscriptions are returned because
        expiry notifications are currently intended
        for individual users.
        """

        now = timezone.now()

        start = (
            now
            + timedelta(days=days)
        )

        end = (
            start
            + timedelta(days=1)
        )

        return (
            Subscription.objects
            .select_related(
                "user",
                "organization",
                "plan",
            )
            .prefetch_related(
                "entitlements__track",
                "entitlements__exam",
                "entitlements__course",
            )
            .filter(
                user__isnull=False,
                status=Subscription.STATUS_ACTIVE,
                expires_at__isnull=False,
                expires_at__gte=start,
                expires_at__lt=end,
            )
            .order_by(
                "expires_at"
            )
        )

    # =========================================================
    # ACTIVATE / REACTIVATE
    # =========================================================

    @staticmethod
    @transaction.atomic
    def activate_subscription(
        subscription,
    ):
        """
        Activate or reactivate an existing subscription.

        Used when an existing subscription is being reused
        for another entitlement.
        """

        now = timezone.now()

        if subscription.has_expired():

            subscription.mark_expired()

            raise ValueError(
                "An expired subscription cannot be activated."
            )

        subscription.status = (
            Subscription.STATUS_ACTIVE
        )

        if not subscription.starts_at:

            subscription.starts_at = now

        subscription.cancelled_at = None

        subscription.save(
            update_fields=[
                "status",
                "starts_at",
                "cancelled_at",
                "updated_at",
            ]
        )

        return subscription

    # =========================================================
    # FIND USER RESOURCE SUBSCRIPTION
    # =========================================================

    @staticmethod
    def get_user_resource_subscription(
        *,
        user,
        resource_type,
        resource,
    ):
        """
        Find the latest active user subscription containing
        the requested exam or track entitlement.
        """

        filters = {
            "subscription__user": user,

            "subscription__status": (
                Subscription.STATUS_ACTIVE
            ),

            "resource_type": resource_type,

            "is_active": True,
        }

        if (
            resource_type
            == SubscriptionEntitlement.RESOURCE_EXAM
        ):

            filters["exam"] = resource

        elif (
            resource_type
            == SubscriptionEntitlement.RESOURCE_TRACK
        ):

            filters["track"] = resource

        else:

            return None

        return (
            SubscriptionEntitlement.objects
            .select_related(
                "subscription",
                "subscription__plan",
                "exam",
                "track",
            )
            .filter(
                **filters
            )
            .order_by(
                "-subscription__created_at"
            )
            .first()
        )

    # =========================================================
    # CREATE / REACTIVATE SUBSCRIPTION
    # =========================================================

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
        """
        Create a new user subscription and entitlement,
        or reuse an existing active subscription for the
        same plan.

        Subscription:

            Billing / lifecycle

        Entitlement:

            Actual exam or track included in subscription.
        """

        # -----------------------------------------------------
        # Validate user
        # -----------------------------------------------------

        if not user:
            raise ValueError(
                "User is required."
            )

        # -----------------------------------------------------
        # Validate plan
        # -----------------------------------------------------

        if not plan:
            raise ValueError(
                "An active subscription plan is required."
            )

        if not plan.is_active:
            raise ValueError(
                "The selected subscription plan is inactive."
            )

        # -----------------------------------------------------
        # Validate resource type
        # -----------------------------------------------------

        if resource_type not in (
            SubscriptionEntitlement.RESOURCE_EXAM,
            SubscriptionEntitlement.RESOURCE_TRACK,
        ):

            raise ValueError(
                "Invalid resource type."
            )

        # -----------------------------------------------------
        # Validate resource
        # -----------------------------------------------------

        if not resource:
            raise ValueError(
                "Resource is required."
            )

        now = timezone.now()

        # -----------------------------------------------------
        # Find existing active lifetime subscription
        # -----------------------------------------------------

        subscription = (
            Subscription.objects
            .filter(
                user=user,

                plan=plan,

                status=Subscription.STATUS_ACTIVE,

                starts_at__lte=now,

                expires_at__isnull=True,
            )
            .order_by(
                "-created_at"
            )
            .first()
        )

        # -----------------------------------------------------
        # Find existing active time-limited subscription
        # -----------------------------------------------------

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
                .order_by(
                    "-created_at"
                )
                .first()
            )

        # -----------------------------------------------------
        # Create subscription if none exists
        # -----------------------------------------------------

        if not subscription:

            subscription = (
                SubscriptionService.create_subscription(
                    plan=plan,

                    user=user,

                    organization=None,

                    granted_by=granted_by,

                    subscribed_by_admin=True,

                    payment_status="not_required",

                    notes=notes,

                    start_at=now,
                )
            )

        else:

            SubscriptionService.activate_subscription(
                subscription
            )

        # -----------------------------------------------------
        # Find existing entitlement
        # -----------------------------------------------------

        entitlement_filters = {
            "subscription": subscription,

            "resource_type": resource_type,
        }

        if (
            resource_type
            == SubscriptionEntitlement.RESOURCE_EXAM
        ):

            entitlement_filters["exam"] = resource

        elif (
            resource_type
            == SubscriptionEntitlement.RESOURCE_TRACK
        ):

            entitlement_filters["track"] = resource

        entitlement = (
            SubscriptionEntitlement.objects
            .filter(
                **entitlement_filters
            )
            .first()
        )







        # -----------------------------------------------------
        # Reactivate existing entitlement
        # -----------------------------------------------------

        if entitlement:

            if not entitlement.is_active:

                entitlement.is_active = True

                entitlement.save(
                    update_fields=[
                        "is_active",
                        "updated_at",
                    ]
                )

        # -----------------------------------------------------
        # Create new entitlement
        # -----------------------------------------------------

        else:

            entitlement = SubscriptionEntitlement(
                subscription=subscription,
                resource_type=resource_type,
                is_active=True,
            )

            if (
                resource_type
                == SubscriptionEntitlement.RESOURCE_EXAM
            ):

                entitlement.exam = resource

            elif (
                resource_type
                == SubscriptionEntitlement.RESOURCE_TRACK
            ):

                entitlement.track = resource

            entitlement.full_clean()
            entitlement.save()

        # =====================================================
        # GRANT ACTUAL USER ACCESS
        # =====================================================
        #
        # SubscriptionEntitlement describes what the
        # subscription contains.
        #
        # ResourceAccess represents actual user access.
        #
        # Therefore every successful individual subscription
        # must also create/reactivate ResourceAccess.
        # =====================================================

        AccessService.grant_access(
            user=user,
            resource_type=resource_type,
            resource=resource,
            source=ResourceAccess.SOURCE_INDIVIDUAL,
            subscription=subscription,
            expires_at=subscription.expires_at,
        )

        # -----------------------------------------------------
        # Return subscription + entitlement
        # -----------------------------------------------------

        return (
            subscription,
            entitlement,
        )