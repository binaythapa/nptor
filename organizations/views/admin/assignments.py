from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Count, Avg
from django.utils.dateparse import parse_datetime
from django.utils.timezone import now, timedelta
from django.http import HttpResponse

from collections import defaultdict
import csv

from organizations.permissions import org_admin_required
from organizations.models.assignment import ResourceAssignment, UserProgress
from organizations.models.membership import OrganizationMember, OrganizationGroup

from courses.models import Course
from quiz.models import Exam, ExamTrack


# =====================================================
# ASSIGN RESOURCE (CLEAN LOGIC)
# =====================================================

def assign_resource(
    org,
    request_user,
    user=None,
    group=None,
    resource_type=None,
    course=None,
    track=None,
    exam=None,
    deadline=None,
    overwrite=False
):

    assignment, created = ResourceAssignment.objects.get_or_create(
        student=user if not group else None,
        group=group if group else None,
        organization=org,
        resource_type=resource_type,
        course=course,
        track=track,
        exam=exam,
        defaults={
            "assigned_by": request_user,
            "deadline": deadline
        }
    )

    # 🚫 Duplicate
    if not created and not overwrite:
        return assignment, "exists"

    # 🔁 Overwrite
    if not created and overwrite:
        assignment.deadline = deadline
        assignment.version += 1
        assignment.save()
        return assignment, "overwritten"

    return assignment, "created"


# =====================================================
# CREATE ASSIGNMENT
# =====================================================

@org_admin_required
def org_assignment_create(request, slug):

    org = request.organization

    students = OrganizationMember.objects.filter(
        organization=org,
        role="student",
        is_active=True
    ).select_related("user")

    groups = OrganizationGroup.objects.filter(
        organization=org,
        is_active=True
    )

    courses = Course.objects.filter(
        organization_subscriptions__organization=org,
        organization_subscriptions__is_active=True
    ).distinct()

    tracks = ExamTrack.objects.filter(organization=org).order_by("title")
    exams = Exam.objects.filter(organization=org).order_by("title")

    if request.method == "POST":

        student_id = request.POST.get("student_id")
        group_id = request.POST.get("group_id")
        resource_type = request.POST.get("resource_type")
        deadline = parse_datetime(request.POST.get("deadline"))

        if not resource_type:
            messages.error(request, "Please select resource type.")
            return redirect("organizations_admin:assignment_create", slug=slug)

        if not student_id and not group_id:
            messages.error(request, "Please select student or group.")
            return redirect("organizations_admin:assignment_create", slug=slug)

        if student_id and group_id:
            messages.error(request, "Select either student OR group.")
            return redirect("organizations_admin:assignment_create", slug=slug)

        group = None
        user = None

        if group_id:
            group = get_object_or_404(OrganizationGroup, id=group_id, organization=org)

        if student_id:
            student = get_object_or_404(
                OrganizationMember,
                id=student_id,
                organization=org,
                role="student"
            )
            user = student.user

        def get_count():
            return OrganizationMember.objects.filter(
                organization=org,
                group=group,
                role="student"
            ).count() if group else 1

        if resource_type == "course":
            course = get_object_or_404(Course, id=request.POST.get("course_id"))

            _, status = assign_resource(
                org, request.user, user, group,
                "course", course=course,
                deadline=deadline, overwrite=True
            )

            messages.success(request, f"{course.title} → {get_count()} users ({status})")

        elif resource_type == "track":
            track = get_object_or_404(ExamTrack, id=request.POST.get("track_id"), organization=org)

            _, status = assign_resource(
                org, request.user, user, group,
                "track", track=track,
                deadline=deadline, overwrite=True
            )

            messages.success(request, f"{track.title} → {get_count()} users ({status})")

        elif resource_type == "exam":
            exam = get_object_or_404(Exam, id=request.POST.get("exam_id"), organization=org)

            _, status = assign_resource(
                org, request.user, user, group,
                "exam", exam=exam,
                deadline=deadline, overwrite=True
            )

            messages.success(request, f"{exam.title} → {get_count()} users ({status})")

        return redirect("organizations_admin:assignments", slug=slug)

    return render(request, "organizations/admin/assignments/create.html", {
        "students": students,
        "groups": groups,
        "courses": courses,
        "tracks": tracks,
        "exams": exams,
    })


# =====================================================
# LIST ASSIGNMENTS
# =====================================================
from django.core.paginator import Paginator

