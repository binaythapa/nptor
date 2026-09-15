from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from accounts.models import UserProfile
from organizations.models import OrganizationMember, OrganizationStudent
from organizations.models.role import OrganizationRole


def get_organization_student(user, organization):
    membership = OrganizationMember.objects.filter(user=user, organization=organization, is_active=True).first()
    if not membership or membership.role != OrganizationRole.STUDENT:
        raise PermissionDenied("An active student membership is required.")

    student, created = OrganizationStudent.objects.get_or_create(
        user=user,
        organization=organization,
        defaults={"status": OrganizationStudent.STATUS_ACTIVE, "joined_date": timezone.localdate()},
    )
    if not created and student.status != OrganizationStudent.STATUS_ACTIVE:
        student.status = OrganizationStudent.STATUS_ACTIVE
        student.save(update_fields=["status", "updated_at"])
    if student.status != OrganizationStudent.STATUS_ACTIVE:
        raise PermissionDenied("Student enrollment is required for this organization.")
    return student


def get_student_for_admin(student_id, organization):
    return (
        OrganizationStudent.objects
        .filter(
            id=student_id,
            organization=organization,
            user__organization_memberships__organization=organization,
            user__organization_memberships__role=OrganizationRole.STUDENT,
            user__organization_memberships__is_active=True,
        )
        .select_related("user", "organization")
        .first()
    )


def get_student_for_teacher(*, actor, student_id, organization):
    """Return a student only when the teacher is assigned to that student's class."""
    student = get_student_for_admin(student_id, organization)
    if not student:
        return None

    membership = OrganizationMember.objects.filter(user=actor, organization=organization, is_active=True).first()
    if not membership:
        raise PermissionDenied("Active organization membership is required.")
    if membership.role not in OrganizationRole.teaching_roles():
        raise PermissionDenied("Teacher access is required.")

    assigned = student.enrollments.filter(
        status="active",
        class_section__teacher_assignments__teacher=actor,
        class_section__teacher_assignments__organization=organization,
        class_section__teacher_assignments__is_active=True,
    ).exists()
    if not assigned:
        raise PermissionDenied("You can only access students in classes assigned to you.")
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

    if "contact_phone" in data:
        profile, _ = UserProfile.objects.get_or_create(user=student.user)
        profile.phone = data["contact_phone"] or None
        profile.save(update_fields=["phone", "updated_at"])
    return student


@transaction.atomic
def update_student_admin_profile(*, actor, organization, student, data):
    """Update organization-owned student identity and profile fields."""
    if student.organization_id != organization.id:
        raise PermissionDenied("Student belongs to another organization.")
    membership = OrganizationMember.objects.filter(user=actor, organization=organization, is_active=True).first()
    if not membership or membership.role not in OrganizationRole.administrative_roles():
        raise PermissionDenied("Organization administrator access is required.")
    student_membership = OrganizationMember.objects.filter(user=student.user, organization=organization, role=OrganizationRole.STUDENT, is_active=True).exists()
    if not student_membership:
        raise PermissionDenied("An active student membership is required.")

    user = student.user
    if "first_name" in data:
        user.first_name = data["first_name"]
    if "last_name" in data:
        user.last_name = data["last_name"]
    user.save(update_fields=["first_name", "last_name"])

    if "contact_phone" in data:
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.phone = data["contact_phone"] or None
        profile.save(update_fields=["phone", "updated_at"])

    editable = {"student_id", "admission_no", "status", "joined_date", "date_of_birth", "guardian_name", "guardian_phone", "address"}
    for field in editable:
        if field in data:
            setattr(student, field, data[field])
    student.save(update_fields=[field for field in editable if field in data] + ["updated_at"])
    return student
