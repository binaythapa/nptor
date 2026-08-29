from django.core.exceptions import ValidationError
from django.db import transaction

from subscriptions.models import Subscription, SubscriptionEntitlement
from subscriptions.services.access_service import AccessService


class CourseAccessService:
    """
    Course-specific access operations built on top of the
    platform-wide subscription system.
    """

    RESOURCE_TYPE = SubscriptionEntitlement.RESOURCE_COURSE

    # =========================================================
    # CHECK USER COURSE ACCESS
    # =========================================================

    @staticmethod
    def has_access(user, course, organization=None):
        """
        Check whether the user currently has access to a course.

        Access can come from:
        - individual subscription
        - organization assignment
        - other ResourceAccess sources
        """

        return AccessService.has_access(
            user=user,
            resource_type=CourseAccessService.RESOURCE_TYPE,
            resource=course,
            organization=organization,
        )

    # =========================================================
    # GRANT COURSE ACCESS
    # =========================================================

    @staticmethod
    @transaction.atomic
    def grant_access(
        *,
        user,
        subscription,
        course,
        source="individual",
        organization=None,
    ):
        """
        Grant a course entitlement through a subscription.
        """

        if not subscription.is_valid():
            raise ValidationError(
                "Subscription is not currently active."
            )

        entitlement, created = (
            SubscriptionEntitlement.objects.get_or_create(
                subscription=subscription,
                resource_type=CourseAccessService.RESOURCE_TYPE,
                course=course,
                defaults={
                    "is_active": True,
                },
            )
        )

        if not entitlement.is_active:
            entitlement.is_active = True
            entitlement.save(
                update_fields=[
                    "is_active",
                    "updated_at",
                ]
            )

        access, access_created = (
            AccessService.grant_from_entitlement(
                user=user,
                entitlement=entitlement,
                source=source,
                organization=organization,
            )
        )

        return {
            "entitlement": entitlement,
            "access": access,
            "created": created,
            "access_created": access_created,
        }

    # =========================================================
    # REVOKE COURSE ACCESS
    # =========================================================

    @staticmethod
    @transaction.atomic
    def revoke_access(
        *,
        user,
        course,
        source=None,
        organization=None,
    ):
        return AccessService.revoke_access(
            user=user,
            resource_type=CourseAccessService.RESOURCE_TYPE,
            resource=course,
            source=source,
            organization=organization,
        )