from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from organizations.permissions import org_admin_required
from organizations.models.assignment import ResourceAssignment
from organizations.models.membership import OrganizationMember
from organizations.models.access import ResourceAccess

from courses.models import Course
from quiz.models import Exam, ExamTrack


# =====================================================
# LIST ASSIGNMENTS
# =====================================================
from django.db.models import Count
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from organizations.permissions import org_admin_required
from organizations.models.assignment import ResourceAssignment
from organizations.models.membership import OrganizationMember, OrganizationGroup


@org_admin_required
def org_assignments(request, slug):

    org = request.organization

    assignments = ResourceAssignment.objects.filter(
        organization=org
    ).select_related(
        "student", "group", "course", "track", "exam"
    ).order_by("-assigned_at")

    # ================= FILTERS =================

    student_id = request.GET.get("student")
    group_id = request.GET.get("group")
    resource_type = request.GET.get("type")

    if student_id:
        assignments = assignments.filter(student_id=student_id)

    if group_id:
        assignments = assignments.filter(group_id=group_id)

    if resource_type:
        assignments = assignments.filter(resource_type=resource_type)

    # ================= ANALYTICS =================

    total_assignments = assignments.count()

    group_counts = (
        OrganizationMember.objects
        .filter(organization=org, role="student", is_active=True)
        .values("group__name")
        .annotate(count=Count("id"))
    )

    # ================= FILTER DATA =================

    students = OrganizationMember.objects.filter(
        organization=org,
        role="student",
        is_active=True
    )

    groups = OrganizationGroup.objects.filter(
        organization=org,
        is_active=True
    )

    return render(
        request,
        "organizations/admin/assignments/list.html",
        {
            "assignments": assignments,
            "org": org,
            "students": students,
            "groups": groups,
            "total_assignments": total_assignments,
            "group_counts": group_counts,
        }
    )


# ================= BULK DELETE =================

@org_admin_required
def org_assignment_bulk_delete(request, slug):

    org = request.organization

    ids = request.POST.getlist("assignment_ids")

    ResourceAssignment.objects.filter(
        id__in=ids,
        organization=org
    ).delete()

    messages.success(request, "Selected assignments removed.")

    return redirect("organizations_admin:assignments", slug=slug)





# =====================================================
# CREATE ASSIGNMENT
# =====================================================

@org_admin_required
def org_assignment_create(request, slug):

    org = request.organization

    # ---------------- STUDENTS ----------------

    students = (
        OrganizationMember.objects
        .filter(
            organization=org,
            role="student",
            is_active=True
        )
        .select_related("user")
    )

    # ---------------- COURSES ----------------

    courses = (
        Course.objects
        .filter(
            organization_subscriptions__organization=org,
            organization_subscriptions__is_active=True
        )
        .distinct()
    )

    # ---------------- TRACKS ----------------

    tracks = (
        ExamTrack.objects
        .filter(organization=org)
        .order_by("title")
    )

    # ---------------- EXAMS ----------------

    exams = (
        Exam.objects
        .filter(organization=org)
        .order_by("title")
    )

    # =================================================
    # POST
    # =================================================

    if request.method == "POST":

        student_id = request.POST.get("student_id")
        resource_type = request.POST.get("resource_type")

        student = get_object_or_404(
            OrganizationMember,
            id=student_id,
            organization=org,
            role="student"
        )

        user = student.user

        # ------------------------------------------------
        # COURSE ASSIGNMENT
        # ------------------------------------------------

        if resource_type == "course":

            course_id = request.POST.get("course_id")

            course = get_object_or_404(
                Course,
                id=course_id,
                organization_subscriptions__organization=org
            )

            # Assignment record
            ResourceAssignment.objects.get_or_create(
                student=user,
                organization=org,
                resource_type="course",
                course=course
            )

            # Access record
            access, created = ResourceAccess.objects.get_or_create(
                user=user,
                resource_type="course",
                course=course,
                source="organization",
                organization=org,
                defaults={"is_active": True},
            )

            if not created and not access.is_active:
                access.is_active = True
                access.save(update_fields=["is_active"])

            messages.success(
                request,
                f"{course.title} assigned to {user.email}"
            )

        # ------------------------------------------------
        # TRACK ASSIGNMENT
        # ------------------------------------------------

        elif resource_type == "track":

            track_id = request.POST.get("track_id")

            track = get_object_or_404(
                ExamTrack,
                id=track_id,
                organization=org
            )

            ResourceAssignment.objects.get_or_create(
                student=user,
                organization=org,
                resource_type="track",
                track=track
            )

            ResourceAccess.objects.get_or_create(
                user=user,
                resource_type="track",
                track=track,
                source="organization",
                organization=org,
                defaults={"is_active": True},
            )

            messages.success(
                request,
                f"{track.title} assigned to {user.email}"
            )

        # ------------------------------------------------
        # EXAM ASSIGNMENT
        # ------------------------------------------------

        elif resource_type == "exam":

            exam_id = request.POST.get("exam_id")

            exam = get_object_or_404(
                Exam,
                id=exam_id,
                organization=org
            )

            ResourceAssignment.objects.get_or_create(
                student=user,
                organization=org,
                resource_type="exam",
                exam=exam
            )

            ResourceAccess.objects.get_or_create(
                user=user,
                resource_type="exam",
                exam=exam,
                source="organization",
                organization=org,
                defaults={"is_active": True},
            )

            messages.success(
                request,
                f"{exam.title} assigned to {user.email}"
            )

        return redirect(
            "organizations_admin:assignments",
            slug=slug
        )

    # =================================================
    # GET
    # =================================================

    return render(
        request,
        "organizations/admin/assignments/create.html",
        {
            "students": students,
            "courses": courses,
            "tracks": tracks,
            "exams": exams,
            "org": org
        }
    )


# =====================================================
# REMOVE ASSIGNMENT
# =====================================================

@org_admin_required
def org_assignment_remove(request, slug, assignment_id):

    org = request.organization

    assignment = get_object_or_404(
        ResourceAssignment,
        id=assignment_id,
        organization=org
    )

    assignment.delete()

    messages.success(
        request,
        "Assignment removed successfully."
    )

    return redirect(
        "organizations_admin:assignments",
        slug=slug
    )