from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from organizations.models import ClassTeacher, OrganizationMember, OrganizationStudent, StudentEnrollment
from organizations.models.role import OrganizationRole


class EnrollmentPermissionError(PermissionDenied):
    pass


def _membership(actor, organization):
    membership = OrganizationMember.objects.filter(user=actor, organization=organization, is_active=True).first()
    if not membership:
        raise EnrollmentPermissionError("Active organization membership is required.")
    return membership


def _teacher_can_manage_section(actor, section):
    membership = _membership(actor, section.organization)
    if membership.role in OrganizationRole.administrative_roles():
        return True
    if membership.role != OrganizationRole.STAFF:
        raise EnrollmentPermissionError("Only organization administrators or assigned teachers may manage enrollment.")
    return ClassTeacher.objects.filter(
        organization=section.organization,
        teacher=actor,
        class_section=section,
        academic_year=section.academic_year,
        is_active=True,
    ).exists()


@transaction.atomic
def enroll_student(*, actor, student, section, roll_number=None):
    if not isinstance(student, OrganizationStudent):
        raise ValidationError("Enrollment requires an organization student record.")
    if student.organization_id != section.organization_id:
        raise ValidationError("Student and class section must belong to the same organization.")
    if not _teacher_can_manage_section(actor, section):
        raise EnrollmentPermissionError("Teacher is not assigned to this class section.")
    if not student.status == OrganizationStudent.STATUS_ACTIVE:
        raise ValidationError("Only active organization students can be enrolled.")
    existing = StudentEnrollment.objects.filter(
        student=student, academic_year=section.academic_year, status=StudentEnrollment.STATUS_ACTIVE
    ).first()
    if existing:
        if existing.class_section_id == section.id:
            return existing
        raise ValidationError("Student already has an active enrollment in this academic year.")
    return StudentEnrollment.objects.create(
        student=student,
        academic_year=section.academic_year,
        class_section=section,
        roll_number=roll_number or "",
    )


@transaction.atomic
def transfer_student(*, actor, enrollment, section, roll_number=None):
    if enrollment.student.organization_id != section.organization_id:
        raise ValidationError("Student and class section must belong to the same organization.")
    if enrollment.academic_year_id != section.academic_year_id:
        raise ValidationError("Transfer must remain within the same academic year.")
    if not _teacher_can_manage_section(actor, section):
        raise EnrollmentPermissionError("Teacher is not assigned to the destination class section.")
    source_membership = _membership(actor, enrollment.student.organization)
    if source_membership.role == OrganizationRole.STAFF:
        if not ClassTeacher.objects.filter(
            organization=section.organization, teacher=actor, class_section=enrollment.class_section,
            academic_year=enrollment.academic_year, is_active=True,
        ).exists():
            raise EnrollmentPermissionError("Teacher is not assigned to the source class section.")
    if enrollment.status != StudentEnrollment.STATUS_ACTIVE:
        raise ValidationError("Only active enrollments can be transferred.")
    if enrollment.class_section_id == section.id:
        return enrollment
    enrollment.status = StudentEnrollment.STATUS_TRANSFERRED
    enrollment.save(update_fields=["status", "left_at"])
    return enroll_student(actor=actor, student=enrollment.student, section=section, roll_number=roll_number)


def assign_teacher_to_section(*, actor, teacher, section, academic_year, subject=None):
    membership = _membership(actor, section.organization)
    if membership.role not in OrganizationRole.administrative_roles():
        raise EnrollmentPermissionError("Only organization administrators may assign teachers to classes.")
    teacher_membership = OrganizationMember.objects.filter(
        user=teacher, organization=section.organization, role=OrganizationRole.STAFF, is_active=True
    ).exists()
    if not teacher_membership:
        raise ValidationError("Teacher must be an active Staff / Teacher member of the organization.")
    if academic_year.organization_id != section.organization_id or section.academic_year_id != academic_year.id:
        raise ValidationError("Academic year and class section must match the organization and section.")
    return ClassTeacher.objects.create(
        organization=section.organization,
        teacher=teacher,
        class_section=section,
        academic_year=academic_year,
        subject=subject or "",
    )
