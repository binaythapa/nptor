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
)
from quiz.models import Category, Domain, Exam, ExamTrack, Question


def get_overview(organization):
    members = OrganizationMember.objects.filter(organization=organization, is_active=True)
    assignments = ResourceAssignment.objects.filter(organization=organization, is_active=True)
    now = timezone.now()
    overdue = assignments.filter(due_at__lt=now).exclude(
        status__in=[
            ResourceAssignment.STATUS_COMPLETED,
            ResourceAssignment.STATUS_CANCELLED,
            ResourceAssignment.STATUS_REVOKED,
        ]
    )

    return {
        # People
        "students": members.filter(role=OrganizationRole.STUDENT).count(),
        "teachers": members.filter(role=OrganizationRole.STAFF).count(),
        "admins": members.filter(role__in=OrganizationRole.administrative_roles()).count(),
        # Academic structure
        "academic_years": AcademicYear.objects.filter(organization=organization).count(),
        "classes": OrganizationClass.objects.filter(organization=organization, is_active=True).count(),
        "sections": ClassSection.objects.filter(organization=organization, is_active=True).count(),
        # Taxonomy & Question bank
        "domains": Domain.objects.filter(organization=organization, is_active=True).count(),
        "categories": Category.objects.filter(organization=organization, is_active=True).count(),
        "questions": Question.objects.filter(organization=organization, is_active=True, is_deleted=False).count(),
        # Content & Products
        "courses": Course.objects.filter(organization=organization).count(),
        "published_courses": Course.objects.filter(organization=organization, is_published=True).count(),
        "tracks": ExamTrack.objects.filter(organization=organization).count(),
        "exams": Exam.objects.filter(organization=organization).count(),
        # Assignments
        "assignments": assignments.count(),
        "assigned_exams": assignments.filter(resource_type=ResourceAssignment.RESOURCE_EXAM).count(),
        "not_started": assignments.filter(status=ResourceAssignment.STATUS_ASSIGNED).count(),
        "started": assignments.filter(status=ResourceAssignment.STATUS_STARTED).count(),
        "completed": assignments.filter(status=ResourceAssignment.STATUS_COMPLETED).count(),
        "overdue_assignments": overdue.count(),
        "recent_assignments": assignments.select_related(
            "student", "course", "track", "exam"
        ).order_by("-assigned_at")[:8],
        # Audit activity
        "recent_audit_logs": OrganizationAuditLog.objects.filter(
            organization=organization
        ).select_related("actor").order_by("-created_at")[:8],
    }
