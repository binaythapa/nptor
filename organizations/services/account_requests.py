from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from accounts.services.notifications import create_notification
from organizations.models.account_request import OrganizationAccountRequest
from organizations.models.membership import OrganizationMember
from organizations.models.organization import Organization
from organizations.models.role import OrganizationRole

User = get_user_model()


def _require_platform_admin(user):
    if not user or not user.is_authenticated or not user.is_staff:
        raise PermissionDenied("Platform administrator access required.")


def _unique_organization_slug(name):
    base = slugify(name) or "organization"
    slug = base
    suffix = 2
    while Organization.objects.filter(slug=slug).exists():
        slug = f"{base}-{suffix}"
        suffix += 1
    return slug


def submit_organization_account_request(user, data):
    if not user or not user.is_authenticated:
        raise PermissionDenied("Authentication is required.")
    if OrganizationMember.objects.filter(
        user=user,
        is_active=True,
        role__in=OrganizationRole.administrative_roles(),
    ).exists():
        raise ValidationError("You already have an active organization account.")

    pending = OrganizationAccountRequest.objects.filter(
        user=user,
        status=OrganizationAccountRequest.STATUS_PENDING,
    ).first()
    if pending:
        return pending

    request = OrganizationAccountRequest.objects.create(
        user=user,
        organization_name=data["organization_name"].strip(),
        org_type=data["org_type"],
        website=(data.get("website") or "").strip(),
        contact_email=data["contact_email"].strip(),
        contact_phone=(data.get("contact_phone") or "").strip(),
        address=(data.get("address") or "").strip(),
        city=(data.get("city") or "").strip(),
        country=(data.get("country") or "").strip(),
        description=(data.get("description") or "").strip(),
        reason=(data.get("reason") or "").strip(),
    )

    admins = User.objects.filter(is_staff=True).only("id")
    for admin in admins:
        create_notification(
            admin,
            "organization",
            "New organization account request",
            f"{user.get_username()} requested an organization account for {request.organization_name}.",
            priority="warning",
            target_url=reverse("accounts:organization-account-requests"),
            dedupe_key=f"org-account-request:{request.pk}:{admin.pk}",
        )
    return request


def approve_organization_account_request(request, reviewer, notes=""):
    _require_platform_admin(reviewer)
    with transaction.atomic():
        locked = OrganizationAccountRequest.objects.select_for_update().select_related("user").get(pk=request.pk)
        if locked.status == OrganizationAccountRequest.STATUS_APPROVED:
            return locked
        if locked.status != OrganizationAccountRequest.STATUS_PENDING:
            raise ValidationError("Only pending requests can be approved.")
        if OrganizationMember.objects.filter(
            user=locked.user,
            is_active=True,
            role__in=OrganizationRole.administrative_roles(),
        ).exists():
            raise ValidationError("The requester already has an active organization account.")

        organization = Organization.objects.create(
            name=locked.organization_name.strip(),
            slug=_unique_organization_slug(locked.organization_name),
            org_type=locked.org_type,
            is_active=True,
            created_by=locked.user,
        )
        OrganizationMember.objects.create(
            user=locked.user,
            organization=organization,
            role=OrganizationRole.ORG_OWNER,
            is_active=True,
        )
        locked.organization = organization
        locked.status = OrganizationAccountRequest.STATUS_APPROVED
        locked.reviewed_by = reviewer
        locked.reviewed_at = timezone.now()
        locked.review_notes = notes.strip()
        locked.save(update_fields=["organization", "status", "reviewed_by", "reviewed_at", "review_notes", "updated_at"])

    create_notification(
        locked.user,
        "organization",
        "Organization account approved",
        f"Your organization account for {locked.organization.name} has been approved.",
        priority="success",
        target_url=reverse("organizations_public:workspace", kwargs={"slug": locked.organization.slug}),
        dedupe_key=f"org-account-approved:{locked.pk}",
    )
    return locked


def reject_organization_account_request(request, reviewer, notes=""):
    _require_platform_admin(reviewer)
    with transaction.atomic():
        locked = OrganizationAccountRequest.objects.select_for_update().select_related("user").get(pk=request.pk)
        if locked.status == OrganizationAccountRequest.STATUS_REJECTED:
            return locked
        if locked.status != OrganizationAccountRequest.STATUS_PENDING:
            raise ValidationError("Only pending requests can be rejected.")
        locked.status = OrganizationAccountRequest.STATUS_REJECTED
        locked.reviewed_by = reviewer
        locked.reviewed_at = timezone.now()
        locked.review_notes = notes.strip()
        locked.save(update_fields=["status", "reviewed_by", "reviewed_at", "review_notes", "updated_at"])

    create_notification(
        locked.user,
        "organization",
        "Organization account request declined",
        f"Your organization account request for {locked.organization_name} was not approved.",
        priority="warning",
        dedupe_key=f"org-account-rejected:{locked.pk}",
    )
    return locked
