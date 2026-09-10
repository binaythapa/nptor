from django.core.exceptions import PermissionDenied, ValidationError

from organizations.models import ClassResourceAssignment, ClassTeacher, OrganizationMember
from organizations.models.role import OrganizationRole


def _actor_can_assign(actor, section):
    membership = OrganizationMember.objects.filter(user=actor, organization=section.organization, is_active=True).first()
    if not membership:
        raise PermissionDenied("Active organization membership is required.")
    if membership.role in OrganizationRole.administrative_roles():
        return
    if membership.role == OrganizationRole.STAFF and ClassTeacher.objects.filter(
        organization=section.organization, teacher=actor, class_section=section,
        academic_year=section.academic_year, is_active=True,
    ).exists():
        return
    raise PermissionDenied("Teacher is not assigned to this class section.")


def assign_class_resource(*, actor, section, resource_type, resource, starts_at=None, due_at=None, expires_at=None):
    _actor_can_assign(actor, section)
    if getattr(resource, "organization_id", None) not in (None, section.organization_id):
        raise ValidationError("Resource belongs to another organization.")
    kwargs = dict(organization=section.organization, class_section=section, assigned_by=actor, resource_type=resource_type, starts_at=starts_at, due_at=due_at, expires_at=expires_at)
    if resource_type == ClassResourceAssignment.RESOURCE_COURSE:
        kwargs["course"] = resource
    elif resource_type == ClassResourceAssignment.RESOURCE_TRACK:
        kwargs["track"] = resource
    elif resource_type == ClassResourceAssignment.RESOURCE_EXAM:
        kwargs["exam"] = resource
    else:
        raise ValidationError("Invalid resource type.")
    obj = ClassResourceAssignment(**kwargs)
    obj.full_clean()
    obj.save()
    return obj


def student_has_class_resource_access(*, student, organization, resource_type, resource):
    from organizations.models import StudentEnrollment
    if getattr(student, "id", None) is None:
        return False
    if getattr(resource, "organization_id", None) not in (None, organization.id):
        return False
    resource_field = {ClassResourceAssignment.RESOURCE_COURSE: "course_id", ClassResourceAssignment.RESOURCE_TRACK: "track_id", ClassResourceAssignment.RESOURCE_EXAM: "exam_id"}.get(resource_type)
    if not resource_field:
        return False
    resource_id = resource.id
    sections = StudentEnrollment.objects.filter(
        student__user=student,
        student__organization=organization,
        student__status="active",
        status=StudentEnrollment.STATUS_ACTIVE,
        class_section__is_active=True,
    ).values_list("class_section_id", flat=True)
    return ClassResourceAssignment.objects.filter(
        organization=organization,
        class_section_id__in=sections,
        resource_type=resource_type,
        **{resource_field: resource_id},
        is_active=True,
    ).exists()
