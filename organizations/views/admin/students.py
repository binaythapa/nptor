from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.views.decorators.http import require_POST

from organizations.forms.student import OrganizationStudentAdminProfileForm
from organizations.forms.academic import StudentEnrollmentForm, StudentEnrollmentUpdateForm, StudentEnrollmentTransferForm
from organizations.permissions import org_admin_required, org_teacher_required
from organizations.models import OrganizationStudent, StudentEnrollment
from organizations.models.access import ResourceAccess
from organizations.models.assignment import ResourceAssignment
from organizations.models.membership import OrganizationMember
from organizations.models.role import OrganizationRole
from organizations.services.enrollment import enroll_student, transfer_student


User = get_user_model()


def _get_active_org_student(request, student_id):
    org = request.organization
    student = get_object_or_404(
        OrganizationStudent.objects.select_related("user", "user__profile"),
        id=student_id,
        organization=org,
        status=OrganizationStudent.STATUS_ACTIVE,
    )
    get_object_or_404(
        OrganizationMember,
        organization=org,
        user=student.user,
        role=OrganizationRole.STUDENT,
        is_active=True,
    )
    return student


def _role_options_for(actor_member, target_member):
    """Return role choices the actor may assign to this target."""
    if not actor_member or not actor_member.is_active:
        return []

    if actor_member.id == target_member.id:
        return []

    if target_member.role == OrganizationRole.ORG_OWNER:
        return []

    if actor_member.role == OrganizationRole.ORG_OWNER:
        return [
            (OrganizationRole.STUDENT, OrganizationRole.STUDENT.label),
            (OrganizationRole.STAFF, OrganizationRole.STAFF.label),
            (OrganizationRole.ORG_ADMIN, OrganizationRole.ORG_ADMIN.label),
        ]

    if actor_member.role == OrganizationRole.ORG_ADMIN:
        if target_member.role in OrganizationRole.administrative_roles():
            return []
        return [
            (OrganizationRole.STUDENT, OrganizationRole.STUDENT.label),
            (OrganizationRole.STAFF, OrganizationRole.STAFF.label),
        ]

    return []


def _can_change_role(actor_member, target_member, new_role):
    """Enforce role transitions independently of the template/UI."""
    allowed_values = {value for value, _label in _role_options_for(actor_member, target_member)}
    return new_role in allowed_values


@org_teacher_required
def org_students(request, slug):
    org = request.organization
    members = list(
        OrganizationMember.objects.filter(organization=org)
        .select_related("user")
        .order_by("role", "user__username")
    )
    student_profiles = OrganizationStudent.objects.filter(
        organization=org,
        user_id__in=[member.user_id for member in members],
        status=OrganizationStudent.STATUS_ACTIVE,
    ).values_list("user_id", "id")
    profile_ids = dict(student_profiles)
    actor_member = request.organization_member
    for member in members:
        member.student_profile_id = profile_ids.get(member.user_id)
        member.role_options = _role_options_for(actor_member, member)
        member.can_edit_role = bool(member.role_options)
    return render(
        request,
        "organizations/admin/students/list.html",
        {"members": members, "org": org},
    )


@org_admin_required
def org_student_detail(request, slug, student_id):
    student = _get_active_org_student(request, student_id)
    enrollments = list(
        StudentEnrollment.objects.filter(student=student)
        .select_related("academic_year", "class_section", "class_section__class_group")
        .order_by("-academic_year__start_date", "-joined_at")
    )
    current_enrollment = next((item for item in enrollments if item.status == StudentEnrollment.STATUS_ACTIVE), None)
    return render(request, "organizations/admin/students/detail.html", {"org": request.organization, "student": student, "profile": getattr(student.user, "profile", None), "enrollments": enrollments, "current_enrollment": current_enrollment})


@org_admin_required
def org_student_detail_edit(request, slug, student_id):
    student = _get_active_org_student(request, student_id)
    if request.method == "POST":
        form = OrganizationStudentAdminProfileForm(request.POST, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, "Student profile updated successfully.")
            return redirect("organizations_admin:student_detail", slug=slug, student_id=student.id)
    else:
        form = OrganizationStudentAdminProfileForm(instance=student)
    return render(request, "organizations/admin/students/edit.html", {"org": request.organization, "student": student, "form": form})


