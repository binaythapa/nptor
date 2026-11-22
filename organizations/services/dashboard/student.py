from django.db.models import Avg, Count, Q
from django.utils import timezone

from organizations.models import (
    ClassResourceAssignment,
    OrganizationStudent,
    ResourceAssignment,
    StudentEnrollment,
)
from quiz.models import UserExam


def get_student_overview(organization, user):
    """
    Compute role-restricted dashboard metrics for a student.

    A student only sees:
      1. Their own student profile and enrollment info (OrganizationStudent, StudentEnrollment).
      2. Learning resources assigned directly to them (ResourceAssignment) or
         to their active class section (ClassResourceAssignment).
      3. Their own exam attempts, scores, and history (UserExam).
      4. Their own upcoming deadlines and completion status.

    Other students' data and teacher/admin management features are strictly excluded.
    """
    student_profile = (
        OrganizationStudent.objects.filter(
            organization=organization,
            user=user,
        )
        .select_related("user")
        .first()
    )

    # Academic enrollments
    enrollments = (
        StudentEnrollment.objects.filter(
            student__organization=organization,
            student__user=user,
            status=StudentEnrollment.STATUS_ACTIVE,
        )
        .select_related("class_section", "class_section__class_group", "academic_year")
        .order_by("-academic_year__is_current", "-joined_at")
    )

    section_ids = [e.class_section_id for e in enrollments]

    # Direct individual assignments
    direct_assignments = (
        ResourceAssignment.objects.filter(
            organization=organization,
            student=user,
            is_active=True,
        )
        .select_related("course", "track", "exam")
        .order_by("due_at", "-assigned_at")
    )

    # Section-level assignments
    section_assignments = (
        ClassResourceAssignment.objects.filter(
            class_section_id__in=section_ids,
            is_active=True,
        )
        .select_related("class_section", "course", "track", "exam")
        .order_by("due_at", "-created_at")
    )

    # Segregate courses
    course_assignments = [
        a for a in direct_assignments
        if a.resource_type == ResourceAssignment.RESOURCE_COURSE and a.course
    ]
    section_courses = [
        sa for sa in section_assignments
        if sa.resource_type == ClassResourceAssignment.RESOURCE_COURSE and sa.course
    ]

    # Segregate tracks
    track_assignments = [
        a for a in direct_assignments
        if a.resource_type == ResourceAssignment.RESOURCE_TRACK and a.track
    ]
    section_tracks = [
        sa for sa in section_assignments
        if sa.resource_type == ClassResourceAssignment.RESOURCE_TRACK and sa.track
    ]

    # Segregate exams
    exam_assignments = [
        a for a in direct_assignments
        if a.resource_type == ResourceAssignment.RESOURCE_EXAM and a.exam
    ]
    section_exams = [
        sa for sa in section_assignments
        if sa.resource_type == ClassResourceAssignment.RESOURCE_EXAM and sa.exam
    ]

    # Exam attempts & score metrics for this student
    attempts = (
        UserExam.objects.filter(user=user)
        .select_related("exam")
        .order_by("-started_at")[:10]
    )

    perf_stats = (
        UserExam.objects.filter(user=user)
        .aggregate(
            total_attempts=Count("id"),
            completed_attempts=Count("id", filter=Q(status=UserExam.STATUS_SUBMITTED)),
            avg_score=Avg("score", filter=Q(score__isnull=False)),
            passed_count=Count("id", filter=Q(passed=True)),
        )
    )

    now = timezone.now()
    # Deadlines & attention
    upcoming_deadlines = [
        a for a in direct_assignments
        if a.due_at and a.due_at >= now and a.status in [
            ResourceAssignment.STATUS_ASSIGNED,
            ResourceAssignment.STATUS_STARTED,
        ]
    ]

    overdue_assignments = [
        a for a in direct_assignments
        if a.due_at and a.due_at < now and a.status in [
            ResourceAssignment.STATUS_ASSIGNED,
            ResourceAssignment.STATUS_STARTED,
        ]
    ]

    # Completed work
    completed_assignments = [
        a for a in direct_assignments
        if a.status == ResourceAssignment.STATUS_COMPLETED
    ]

    return {
        "student_profile": student_profile,
        "enrollments": enrollments,
        "primary_enrollment": enrollments.first() if enrollments else None,
        "course_assignments": course_assignments,
        "section_courses": section_courses,
        "total_courses": len(course_assignments) + len(section_courses),
        "track_assignments": track_assignments,
        "section_tracks": section_tracks,
        "total_tracks": len(track_assignments) + len(section_tracks),
        "exam_assignments": exam_assignments,
        "section_exams": section_exams,
        "total_exams": len(exam_assignments) + len(section_exams),
        "attempts": attempts,
        "total_attempts": perf_stats["total_attempts"] or 0,
        "completed_attempts": perf_stats["completed_attempts"] or 0,
        "avg_score": round(perf_stats["avg_score"], 1) if perf_stats["avg_score"] is not None else None,
        "passed_count": perf_stats["passed_count"] or 0,
        "upcoming_deadlines": upcoming_deadlines,
        "overdue_assignments": overdue_assignments,
        "completed_assignments": completed_assignments,
    }
