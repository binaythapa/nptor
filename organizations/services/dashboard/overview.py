from django.utils import timezone

from courses.models import Course
from organizations.models import OrganizationMember, ResourceAssignment


def get_overview(organization):
    members = OrganizationMember.objects.filter(organization=organization, is_active=True)
    assignments = ResourceAssignment.objects.filter(organization=organization, is_active=True)
    now = timezone.now()
    students = members.filter(role="student")
    overdue = assignments.filter(due_at__lt=now).exclude(status__in=[ResourceAssignment.STATUS_COMPLETED, ResourceAssignment.STATUS_CANCELLED, ResourceAssignment.STATUS_REVOKED])
    return {
        "students": students.count(),
        "courses": Course.objects.filter(organization=organization, is_published=True).count(),
        "assignments": assignments.count(),
        "active_exams": assignments.filter(resource_type=ResourceAssignment.RESOURCE_EXAM).count(),
        "overdue_assignments": overdue.count(),
        "not_started": assignments.filter(status=ResourceAssignment.STATUS_ASSIGNED).count(),
        "recent_assignments": assignments.select_related("student", "course", "track", "exam").order_by("-assigned_at")[:10],
    }