@org_teacher_required
def org_student_enroll(request, slug, student_id):
    student = _get_active_org_student(request, student_id)
    if StudentEnrollment.objects.filter(student=student, status=StudentEnrollment.STATUS_ACTIVE).exists():
        messages.info(request, "This student already has an active enrollment. Use Edit or Transfer to update it.")
        return redirect("organizations_admin:student_detail", slug=slug, student_id=student.id)
    form = StudentEnrollmentForm(request.POST or None, organization=request.organization)
    if request.method == "POST" and form.is_valid():
        try:
            enroll_student(actor=request.user, student=student, section=form.cleaned_data["class_section"], roll_number=form.cleaned_data["roll_number"])
            messages.success(request, "Student enrolled successfully.")
            return redirect("organizations_admin:student_detail", slug=slug, student_id=student.id)
        except Exception as exc:
            form.add_error(None, str(exc))
    return render(request, "organizations/admin/students/enrollment_form.html", {"org": request.organization, "student": student, "form": form, "mode": "enroll", "title": "Enroll Student"})


@org_teacher_required
def org_student_enrollment_edit(request, slug, student_id, enrollment_id):
    student = _get_active_org_student(request, student_id)
    enrollment = get_object_or_404(StudentEnrollment, id=enrollment_id, student=student, status=StudentEnrollment.STATUS_ACTIVE)
    form = StudentEnrollmentUpdateForm(request.POST or None, instance=enrollment)
    if request.method == "POST" and form.is_valid():
        enrollment = form.save(commit=False)
        enrollment.left_at = timezone.now() if enrollment.status != StudentEnrollment.STATUS_ACTIVE else None
        enrollment.save(update_fields=["roll_number", "status", "left_at"])
        messages.success(request, "Enrollment updated successfully.")
        return redirect("organizations_admin:student_detail", slug=slug, student_id=student.id)
    return render(request, "organizations/admin/students/enrollment_form.html", {"org": request.organization, "student": student, "enrollment": enrollment, "form": form, "mode": "edit", "title": "Update Enrollment"})


@org_teacher_required
def org_student_enrollment_transfer(request, slug, student_id, enrollment_id):
    student = _get_active_org_student(request, student_id)
    enrollment = get_object_or_404(StudentEnrollment.objects.select_related("academic_year", "class_section"), id=enrollment_id, student=student, status=StudentEnrollment.STATUS_ACTIVE)
    form = StudentEnrollmentTransferForm(request.POST or None, organization=request.organization, academic_year=enrollment.academic_year, current_section=enrollment.class_section, initial_roll_number=enrollment.roll_number)
    if request.method == "POST" and form.is_valid():
        try:
            transfer_student(actor=request.user, enrollment=enrollment, section=form.cleaned_data["class_section"], roll_number=form.cleaned_data["roll_number"])
            messages.success(request, "Student transferred successfully.")
            return redirect("organizations_admin:student_detail", slug=slug, student_id=student.id)
        except Exception as exc:
            form.add_error(None, str(exc))
    return render(request, "organizations/admin/students/enrollment_form.html", {"org": request.organization, "student": student, "enrollment": enrollment, "form": form, "mode": "transfer", "title": "Transfer Student"})


