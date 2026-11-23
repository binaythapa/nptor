# organizations/services/analytics/teacher.py

from django.db.models import Avg, Count, Q
from django.utils import timezone

from courses.models import Course
from organizations.models import (
    ClassSection,
    ClassTeacher,
    ClassResourceAssignment,
    ResourceAssignment,
    StudentEnrollment,
)
from quiz.models import Exam, Question, UserExam
from .filters import parse_date_range


def get_teacher_analytics(organization, teacher_user, date_range="30d"):
    """
    Calculate role-restricted teaching and section analytics for organization
    teaching staff.

    Enforces strict scoping:
      - Only academic sections assigned to teacher_user (ClassTeacher).
      - Only students actively enrolled in those sections.
      - Confidential org-level stats (billing, total org users/admins) are strictly excluded.
    """
    start_dt, end_dt, active_range, range_label = parse_date_range(date_range)
    now = timezone.now()

    # 1. Assigned Sections
    class_teachers = (
        ClassTeacher.objects.filter(
            organization=organization,
            teacher=teacher_user,
            is_active=True,
        )
        .select_related("class_section", "class_section__class_group", "academic_year")
        .order_by("academic_year__name", "class_section__class_group__name", "class_section__name")
    )

    section_ids = [ct.class_section_id for ct in class_teachers]

    # 2. Section Student Enrollments
    enrollments = StudentEnrollment.objects.filter(
        class_section_id__in=section_ids,
        status=StudentEnrollment.STATUS_ACTIVE,
    )
    student_user_ids = list(
        enrollments.values_list("student__user_id", flat=True).distinct()
    )
    total_section_students = len(student_user_ids)

    # Breakdown by section
    section_student_counts = dict(
        enrollments.values("class_section_id")
        .annotate(total=Count("id"))
        .values_list("class_section_id", "total")
    )

    assigned_sections_data = []
    section_chart_labels = []
    section_chart_data = []
    for ct in class_teachers:
        count = section_student_counts.get(ct.class_section_id, 0)
        label = f"{ct.class_section.class_group.name} - {ct.class_section.name}"
        section_chart_labels.append(label)
        section_chart_data.append(count)
        assigned_sections_data.append({
            "assignment": ct,
            "section": ct.class_section,
            "class_group": ct.class_section.class_group,
            "academic_year": ct.academic_year,
            "subject": ct.subject,
            "is_primary": ct.is_primary,
            "student_count": count,
        })

    # 3. Section Resources
    section_resources_qs = ClassResourceAssignment.objects.filter(
        class_section_id__in=section_ids,
        is_active=True,
    )
    if start_dt is not None:
        section_resources_filtered = section_resources_qs.filter(created_at__gte=start_dt)
    else:
        section_resources_filtered = section_resources_qs

    section_resources_count = section_resources_filtered.count()

    # 4. Teacher's Created Assignments
    teacher_assignments_qs = ResourceAssignment.objects.filter(
        organization=organization,
        assigned_by=teacher_user,
    ).exclude(
        status__in=[
            ResourceAssignment.STATUS_CANCELLED,
            ResourceAssignment.STATUS_REVOKED,
        ]
    )
    if start_dt is not None:
        teacher_assignments_filtered = teacher_assignments_qs.filter(assigned_at__gte=start_dt)
    else:
        teacher_assignments_filtered = teacher_assignments_qs

    total_teacher_assignments = teacher_assignments_filtered.count()
    completed_assignments = teacher_assignments_filtered.filter(
        status=ResourceAssignment.STATUS_COMPLETED
    ).count()
    started_assignments = teacher_assignments_filtered.filter(
        status=ResourceAssignment.STATUS_STARTED
    ).count()
    assigned_assignments = teacher_assignments_filtered.filter(
        status=ResourceAssignment.STATUS_ASSIGNED
    ).count()

    overdue_assignments = (
        teacher_assignments_filtered.filter(due_at__isnull=False, due_at__lt=now, is_active=True)
        .count()
    )

    completion_rate = (
        round((completed_assignments / total_teacher_assignments) * 100, 1)
        if total_teacher_assignments > 0
        else 0.0
    )

    # 5. Student Exam Performance in Assigned Sections
    student_exams_qs = UserExam.objects.filter(
        user_id__in=student_user_ids,
        exam__organization=organization,
    )
    if start_dt is not None:
        student_exams_filtered = student_exams_qs.filter(started_at__gte=start_dt)
    else:
        student_exams_filtered = student_exams_qs

    exam_aggregates = student_exams_filtered.aggregate(
        total_attempts=Count("id"),
        submitted_attempts=Count("id", filter=Q(status=UserExam.STATUS_SUBMITTED)),
        avg_score=Avg("score", filter=Q(status=UserExam.STATUS_SUBMITTED, score__isnull=False)),
        passed_attempts=Count("id", filter=Q(status=UserExam.STATUS_SUBMITTED, passed=True)),
    )

    submitted_count = exam_aggregates["submitted_attempts"] or 0
    avg_score = (
        round(exam_aggregates["avg_score"], 1)
        if exam_aggregates["avg_score"] is not None
        else None
    )
    passed_count = exam_aggregates["passed_attempts"] or 0
    pass_rate = (
        round((passed_count / submitted_count) * 100, 1)
        if submitted_count > 0
        else 0.0
    )

    # 6. Score Distribution Histogram (Teacher's Students)
    submitted_exams = student_exams_filtered.filter(
        status=UserExam.STATUS_SUBMITTED,
        score__isnull=False,
    )

    count_90_100 = submitted_exams.filter(score__gte=90.0).count()
    count_75_89 = submitted_exams.filter(score__gte=75.0, score__lt=90.0).count()
    count_60_74 = submitted_exams.filter(score__gte=60.0, score__lt=75.0).count()
    count_40_59 = submitted_exams.filter(score__gte=40.0, score__lt=60.0).count()
    count_under_40 = submitted_exams.filter(score__lt=40.0).count()

    score_dist_labels = [
        "90-100% (Excellent)",
        "75-89% (Good)",
        "60-74% (Average)",
        "40-59% (Needs Help)",
        "<40% (At Risk)",
    ]
    score_dist_data = [
        count_90_100,
        count_75_89,
        count_60_74,
        count_40_59,
        count_under_40,
    ]

    # 7. Content Owned by Teacher
    my_courses_count = Course.objects.filter(organization=organization, created_by=teacher_user).count()
    my_exams_count = Exam.objects.filter(organization=organization, created_by=teacher_user).count()
    my_questions_count = Question.objects.filter(
        organization=organization, created_by=teacher_user, is_deleted=False
    ).count()

    # 8. Lists for Display
    upcoming_deadlines = (
        teacher_assignments_qs.filter(
            due_at__isnull=False,
            due_at__gte=now,
        )
        .exclude(status=ResourceAssignment.STATUS_COMPLETED)
        .select_related("student", "course", "track", "exam")
        .order_by("due_at")[:10]
    )

    recent_teacher_assignments = (
        teacher_assignments_qs.select_related("student", "course", "track", "exam")
        .order_by("-assigned_at")[:10]
    )

    student_roster = (
        enrollments.select_related(
            "student",
            "student__user",
            "class_section",
            "class_section__class_group",
            "academic_year",
        )
        .order_by("class_section__class_group__name", "class_section__name", "roll_number")[:25]
    )

    return {
        "active_range": active_range,
        "range_label": range_label,
        # Section & Student Scope
        "assigned_sections": assigned_sections_data,
        "assigned_sections_count": len(class_teachers),
        "total_section_students": total_section_students,
        "section_resources_count": section_resources_count,
        # Assignments
        "total_teacher_assignments": total_teacher_assignments,
        "completed_assignments": completed_assignments,
        "started_assignments": started_assignments,
        "assigned_assignments": assigned_assignments,
        "overdue_assignments": overdue_assignments,
        "completion_rate": completion_rate,
        # Exams & Performance
        "student_exams_attempted": submitted_count,
        "avg_student_exam_score": avg_score,
        "student_passed_count": passed_count,
        "student_pass_rate": pass_rate,
        # Content creation
        "my_courses_count": my_courses_count,
        "my_exams_count": my_exams_count,
        "my_questions_count": my_questions_count,
        # Visual Chart Payloads
        "charts": {
            "section_students": {
                "labels": section_chart_labels,
                "data": section_chart_data,
                "has_data": bool(section_chart_data and any(section_chart_data)),
            },
            "assignment_status": {
                "labels": ["Completed", "In Progress", "Pending", "Overdue"],
                "data": [
                    completed_assignments,
                    started_assignments,
                    assigned_assignments,
                    overdue_assignments,
                ],
                "has_data": bool(total_teacher_assignments > 0),
            },
            "score_distribution": {
                "labels": score_dist_labels,
                "data": score_dist_data,
                "has_data": bool(sum(score_dist_data) > 0),
            },
        },
        # Display Records
        "upcoming_deadlines": upcoming_deadlines,
        "recent_teacher_assignments": recent_teacher_assignments,
        "student_roster": student_roster,
    }
