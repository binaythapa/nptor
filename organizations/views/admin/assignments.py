from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Count

from organizations.permissions import org_admin_required
from organizations.models.assignment import ResourceAssignment
from organizations.models.membership import OrganizationMember, OrganizationGroup
from organizations.models.access import ResourceAccess

from courses.models import Course
from quiz.models import Exam, ExamTrack


# =====================================================
# LIST ASSIGNMENTS
# =====================================================

from collections import defaultdict

from collections import defaultdict
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Count

from organizations.permissions import org_admin_required
from organizations.models.assignment import ResourceAssignment
from organizations.models.membership import OrganizationMember, OrganizationGroup

from collections import defaultdict

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

    # ================= GROUP BY RESOURCE (🔥 MAIN LOGIC) =================

    grouped_resources = defaultdict(lambda: {
        "type": "",
        "title": "",
        "assignments": []
    })

    for a in assignments:

        # Identify resource
        if a.course:
            key = f"course_{a.course.id}"
            grouped_resources[key]["type"] = "course"
            grouped_resources[key]["title"] = a.course.title

        elif a.track:
            key = f"track_{a.track.id}"
            grouped_resources[key]["type"] = "track"
            grouped_resources[key]["title"] = a.track.title

        elif a.exam:
            key = f"exam_{a.exam.id}"
            grouped_resources[key]["type"] = "exam"
            grouped_resources[key]["title"] = a.exam.title

        grouped_resources[key]["assignments"].append(a)

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
            "grouped_resources": dict(grouped_resources),  # 🔥 IMPORTANT
            "org": org,
            "students": students,
            "groups": groups,
            "total_assignments": total_assignments,
            "group_counts": group_counts,
        }
    )

# =====================================================
# BULK DELETE
# =====================================================

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
# CREATE ASSIGNMENT (FINAL)
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

    # ---------------- GROUPS ----------------
    groups = OrganizationGroup.objects.filter(
        organization=org,
        is_active=True
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
    tracks = ExamTrack.objects.filter(
        organization=org
    ).order_by("title")

    # ---------------- EXAMS ----------------
    exams = Exam.objects.filter(
        organization=org
    ).order_by("title")

    # =================================================
    # POST
    # =================================================

    if request.method == "POST":

        student_id = request.POST.get("student_id")
        group_id = request.POST.get("group_id")
        resource_type = request.POST.get("resource_type")

        # ================= VALIDATION =================

        if not student_id and not group_id:
            messages.error(request, "Please select student or group.")
            return redirect("organizations_admin:assignment_create", slug=slug)

        if student_id and group_id:
            messages.error(request, "Select either student OR group.")
            return redirect("organizations_admin:assignment_create", slug=slug)

        users = []

        # ================= TARGET =================

        if group_id:
            group = get_object_or_404(
                OrganizationGroup,
                id=group_id,
                organization=org
            )

            members = OrganizationMember.objects.filter(
                organization=org,
                group=group,
                role="student",
                is_active=True
            ).select_related("user")

            users = [m.user for m in members]

        else:
            student = get_object_or_404(
                OrganizationMember,
                id=student_id,
                organization=org,
                role="student"
            )
            users = [student.user]

        # =================================================
        # ASSIGNMENT LOGIC
        # =================================================

        def assign_resource(user, resource_type, course=None, track=None, exam=None):

            ResourceAssignment.objects.get_or_create(
                student=user,
                organization=org,
                resource_type=resource_type,
                course=course,
                track=track,
                exam=exam
            )

            ResourceAccess.objects.get_or_create(
                user=user,
                resource_type=resource_type,
                course=course,
                track=track,
                exam=exam,
                source="organization",
                organization=org,
                defaults={"is_active": True},
            )

        # ---------------- COURSE ----------------
        if resource_type == "course":

            course = get_object_or_404(
                Course,
                id=request.POST.get("course_id"),
                organization_subscriptions__organization=org
            )

            for user in users:
                assign_resource(user, "course", course=course)

            messages.success(
                request,
                f"{course.title} assigned to {len(users)} student(s)"
            )

        # ---------------- TRACK ----------------
        elif resource_type == "track":

            track = get_object_or_404(
                ExamTrack,
                id=request.POST.get("track_id"),
                organization=org
            )

            for user in users:
                assign_resource(user, "track", track=track)

            messages.success(
                request,
                f"{track.title} assigned to {len(users)} student(s)"
            )

        # ---------------- EXAM ----------------
        elif resource_type == "exam":

            exam = get_object_or_404(
                Exam,
                id=request.POST.get("exam_id"),
                organization=org
            )

            for user in users:
                assign_resource(user, "exam", exam=exam)

            messages.success(
                request,
                f"{exam.title} assigned to {len(users)} student(s)"
            )

        return redirect("organizations_admin:assignments", slug=slug)

    # =================================================
    # GET
    # =================================================

    return render(
        request,
        "organizations/admin/assignments/create.html",
        {
            "students": students,
            "groups": groups,   # 🔥 IMPORTANT FIX
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

    messages.success(request, "Assignment removed successfully.")

    return redirect("organizations_admin:assignments", slug=slug)