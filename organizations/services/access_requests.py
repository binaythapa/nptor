from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from accounts.services.notifications import create_notification
from organizations.models.access_request import OrganizationAccessRequest
from organizations.models.membership import OrganizationMember
from organizations.models.role import OrganizationRole
from organizations.permissions import get_active_membership, is_platform_admin


User = get_user_model()


def _require_platform_admin(user):
    if not is_platform_admin(user):
        raise PermissionDenied("Platform administrator access required.")


def submit_access_request(user, organization, service=OrganizationAccessRequest.SERVICE_ORGANIZATION_ACCESS, requested_role=OrganizationRole.STUDENT, reason=""):
    if not user or not user.is_authenticated:
        raise PermissionDenied("Authentication is required.")
    if not organization or not organization.is_active:
        raise ValidationError("The organization is not available.")
    if requested_role and requested_role not in set(OrganizationRole.all_roles()):
        raise ValidationError("Invalid organization role.")
    if get_active_membership(user, organization):
        raise ValidationError("You already have active access to this organization.")

    access_request = OrganizationAccessRequest.objects.filter(
        user=user, organization=organization, service=service,
        requested_role=requested_role, status=OrganizationAccessRequest.STATUS_PENDING,
    ).first()
    if access_request:
        return access_request

    access_request = OrganizationAccessRequest.objects.create(
        user=user, organization=organization, service=service,
        requested_role=requested_role, reason=reason.strip(),
    )
    platform_admins = User.objects.filter(Q(is_superuser=True) | Q(profile__is_platform_admin=True)).distinct().only("id")
    for admin in platform_admins:
        create_notification(
            admin, "organization", "New organization access request",
            f"{user.get_username()} requested access to {organization.name}.",
            priority="warning", target_url=reverse("accounts:organization_requests"),
            dedupe_key=f"org-access-request:{access_request.pk}:{admin.pk}",
        )
    return access_request


def approve_access_request(request, reviewer, notes=""):
    _require_platform_admin(reviewer)
    with transaction.atomic():
        locked = OrganizationAccessRequest.objects.select_for_update().select_related("user", "organization").get(pk=request.pk)
        if locked.status == OrganizationAccessRequest.STATUS_APPROVED:
            return locked
        if locked.status != OrganizationAccessRequest.STATUS_PENDING:
            raise ValidationError("Only pending requests can be approved.")
        member, _ = OrganizationMember.objects.get_or_create(
            user=locked.user, organization=locked.organization,
            defaults={"role": locked.requested_role or OrganizationRole.STUDENT, "is_active": True},
        )
        member.role = locked.requested_role or OrganizationRole.STUDENT
        member.is_active = True
        member.save(update_fields=["role", "is_active", "updated_at"])
        locked.status = OrganizationAccessRequest.STATUS_APPROVED
        locked.reviewed_by = reviewer
        locked.reviewed_at = timezone.now()
        locked.review_notes = notes.strip()
        locked.save(update_fields=["status", "reviewed_by", "reviewed_at", "review_notes"])
    create_notification(locked.user, "organization", "Organization access approved", f"Your access to {locked.organization.name} has been approved.", priority="success", target_url=reverse("organizations_public:workspace", kwargs={"slug": locked.organization.slug}), dedupe_key=f"org-access-approved:{locked.pk}")
    return locked


def reject_access_request(request, reviewer, notes=""):
    _require_platform_admin(reviewer)
    with transaction.atomic():
        locked = OrganizationAccessRequest.objects.select_for_update().select_related("user", "organization").get(pk=request.pk)
        if locked.status == OrganizationAccessRequest.STATUS_REJECTED:
            return locked
        if locked.status != OrganizationAccessRequest.STATUS_PENDING:
            raise ValidationError("Only pending requests can be rejected.")
        locked.status = OrganizationAccessRequest.STATUS_REJECTED
        locked.reviewed_by = reviewer
        locked.reviewed_at = timezone.now()
        locked.review_notes = notes.strip()
        locked.save(update_fields=["status", "reviewed_by", "reviewed_at", "review_notes"])
    create_notification(locked.user, "organization", "Organization access request declined", f"Your request for {locked.organization.name} was not approved.", priority="warning", dedupe_key=f"org-access-rejected:{locked.pk}")
    return locked
