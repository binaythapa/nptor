from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from organizations.models.membership import OrganizationMember
from subscriptions.models import Payment, Subscription, SubscriptionEntitlement
from subscriptions.services.subscription_service import SubscriptionService

from .payment_gateway import get_payment_gateway
from .public_resource_subscriptions import (
    get_public_resource,
    get_resource_plan,
)


class PublicResourceCheckoutError(Exception):
    """Base error for organization public-resource checkout."""


class PublicResourceCheckout:
    def __init__(self, *, subscription, payment, checkout_url, reference):
        self.subscription = subscription
        self.payment = payment
        self.checkout_url = checkout_url
        self.reference = reference


def _validate_actor(*, actor, organization):
    membership = OrganizationMember.objects.filter(
        user=actor,
        organization=organization,
        is_active=True,
    ).first()
    if not membership or not membership.can_manage_students:
        raise PublicResourceCheckoutError(
            "You do not have permission to start organization checkout."
        )


@transaction.atomic
def create_organization_checkout(
    *,
    organization,
    actor,
    resource_type,
    resource_id,
    plan_id,
):
    if not organization or not organization.is_active:
        raise PublicResourceCheckoutError("An active organization is required.")

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
    # Do not create a second pending checkout for the same organization,
    # resource, and plan while the existing payment is still awaiting payment.
    resource_field = (
        "course" if resource_type == SubscriptionEntitlement.RESOURCE_COURSE else "track"
    )
    pending_payment = (
        Payment.objects
        .select_related("subscription")
        .filter(
            organization=organization,
            status=Payment.STATUS_PENDING,
            subscription__status=Subscription.STATUS_PENDING,
            subscription__plan=plan,
            **{f"subscription__entitlements__{resource_field}": resource},
        )
        .order_by("-created_at")
        .first()
    )
    gateway = get_payment_gateway()
    if pending_payment:
        checkout = gateway.create_checkout(payment=pending_payment)
        return PublicResourceCheckout(
            subscription=pending_payment.subscription,
            payment=pending_payment,
            checkout_url=checkout.checkout_url,
            reference=checkout.reference,
        )

    subscription = Subscription.objects.create(
        plan=plan,
        organization=organization,
        user=None,
        status=Subscription.STATUS_PENDING,
        starts_at=now,
        expires_at=None,
        amount=plan.price,
        currency=plan.currency,
        payment_status=("not_required" if plan.price == 0 else "pending"),
        subscribed_by_admin=False,
        notes=f"Organization checkout for public {resource_type}.",
    )

    entitlement = SubscriptionEntitlement(
        subscription=subscription,
        resource_type=resource_type,
        is_active=True,
    )
    if resource_type == SubscriptionEntitlement.RESOURCE_COURSE:
        entitlement.course = resource
    elif resource_type == SubscriptionEntitlement.RESOURCE_TRACK:
        entitlement.track = resource
    else:
        raise PublicResourceCheckoutError(
            "Only public Courses and Tracks can be checked out."
        )
    try:
        entitlement.full_clean()
        entitlement.save()
    except ValidationError as exc:
        raise PublicResourceCheckoutError(str(exc)) from exc

    payment = Payment.objects.create(
        subscription=subscription,
        amount=plan.price,
        currency=plan.currency,
        status=Payment.STATUS_PENDING,
        provider=getattr(gateway, "provider", Payment.PROVIDER_MANUAL),
        transaction_id="",
        order_id=f"NPTOR-ORG-{subscription.pk}",
        user=None,
        organization=organization,
        notes=f"Dummy checkout for public {resource_type}.",
    )
    checkout = gateway.create_checkout(payment=payment)
    return PublicResourceCheckout(
        subscription=subscription,
        payment=payment,
        checkout_url=checkout.checkout_url,
        reference=checkout.reference,
    )


@transaction.atomic
def complete_organization_checkout(payment_id, *, actor, reference=None):
    payment = (
        Payment.objects
        .select_for_update()
        .select_related("subscription", "organization")
        .filter(pk=payment_id)
        .first()
    )
    if not payment:
        raise PublicResourceCheckoutError("Payment was not found.")
    if payment.organization_id is None:
        raise PublicResourceCheckoutError("This payment is not an organization checkout.")
    _validate_actor(actor=actor, organization=payment.organization)

    if payment.status == Payment.STATUS_SUCCESS:
        return payment.subscription
    if payment.status != Payment.STATUS_PENDING:
        raise PublicResourceCheckoutError("This checkout is no longer payable.")

    gateway = get_payment_gateway()
    reference = reference or f"DUMMY-{payment.pk}"
    if not gateway.verify_payment(payment=payment, reference=reference):
        raise PublicResourceCheckoutError("Payment verification failed.")

    subscription = payment.subscription
    subscription.starts_at = timezone.now()
    subscription.expires_at = SubscriptionService.calculate_expiry(
        subscription.plan,
        subscription.starts_at,
    )
    subscription.status = Subscription.STATUS_ACTIVE
    subscription.payment_status = "paid"
    subscription.payment_id = reference
    subscription.subscribed_by_admin = False
    subscription.save(
        update_fields=[
            "starts_at",
            "expires_at",
            "status",
            "payment_status",
            "payment_id",
            "subscribed_by_admin",
            "updated_at",
        ]
    )

    payment.status = Payment.STATUS_SUCCESS
    payment.transaction_id = reference
    payment.paid_at = timezone.now()
    payment.save(update_fields=["status", "transaction_id", "paid_at", "updated_at"])

    for entitlement in subscription.entitlements.filter(is_active=True):
        # The entitlement already exists in pending state; activation is valid
        # now that its parent subscription is active.
        entitlement.is_active = True
        entitlement.save(update_fields=["is_active", "updated_at"])

    return subscription
