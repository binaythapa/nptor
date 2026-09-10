from django.core.exceptions import PermissionDenied

from organizations.models import ClassTeacher, OrganizationMember, OrganizationStudent
from organizations.models.role import OrganizationRole


def get_organization_student(user, organization):
    membership = OrganizationMember.objects.filter(user=user, organization=organization, is_active=True).first()
    if not membership or membership.role != OrganizationRole.STUDENT:
        raise PermissionDenied("An active student membership is required.")
    student = OrganizationStudent.objects.filter(
        user=user, organization=organization, status=OrganizationStudent.STATUS_ACTIVE
    ).select_related("user", "organization").first()
    if not student:
        raise PermissionDenied("Student enrollment is required for this organization.")
    return student


def get_student_for_admin(student_id, organization):
    return OrganizationStudent.objects.filter(id=student_id, organization=organization).select_related("user", "organization").first()


def get_student_for_teacher(*, actor, student_id, organization):
    student = get_student_for_admin(student_id, organization)
    if not student:
        return None
    membership = OrganizationMember.objects.filter(user=actor, organization=organization, is_active=True).first()
    if not membership:
        raise PermissionDenied("Active organization membership is required.")
    if membership.role in OrganizationRole.administrative_roles():
        return student
    if membership.role != OrganizationRole.STAFF:
        raise PermissionDenied("Teacher access is required.")
    allowed = student.enrollments.filter(
        status="active",
        class_section__teacher_assignments__teacher=actor,
        class_section__teacher_assignments__is_active=True,
    ).exists()
    if not allowed:
        raise PermissionDenied("Teacher is not assigned to this student's class.")
    return student


def update_student_profile(*, actor, organization, student, data):
    if student.organization_id != organization.id:
        raise PermissionDenied("Student belongs to another organization.")
    if actor.id != student.user_id:
        membership = OrganizationMember.objects.filter(user=actor, organization=organization, is_active=True).first()
        if not membership or membership.role not in OrganizationRole.administrative_roles():
            raise PermissionDenied("You cannot edit this student profile.")
    forbidden = {"student_id", "admission_no", "status", "organization", "enrollments", "class_section", "roll_number", "joined_date"}
    if forbidden.intersection(data.keys()):
        raise PermissionDenied("Enrollment and administrative fields cannot be edited here.")
    editable = {"date_of_birth", "guardian_name", "guardian_phone", "address"}
    for field in editable:
        if field in data:
            setattr(student, field, data[field])
    student.save(update_fields=[field for field in editable if field in data] + ["updated_at"])
    if "first_name" in data or "last_name" in data:
        user = student.user
        if "first_name" in data:
            user.first_name = data["first_name"]
        if "last_name" in data:
            user.last_name = data["last_name"]
        user.save(update_fields=["first_name", "last_name"])
    return student
