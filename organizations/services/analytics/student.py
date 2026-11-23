# organizations/services/analytics/student.py

from django.db.models import Avg, Count, Q
from django.utils import timezone

from organizations.models import (
    ClassResourceAssignment,
    OrganizationStudent,
    ResourceAssignment,
    StudentEnrollment,
)
from quiz.models import UserExam


def get_student_analytics(organization, student_user):
    """
    Calculate role-restricted learning analytics and progression for an individual student.

    Strictly isolated:
      - Only the authenticated student's assignments, enrollments, and exam attempts.
      - No peer rankings, other students' scores, or staff administrative metrics.
    """
    now = timezone.now()

    # 1. Profile and Enrolled Sections
    student_profile = (
        OrganizationStudent.objects.filter(
            organization=organization,
            user=student_user,
        )
        .select_related("user")
        .first()
    )

    enrollments = (
        StudentEnrollment.objects.filter(
            student__organization=organization,
            student__user=student_user,
            status=StudentEnrollment.STATUS_ACTIVE,
        )
        .select_related("class_section", "class_section__class_group", "academic_year")
        .order_by("-academic_year__is_current", "-joined_at")
    )

    section_ids = [e.class_section_id for e in enrollments]

    # 2. Assignments (Direct + Section)
    direct_assignments = (
        ResourceAssignment.objects.filter(
            organization=organization,
            student=student_user,
        )
        .exclude(
            status__in=[
                ResourceAssignment.STATUS_CANCELLED,
                ResourceAssignment.STATUS_REVOKED,
            ]
        )
        .select_related("course", "track", "exam")
        .order_by("due_at", "-assigned_at")
    )

    section_resources = (
        ClassResourceAssignment.objects.filter(
            class_section_id__in=section_ids,
            is_active=True,
        )
        .select_related("class_section", "course", "track", "exam")
        .order_by("due_at", "-created_at")
    )

    # Segregation by Resource Type
    course_assignments = [
        a for a in direct_assignments
        if a.resource_type == ResourceAssignment.RESOURCE_COURSE and a.course
    ]
    sec_courses = [
        sa for sa in section_resources
        if sa.resource_type == ClassResourceAssignment.RESOURCE_COURSE and sa.course
    ]
    total_courses = len(course_assignments) + len(sec_courses)

    track_assignments = [
        a for a in direct_assignments
        if a.resource_type == ResourceAssignment.RESOURCE_TRACK and a.track
    ]
    sec_tracks = [
        sa for sa in section_resources
        if sa.resource_type == ClassResourceAssignment.RESOURCE_TRACK and sa.track
    ]
    total_tracks = len(track_assignments) + len(sec_tracks)

    exam_assignments = [
        a for a in direct_assignments
        if a.resource_type == ResourceAssignment.RESOURCE_EXAM and a.exam
    ]
    sec_exams = [
        sa for sa in section_resources
        if sa.resource_type == ClassResourceAssignment.RESOURCE_EXAM and sa.exam
    ]
    total_exams = len(exam_assignments) + len(sec_exams)

    # 3. Direct Assignment Lifecycle & Attention
    total_direct = len(direct_assignments)
    completed_direct = len([a for a in direct_assignments if a.status == ResourceAssignment.STATUS_COMPLETED])
    started_direct = len([a for a in direct_assignments if a.status == ResourceAssignment.STATUS_STARTED])
    pending_direct = len([a for a in direct_assignments if a.status == ResourceAssignment.STATUS_ASSIGNED])

    overdue_direct = [
        a for a in direct_assignments
        if a.due_at and a.due_at < now and a.status in [
            ResourceAssignment.STATUS_ASSIGNED,
            ResourceAssignment.STATUS_STARTED,
        ]
    ]

    upcoming_deadlines = [
        a for a in direct_assignments
        if a.due_at and a.due_at >= now and a.status in [
            ResourceAssignment.STATUS_ASSIGNED,
            ResourceAssignment.STATUS_STARTED,
        ]
    ]

    completion_rate = (
        round((completed_direct / total_direct) * 100, 1)
        if total_direct > 0
        else 0.0
    )

    # 4. Exam Attempts & Score History
    attempts_qs = (
        UserExam.objects.filter(
            user=student_user,
            exam__organization=organization,
        )
        .select_related("exam")
        .order_by("-started_at")
    )

    perf_stats = attempts_qs.aggregate(
        total_attempts=Count("id"),
        submitted_attempts=Count("id", filter=Q(status=UserExam.STATUS_SUBMITTED)),
        avg_score=Avg("score", filter=Q(status=UserExam.STATUS_SUBMITTED, score__isnull=False)),
        passed_count=Count("id", filter=Q(status=UserExam.STATUS_SUBMITTED, passed=True)),
    )

    total_attempts = perf_stats["total_attempts"] or 0
    submitted_attempts = perf_stats["submitted_attempts"] or 0
    avg_score = (
        round(perf_stats["avg_score"], 1)
        if perf_stats["avg_score"] is not None
        else None
    )
    passed_count = perf_stats["passed_count"] or 0
    pass_rate = (
        round((passed_count / submitted_attempts) * 100, 1)
        if submitted_attempts > 0
        else 0.0
    )

    # 5. Score Progression Dataset (chronological order)
    submitted_chronological = (
        attempts_qs.filter(status=UserExam.STATUS_SUBMITTED, score__isnull=False)
        .order_by("submitted_at")[:10]
    )

    score_progression_labels = []
    score_progression_scores = []
    for attempt in submitted_chronological:
        dt_label = attempt.submitted_at.strftime("%b %d") if attempt.submitted_at else "Test"
        exam_title = attempt.exam.title if attempt.exam else "Exam"
        label = f"{exam_title[:14]}.. ({dt_label})" if len(exam_title) > 14 else f"{exam_title} ({dt_label})"
        score_progression_labels.append(label)
        score_progression_scores.append(round(attempt.score, 1))

    # 6. Resource Type Breakdown
    resource_type_labels = ["Courses", "Tracks", "Exams"]
    resource_type_data = [total_courses, total_tracks, total_exams]

    return {
        "student_profile": student_profile,
        "primary_enrollment": enrollments.first() if enrollments else None,
        # KPIs
        "total_courses": total_courses,
        "total_tracks": total_tracks,
        "total_exams": total_exams,
        "total_assignments": total_direct,
        "completed_assignments": completed_direct,
        "started_assignments": started_direct,
        "pending_assignments": pending_direct,
        "overdue_count": len(overdue_direct),
        "completion_rate": completion_rate,
        # Performance
        "total_attempts": total_attempts,
        "submitted_attempts": submitted_attempts,
        "avg_score": avg_score,
        "passed_count": passed_count,
        "pass_rate": pass_rate,
        # Charts
        "charts": {
            "score_progression": {
                "labels": score_progression_labels,
                "scores": score_progression_scores,
                "has_data": bool(score_progression_scores),
            },
            "assignment_progress": {
                "labels": ["Completed", "In Progress", "Not Started", "Overdue"],
                "data": [
                    completed_direct,
                    started_direct,
                    pending_direct,
                    len(overdue_direct),
                ],
                "has_data": bool(total_direct > 0),
            },
            "resource_distribution": {
                "labels": resource_type_labels,
                "data": resource_type_data,
                "has_data": bool(any(resource_type_data)),
            },
        },
        # Actionable lists
        "upcoming_deadlines": upcoming_deadlines[:6],
        "overdue_assignments": overdue_direct,
        "recent_attempts": list(attempts_qs[:8]),
    }
