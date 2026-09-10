"""Authorization helpers for organization-owned learning content."""

from organizations.models.role import OrganizationRole
from organizations.permissions import get_active_membership


def user_can_manage_owned_content(user, organization, resource):
    """Return whether a member may mutate an organization-owned resource.

    Owners and admins may manage any resource owned by the organization.
    Staff/teachers may manage only resources they personally created.
    Students and users without an active membership are denied.
    """
    membership = get_active_membership(user, organization)
    if not membership:
        return False

    if getattr(resource, "organization_id", None) != organization.id:
        return False

    if membership.role in OrganizationRole.administrative_roles():
        return True

    return (
        membership.role == OrganizationRole.STAFF
        and getattr(resource, "created_by_id", None) == user.id
    )
