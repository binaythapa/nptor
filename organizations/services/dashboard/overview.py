from django.db.models import Q
from django.utils import timezone

from courses.models import Course
from organizations.models import OrganizationMember, ResourceAssignment
from quiz.models import Exam, ExamTrack


def get_overview(organization):
    members = OrganizationMember.objects.filter(organization=organization, is_active=True)
    assignments = ResourceAssignment.objects.filter(organization=organization, is_active=True)
    now = timezone.now()
    students = members.filter(role="student")
    overdue = assignments.filter(due_at__lt=now).exclude(
        status__in=[
            ResourceAssignment.STATUS_COMPLETED,
            ResourceAssignment.STATUS_CANCELLED,
            ResourceAssignment.STATUS_REVOKED,
        ]
    )
    visible_courses = Course.objects.filter(
        Q(organization=organization) | Q(organization__isnull=True, is_published=True)
    )
    visible_tracks = ExamTrack.objects.filter(
        Q(organization=organization) | Q(organization__isnull=True)
    )
    visible_exams = Exam.objects.filter(
        Q(organization=organization) | Q(organization__isnull=True)
    )
    return {
        "students": students.count(),
        "courses": visible_courses.count(),
        "learning_tracks": visible_tracks.count(),
        "exams": visible_exams.count(),
        "assignments": assignments.count(),
        "assigned_exams": assignments.filter(resource_type=ResourceAssignment.RESOURCE_EXAM).count(),
        "overdue_assignments": overdue.count(),
        "not_started": assignments.filter(status=ResourceAssignment.STATUS_ASSIGNED).count(),
        "recent_assignments": assignments.select_related("student", "course", "track", "exam").order_by("-assigned_at")[:10],
    }
