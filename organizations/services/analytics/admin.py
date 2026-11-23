# organizations/services/analytics/admin.py

import datetime
from django.db.models import Avg, Count, Q
from django.db.models.functions import TruncMonth
from django.utils import timezone

from courses.models import Course
from organizations.models import (
    AcademicYear,
    ClassSection,
    OrganizationClass,
    OrganizationMember,
    OrganizationRole,
    OrganizationAuditLog,
    ResourceAssignment,
    ClassResourceAssignment,
    StudentEnrollment,
)
from quiz.models import Category, Domain, Exam, ExamTrack, Question, UserExam
from .filters import parse_date_range


def get_admin_analytics(organization, date_range="30d"):
    """
    Calculate institution-wide analytics and visual chart datasets for
    organization owners and administrators.
    """
    start_dt, end_dt, active_range, range_label = parse_date_range(date_range)
    now = timezone.now()

    # 1. Organization People
    members = OrganizationMember.objects.filter(organization=organization, is_active=True)
    total_students = members.filter(role=OrganizationRole.STUDENT).count()
    total_teachers = members.filter(role=OrganizationRole.STAFF).count()
    total_admins = members.filter(role__in=OrganizationRole.administrative_roles()).count()

    # 2. Academic Structure
    academic_years_count = AcademicYear.objects.filter(organization=organization).count()
    classes_count = OrganizationClass.objects.filter(organization=organization, is_active=True).count()
    sections_count = ClassSection.objects.filter(organization=organization, is_active=True).count()

    # 3. Learning Catalog & Question Bank
    domains_count = Domain.objects.filter(organization=organization, is_active=True).count()
    categories_count = Category.objects.filter(organization=organization, is_active=True).count()
    questions_count = Question.objects.filter(organization=organization, is_active=True, is_deleted=False).count()
    courses_count = Course.objects.filter(organization=organization).count()
    published_courses_count = Course.objects.filter(organization=organization, is_published=True).count()
    tracks_count = ExamTrack.objects.filter(organization=organization).count()
    exams_count = Exam.objects.filter(organization=organization).count()

    # 4. Assignments & Lifecycle (filtered by date_range if requested)
    base_assignments = ResourceAssignment.objects.filter(organization=organization).exclude(
        status__in=[ResourceAssignment.STATUS_CANCELLED, ResourceAssignment.STATUS_REVOKED]
    )
    if start_dt is not None:
        period_assignments = base_assignments.filter(assigned_at__gte=start_dt)
    else:
        period_assignments = base_assignments

    total_assignments = period_assignments.count()
    completed_assignments = period_assignments.filter(status=ResourceAssignment.STATUS_COMPLETED).count()
    started_assignments = period_assignments.filter(status=ResourceAssignment.STATUS_STARTED).count()
    assigned_assignments = period_assignments.filter(status=ResourceAssignment.STATUS_ASSIGNED).count()

    overdue_assignments = (
        period_assignments.filter(due_at__isnull=False, due_at__lt=now, is_active=True)
        .count()
    )

    completion_rate = (
        round((completed_assignments / total_assignments) * 100, 1)
        if total_assignments > 0
        else 0.0
    )

    # 5. Exam Performance (scoped to organization students taking org exams)
    student_user_ids = members.filter(role=OrganizationRole.STUDENT).values_list("user_id", flat=True)
    base_user_exams = UserExam.objects.filter(
        user_id__in=student_user_ids,
        exam__organization=organization,
    )
    if start_dt is not None:
        period_user_exams = base_user_exams.filter(started_at__gte=start_dt)
    else:
        period_user_exams = base_user_exams

    exam_aggregates = period_user_exams.aggregate(
        total_attempts=Count("id"),
        submitted_attempts=Count("id", filter=Q(status=UserExam.STATUS_SUBMITTED)),
        avg_score=Avg("score", filter=Q(status=UserExam.STATUS_SUBMITTED, score__isnull=False)),
        passed_attempts=Count("id", filter=Q(status=UserExam.STATUS_SUBMITTED, passed=True)),
    )

    total_exam_attempts = exam_aggregates["total_attempts"] or 0
    submitted_exam_attempts = exam_aggregates["submitted_attempts"] or 0
    avg_exam_score = (
        round(exam_aggregates["avg_score"], 1)
        if exam_aggregates["avg_score"] is not None
        else None
    )
    passed_exam_attempts = exam_aggregates["passed_attempts"] or 0
    pass_rate = (
        round((passed_exam_attempts / submitted_exam_attempts) * 100, 1)
        if submitted_exam_attempts > 0
        else 0.0
    )

    # 6. Chart Datasets
    # 6a. Student Enrollment Trends (Monthly Database-Aggregated)
    enrollments_qs = StudentEnrollment.objects.filter(student__organization=organization)
    if start_dt is not None:
        enrollments_qs = enrollments_qs.filter(joined_at__gte=start_dt)

    monthly_enrollments = (
        enrollments_qs.annotate(period=TruncMonth("joined_at", tzinfo=datetime.timezone.utc))
        .values("period")
        .annotate(total=Count("id"))
        .order_by("period")
    )

    enrollment_chart_labels = []
    enrollment_chart_data = []
    for item in monthly_enrollments:
        p = item["period"]
        if p:
            enrollment_chart_labels.append(p.strftime("%b %Y"))
            enrollment_chart_data.append(item["total"])

    # 6b. Class & Section Student Distribution
    section_dist_qs = (
        StudentEnrollment.objects.filter(
            student__organization=organization,
            status=StudentEnrollment.STATUS_ACTIVE,
        )
        .values("class_section__class_group__name", "class_section__name")
        .annotate(total=Count("id"))
        .order_by("class_section__class_group__name", "class_section__name")[:10]
    )

    section_chart_labels = [
        f"{row['class_section__class_group__name']} - {row['class_section__name']}"
        for row in section_dist_qs
    ]
    section_chart_data = [row["total"] for row in section_dist_qs]

    # 6c. Assignment Status Chart
    assignment_status_labels = ["Completed", "In Progress", "Pending", "Overdue"]
    assignment_status_data = [
        completed_assignments,
        started_assignments,
        assigned_assignments,
        overdue_assignments,
    ]

    # 6d. Learning Products Breakdown
    course_assignments_count = period_assignments.filter(
        resource_type=ResourceAssignment.RESOURCE_COURSE
    ).count()
    track_assignments_count = period_assignments.filter(
        resource_type=ResourceAssignment.RESOURCE_TRACK
    ).count()
    exam_assignments_count = period_assignments.filter(
        resource_type=ResourceAssignment.RESOURCE_EXAM
    ).count()

    section_resources_base = ClassResourceAssignment.objects.filter(
        organization=organization,
        is_active=True,
    )
    if start_dt is not None:
        section_resources_base = section_resources_base.filter(created_at__gte=start_dt)

    sec_courses = section_resources_base.filter(
        resource_type=ClassResourceAssignment.RESOURCE_COURSE
    ).count()
    sec_tracks = section_resources_base.filter(
        resource_type=ClassResourceAssignment.RESOURCE_TRACK
    ).count()
    sec_exams = section_resources_base.filter(
        resource_type=ClassResourceAssignment.RESOURCE_EXAM
    ).count()

    product_labels = ["Courses", "Learning Tracks", "Exams"]
    product_data = [
        course_assignments_count + sec_courses,
        track_assignments_count + sec_tracks,
        exam_assignments_count + sec_exams,
    ]

    # 6e. Exam Performance Trends (Monthly Database-Aggregated Avg Score & Pass Rate)
    exam_trends_qs = (
        period_user_exams.filter(
            status=UserExam.STATUS_SUBMITTED,
            submitted_at__isnull=False,
        )
        .annotate(period=TruncMonth("submitted_at", tzinfo=datetime.timezone.utc))
        .values("period")
        .annotate(
            avg_score=Avg("score", filter=Q(score__isnull=False)),
            total=Count("id"),
            passed=Count("id", filter=Q(passed=True)),
        )
        .order_by("period")
    )

    exam_trend_labels = []
    exam_trend_scores = []
    exam_trend_pass_rates = []
    for row in exam_trends_qs:
        p = row["period"]
        if p:
            exam_trend_labels.append(p.strftime("%b %Y"))
            exam_trend_scores.append(round(row["avg_score"], 1) if row["avg_score"] is not None else 0.0)
            p_rate = round((row["passed"] / row["total"]) * 100, 1) if row["total"] > 0 else 0.0
            exam_trend_pass_rates.append(p_rate)

    # 7. Audit Activity & Recent Assignments
    recent_audit_logs = (
        OrganizationAuditLog.objects.filter(organization=organization)
        .select_related("actor")
        .order_by("-created_at")[:8]
    )

    recent_assignments = (
        base_assignments.select_related("student", "course", "track", "exam")
        .order_by("-assigned_at")[:8]
    )

    return {
        "active_range": active_range,
        "range_label": range_label,
        # KPI Cards
        "total_students": total_students,
        "total_teachers": total_teachers,
        "total_admins": total_admins,
        "academic_years_count": academic_years_count,
        "classes_count": classes_count,
        "sections_count": sections_count,
        "domains_count": domains_count,
        "categories_count": categories_count,
        "questions_count": questions_count,
        "courses_count": courses_count,
        "published_courses_count": published_courses_count,
        "tracks_count": tracks_count,
        "exams_count": exams_count,
        "total_assignments": total_assignments,
        "completed_assignments": completed_assignments,
        "started_assignments": started_assignments,
        "assigned_assignments": assigned_assignments,
        "overdue_assignments": overdue_assignments,
        "completion_rate": completion_rate,
        "total_exam_attempts": total_exam_attempts,
        "submitted_exam_attempts": submitted_exam_attempts,
        "avg_exam_score": avg_exam_score,
        "passed_exam_attempts": passed_exam_attempts,
        "pass_rate": pass_rate,
        # Chart JSON Payload
        "charts": {
            "enrollment_trends": {
                "labels": enrollment_chart_labels,
                "data": enrollment_chart_data,
                "has_data": bool(enrollment_chart_data and any(enrollment_chart_data)),
            },
            "section_distribution": {
                "labels": section_chart_labels,
                "data": section_chart_data,
                "has_data": bool(section_chart_data and any(section_chart_data)),
            },
            "assignment_status": {
                "labels": assignment_status_labels,
                "data": assignment_status_data,
                "has_data": bool(assignment_status_data and any(assignment_status_data)),
            },
            "product_distribution": {
                "labels": product_labels,
                "data": product_data,
                "has_data": bool(product_data and any(product_data)),
            },
            "exam_trends": {
                "labels": exam_trend_labels,
                "scores": exam_trend_scores,
                "pass_rates": exam_trend_pass_rates,
                "has_data": bool(exam_trend_labels),
            },
        },
        # Records for tables
        "recent_audit_logs": recent_audit_logs,
        "recent_assignments": recent_assignments,
    }
