from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from courses.models import Course
from quiz.models import ExamTrack
from subscriptions.models import Subscription, SubscriptionEntitlement, SubscriptionPlan
from subscriptions.services.subscription_service import SubscriptionService
from organizations.models.membership import OrganizationMember


class PublicResourceSubscriptionError(Exception):
    """Base error for organization public-resource subscriptions."""


class PublicResourceNotAvailableError(PublicResourceSubscriptionError):
    pass


class PublicResourcePlanError(PublicResourceSubscriptionError):
    pass


def _validate_actor(*, actor, organization):
    membership = OrganizationMember.objects.filter(
        user=actor,
        organization=organization,
        is_active=True,
    ).first()
    if not membership:
        raise PublicResourceSubscriptionError(
            "You are not an active member of this organization."
        )
    if not membership.can_manage_students:
        raise PublicResourceSubscriptionError(
            "You do not have permission to manage organization subscriptions."
        )


def get_public_resource(*, resource_type, resource_id):
    if resource_type == SubscriptionEntitlement.RESOURCE_COURSE:
        resource = Course.objects.filter(pk=resource_id).first()
        if not resource or not resource.is_publicly_available():
            raise PublicResourceNotAvailableError(
                "This public course is not currently available."
            )
        return resource

    if resource_type == SubscriptionEntitlement.RESOURCE_TRACK:
        resource = ExamTrack.objects.filter(
            pk=resource_id,
            organization__isnull=True,
            is_active=True,
        ).first()
        if not resource:
            raise PublicResourceNotAvailableError(
                "This public track is not currently available."
            )
        return resource

    raise PublicResourceNotAvailableError(
        "Only public Courses and Tracks can be subscribed to by an organization."
    )


def get_resource_plan(*, resource_type, resource, plan_id):
    if not plan_id:
        raise PublicResourcePlanError("A subscription plan is required.")

    if resource_type == SubscriptionEntitlement.RESOURCE_COURSE:
        plan = resource.subscription_plans.filter(
            pk=plan_id,
            is_active=True,
            product_type=SubscriptionPlan.PRODUCT_COURSE,
            access_mode=SubscriptionPlan.ACCESS_SINGLE_RESOURCE,
        ).first()
    elif resource_type == SubscriptionEntitlement.RESOURCE_TRACK:
        plan = resource.subscription_plans.filter(
            pk=plan_id,
            is_active=True,
            product_type=SubscriptionPlan.PRODUCT_TRACK,
            access_mode=SubscriptionPlan.ACCESS_SINGLE_RESOURCE,
        ).first()
    else:
        plan = None

    if not plan:
        raise PublicResourcePlanError(
            "The selected plan is not an active plan for this public resource."
        )
    return plan


@transaction.atomic
def subscribe_organization_to_public_resource(
    *,
    organization,
    actor,
    resource_type,
    resource_id,
    plan_id,
):
    """Create an organization subscription for one public Course/Track.

    This is the organization-admin provisioning path. Payment checkout can be
    connected later without changing the entitlement/assignment boundary.
    """
    if not organization or not organization.is_active:
        raise PublicResourceSubscriptionError(
            "An active organization is required."
        )

    _validate_actor(actor=actor, organization=organization)
    resource = get_public_resource(
        resource_type=resource_type,
        resource_id=resource_id,
    )
    plan = get_resource_plan(
        resource_type=resource_type,
        resource=resource,
        plan_id=plan_id,
    )

    now = timezone.now()
    existing = (
        SubscriptionEntitlement.objects
        .select_related("subscription")
        .filter(
            subscription__organization=organization,
            subscription__status=Subscription.STATUS_ACTIVE,
            subscription__starts_at__lte=now,
            resource_type=resource_type,
            is_active=True,
            **{
                "course" if resource_type == SubscriptionEntitlement.RESOURCE_COURSE else "track": resource,
            },
        )
        .filter(
            subscription__expires_at__isnull=True
        )
        .first()
    )
    if existing:
        return existing.subscription, existing, False

    existing = (
        SubscriptionEntitlement.objects
        .select_related("subscription")
        .filter(
            subscription__organization=organization,
            subscription__status=Subscription.STATUS_ACTIVE,
            subscription__starts_at__lte=now,
            subscription__expires_at__gt=now,
            resource_type=resource_type,
            is_active=True,
            **{
                "course" if resource_type == SubscriptionEntitlement.RESOURCE_COURSE else "track": resource,
            },
        )
        .first()
    )
    if existing:
        return existing.subscription, existing, False

    subscription = SubscriptionService.create_subscription(
        plan=plan,
        organization=organization,
        user=None,
        granted_by=actor,
        subscribed_by_admin=True,
        payment_status="success" if plan.price > 0 else "not_required",
        notes=f"Organization public {resource_type} subscription provisioned by {actor}.",
        start_at=now,
    )

    entitlement = SubscriptionEntitlement(
        subscription=subscription,
        resource_type=resource_type,
        is_active=True,
    )
    if resource_type == SubscriptionEntitlement.RESOURCE_COURSE:
        entitlement.course = resource
    else:
        entitlement.track = resource
    try:
        entitlement.full_clean()
        entitlement.save()
    except ValidationError:
        raise

    return subscription, entitlement, True