@org_teacher_required
def org_student_add(request, slug):
    org = request.organization
    if request.method == "GET":
        return render(request, "organizations/admin/students/add.html", {"org": org})
    email = (request.POST.get("email") or "").strip().lower()
    role = request.POST.get("role", OrganizationRole.STUDENT)
    if request.organization_member.role == OrganizationRole.STAFF:
        if role != OrganizationRole.STUDENT:
            messages.error(request, "Staff / Teacher members can add students only.")
            return redirect("organizations_admin:students", slug=slug)
    elif role not in {OrganizationRole.STUDENT, OrganizationRole.STAFF}:
        messages.error(request, "Invalid organization role.")
        return redirect("organizations_admin:students", slug=slug)
    user = User.objects.filter(email__iexact=email).first()
    if not user:
        messages.error(request, "User with this email does not exist.")
        return redirect("organizations_admin:students", slug=slug)
    member, created = OrganizationMember.objects.get_or_create(user=user, organization=org, defaults={"role": role, "is_active": True})
    if not created and request.organization_member.role == OrganizationRole.STAFF and member.role != OrganizationRole.STUDENT:
        messages.error(request, "Staff / Teacher members cannot change another staff member's role.")
        return redirect("organizations_admin:students", slug=slug)
    if not created:
        member.role = role
        member.is_active = True
        member.save(update_fields=["role", "is_active"])
    if member.role == OrganizationRole.STUDENT and member.is_active:
        student, created = OrganizationStudent.objects.get_or_create(organization=org, user=user, defaults={"status": OrganizationStudent.STATUS_ACTIVE, "joined_date": timezone.localdate()})
        if not created and student.status != OrganizationStudent.STATUS_ACTIVE:
            student.status = OrganizationStudent.STATUS_ACTIVE
            student.save(update_fields=["status", "updated_at"])
    messages.success(request, f"{user.email} added to organization.")
    return redirect("organizations_admin:students", slug=slug)


@org_admin_required
@require_POST
def org_student_update_role(request, slug, member_id):
    org = request.organization
    actor_member = request.organization_member
    member = get_object_or_404(OrganizationMember, id=member_id, organization=org)
    new_role = request.POST.get("role")

    if not _can_change_role(actor_member, member, new_role):
        messages.error(request, "You are not authorized to assign this role to this member.")
        return redirect("organizations_admin:students", slug=slug)

    member.role = new_role
    member.save(update_fields=["role", "updated_at"])
    if new_role == OrganizationRole.STUDENT and member.is_active:
        student, created = OrganizationStudent.objects.get_or_create(organization=org, user=member.user, defaults={"status": OrganizationStudent.STATUS_ACTIVE, "joined_date": timezone.localdate()})
        if not created and student.status != OrganizationStudent.STATUS_ACTIVE:
            student.status = OrganizationStudent.STATUS_ACTIVE
            student.save(update_fields=["status", "updated_at"])
    elif new_role in {OrganizationRole.STAFF, OrganizationRole.ORG_ADMIN}:
        OrganizationStudent.objects.filter(organization=org, user=member.user).update(status=OrganizationStudent.STATUS_INACTIVE, updated_at=timezone.now())
    messages.success(request, "Role updated successfully.")
    return redirect("organizations_admin:students", slug=slug)


@org_teacher_required
@require_POST
def org_student_remove(request, slug, member_id):
    org = request.organization
    member = get_object_or_404(OrganizationMember, id=member_id, organization=org)
    if member.role in OrganizationRole.administrative_roles():
        messages.error(request, "Cannot remove an organization administrator here.")
        return redirect("organizations_admin:students", slug=slug)
    if request.organization_member.role == OrganizationRole.STAFF and member.role != OrganizationRole.STUDENT:
        messages.error(request, "Staff / Teacher members can remove students only.")
        return redirect("organizations_admin:students", slug=slug)
    now = timezone.now()
    ResourceAssignment.objects.filter(student=member.user, organization=org, is_active=True).update(is_active=False, status=ResourceAssignment.STATUS_REVOKED, revoked_at=now, revoked_by=request.user, revoke_reason="Student removed from organization.")
    ResourceAccess.objects.filter(user=member.user, organization=org, source=ResourceAccess.SOURCE_ORGANIZATION, is_active=True).update(is_active=False, revoked_at=now)
    if member.role == OrganizationRole.STUDENT:
        OrganizationStudent.objects.filter(organization=org, user=member.user).update(status=OrganizationStudent.STATUS_INACTIVE, updated_at=now)
    member.delete()
    messages.success(request, "Student removed from organization.")
    return redirect("organizations_admin:students", slug=slug)
