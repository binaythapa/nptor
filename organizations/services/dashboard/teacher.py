from django.db.models import Count
from django.utils import timezone

from courses.models import Course
from organizations.models import (
    ClassSection,
    ClassTeacher,
    ClassResourceAssignment,
    ResourceAssignment,
    StudentEnrollment,
)
from quiz.models import Exam, Question


def get_teacher_overview(organization, user):
    """
    Compute role-restricted dashboard metrics for a teacher/staff member.

    A teacher only sees:
      1. Academic sections where they are assigned as teacher (ClassTeacher).
      2. Student counts and student records enrolled in their assigned sections only.
      3. Class-level resource assignments for their assigned sections.
      4. Assignments and content they created or manage.
      5. Upcoming deadlines for their students.

    Confidential org-level stats (finances, total org users/admins, billing, domain settings)
    are strictly excluded.
    """
    class_teachers = (
        ClassTeacher.objects.filter(
            organization=organization,
            teacher=user,
            is_active=True,
        )
        .select_related("class_section", "class_section__class_group", "academic_year")
        .order_by("academic_year__name", "class_section__class_group__name", "class_section__name")
    )

    section_ids = [ct.class_section_id for ct in class_teachers]

    # Section-level student counts (aggregated in a single query)
    section_student_counts = dict(
        StudentEnrollment.objects.filter(
            class_section_id__in=section_ids,
            status=StudentEnrollment.STATUS_ACTIVE,
        )
        .values("class_section_id")
        .annotate(total=Count("id"))
        .values_list("class_section_id", "total")
    )

    # Attach student count to each assigned section representation
    assigned_sections_data = []
    for ct in class_teachers:
        assigned_sections_data.append({
            "assignment": ct,
            "section": ct.class_section,
            "class_group": ct.class_section.class_group,
            "academic_year": ct.academic_year,
            "subject": ct.subject,
            "is_primary": ct.is_primary,
            "student_count": section_student_counts.get(ct.class_section_id, 0),
        })

    # Total distinct active students across the teacher's sections
    total_section_students = (
        StudentEnrollment.objects.filter(
            class_section_id__in=section_ids,
            status=StudentEnrollment.STATUS_ACTIVE,
        )
        .values("student_id")
        .distinct()
        .count()
    )

    # Class-level resource assignments in teacher's sections
    section_resources = (
        ClassResourceAssignment.objects.filter(
            class_section_id__in=section_ids,
            is_active=True,
        )
        .select_related("class_section", "class_section__class_group", "course", "track", "exam")
        .order_by("-created_at")[:15]
    )

    # Direct individual student assignments created by this teacher
    teacher_assignments = (
        ResourceAssignment.objects.filter(
            organization=organization,
            assigned_by=user,
            is_active=True,
        )
        .select_related("student", "course", "track", "exam")
        .order_by("due_at", "-assigned_at")[:15]
    )

    now = timezone.now()
    # Deadlines for assignments created by this teacher
    upcoming_deadlines = (
        ResourceAssignment.objects.filter(
            organization=organization,
            assigned_by=user,
            is_active=True,
            due_at__isnull=False,
            due_at__gte=now,
        )
        .exclude(status=ResourceAssignment.STATUS_COMPLETED)
        .select_related("student", "course", "track", "exam")
        .order_by("due_at")[:10]
    )

    # Overdue assignments created by this teacher
    overdue_assignments = (
        ResourceAssignment.objects.filter(
            organization=organization,
            assigned_by=user,
            is_active=True,
            due_at__isnull=False,
            due_at__lt=now,
        )
        .exclude(
            status__in=[
                ResourceAssignment.STATUS_COMPLETED,
                ResourceAssignment.STATUS_CANCELLED,
                ResourceAssignment.STATUS_REVOKED,
            ]
        )
        .count()
    )

    # Student roster in teacher's assigned sections
    student_roster = (
        StudentEnrollment.objects.filter(
            class_section_id__in=section_ids,
            status=StudentEnrollment.STATUS_ACTIVE,
        )
        .select_related(
            "student",
            "student__user",
            "student__user__profile",
            "class_section",
            "class_section__class_group",
            "academic_year",
        )
        .order_by("class_section__class_group__name", "class_section__name", "roll_number")[:25]
    )

    # Content created/owned by this teacher
    my_courses_count = Course.objects.filter(organization=organization, created_by=user).count()
    my_exams_count = Exam.objects.filter(organization=organization, created_by=user).count()
    my_questions_count = Question.objects.filter(organization=organization, created_by=user, is_deleted=False).count()

    return {
        "assigned_sections": assigned_sections_data,
        "assigned_sections_count": len(class_teachers),
        "total_section_students": total_section_students,
        "section_resources": section_resources,
        "section_resources_count": ClassResourceAssignment.objects.filter(
            class_section_id__in=section_ids, is_active=True
        ).count(),
        "teacher_assignments": teacher_assignments,
        "teacher_assignments_count": ResourceAssignment.objects.filter(
            organization=organization, assigned_by=user, is_active=True
        ).count(),
        "upcoming_deadlines": upcoming_deadlines,
        "overdue_assignments": overdue_assignments,
        "student_roster": student_roster,
        "my_courses_count": my_courses_count,
        "my_exams_count": my_exams_count,
        "my_questions_count": my_questions_count,
    }