@org_admin_required
def org_assignments(request, slug):

    org = request.organization

    assignments = ResourceAssignment.objects.filter(
        organization=org
    ).select_related(
        "student", "group", "course", "track", "exam"
    ).prefetch_related("userprogress_set")

    # ================= SEARCH =================
    search = request.GET.get("search")
    if search:
        assignments = assignments.filter(
            course__title__icontains=search
        ) | assignments.filter(
            group__name__icontains=search
        ) | assignments.filter(
            student__email__icontains=search
        )

    # ================= SORT =================
    sort = request.GET.get("sort", "-assigned_at")

    if sort == "progress":
        assignments = sorted(assignments, key=lambda a: getattr(a, "avg_progress", 0), reverse=True)
    else:
        assignments = assignments.order_by(sort)

    # ================= PAGINATION =================
    paginator = Paginator(assignments, 10)  # 10 per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # ================= GROUPING =================
    grouped = defaultdict(lambda: {"type": "", "title": "", "assignments": []})

    for a in page_obj:

        progresses = a.userprogress_set.all()

        a.avg_progress = round(
            sum(p.progress_percent for p in progresses) / progresses.count(), 1
        ) if progresses else 0

        a.is_completed = all(p.is_completed for p in progresses) if progresses else False

        if a.course:
            key = f"course_{a.course.id}"
            grouped[key]["type"] = "course"
            grouped[key]["title"] = a.course.title

        elif a.track:
            key = f"track_{a.track.id}"
            grouped[key]["type"] = "track"
            grouped[key]["title"] = a.track.title

        elif a.exam:
            key = f"exam_{a.exam.id}"
            grouped[key]["type"] = "exam"
            grouped[key]["title"] = a.exam.title

        grouped[key]["assignments"].append(a)

    return render(request, "organizations/admin/assignments/list.html", {
        "grouped_resources": dict(grouped),
        "students": OrganizationMember.objects.filter(organization=org),
        "groups": OrganizationGroup.objects.filter(organization=org),
        "total_assignments": assignments.count(),
        "page_obj": page_obj,
        "search": search,
        "sort": sort,
        "now": now()
    })
# =====================================================
# BULK DELETE
# =====================================================

@org_admin_required
def org_assignment_bulk_delete(request, slug):

    ResourceAssignment.objects.filter(
        id__in=request.POST.getlist("assignment_ids"),
        organization=request.organization
    ).delete()

    messages.success(request, "Selected assignments removed.")
    return redirect("organizations_admin:assignments", slug=slug)


# =====================================================
# REMOVE SINGLE
# =====================================================

@org_admin_required
def org_assignment_remove(request, slug, assignment_id):

    assignment = get_object_or_404(
        ResourceAssignment,
        id=assignment_id,
        organization=request.organization
    )

    assignment.delete()
    messages.success(request, "Assignment removed.")
    return redirect("organizations_admin:assignments", slug=slug)


# =====================================================
# DASHBOARD
# =====================================================

@org_admin_required
def org_assignment_dashboard(request, slug):

    org = request.organization
    assignments = ResourceAssignment.objects.filter(organization=org)

    # FILTERS
    if request.GET.get("group"):
        assignments = assignments.filter(group_id=request.GET.get("group"))

    if request.GET.get("course"):
        assignments = assignments.filter(course_id=request.GET.get("course"))

    # EXPORT
    if request.GET.get("export") == "csv":
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="assignments.csv"'

        writer = csv.writer(response)
        writer.writerow(["Type", "Target", "Deadline"])

        for a in assignments:
            writer.writerow([
                a.resource_type,
                a.group.name if a.group else a.student.email,
                a.deadline
            ])

        return response

    # CHART DATA
    course_data = assignments.values("course__title", "course_id").annotate(count=Count("id"))

    progress_qs = UserProgress.objects.filter(assignment__in=assignments)

    return render(request, "organizations/admin/assignment_dashboard.html", {
        "course_labels": [c["course__title"] or "Unknown" for c in course_data],
        "course_counts": [c["count"] for c in course_data],
        "course_ids": [c["course_id"] for c in course_data],
        "completed": progress_qs.filter(is_completed=True).count(),
        "pending": progress_qs.filter(is_completed=False).count(),
        "groups": OrganizationGroup.objects.filter(organization=org),
        "courses": Course.objects.all(),
    })