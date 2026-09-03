from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from courses.models import Course
from organizations.models.access import ResourceAccess
from organizations.models.assignment import ResourceAssignment
from organizations.models.membership import OrganizationMember
from organizations.models.organization import Organization
from organizations.models.role import OrganizationRole
from organizations.services.assignments import assign_resource, StudentNotInOrganizationError
from quiz.models import Exam, ExamTrack
from subscriptions.models import Subscription, SubscriptionEntitlement, SubscriptionPlan
from subscriptions.services import AccessService
from organizations.views.admin.courses import _platform_or_organization_resource

User = get_user_model()


class OrganizationSecurityBoundaryTests(TestCase):
    def setUp(self):
        self.org_a = Organization.objects.create(name="School A", slug="security-a", org_type=Organization.TYPE_SCHOOL)
        self.org_b = Organization.objects.create(name="School B", slug="security-b", org_type=Organization.TYPE_SCHOOL)
        self.admin_a = User.objects.create_user(username="security-admin-a", email="security-a@example.com", password="password")
        self.student_a = User.objects.create_user(username="security-student-a", email="security-student-a@example.com", password="password")
        OrganizationMember.objects.create(user=self.admin_a, organization=self.org_a, role=OrganizationRole.ORG_ADMIN)
        OrganizationMember.objects.create(user=self.student_a, organization=self.org_a, role=OrganizationRole.STUDENT)

    def test_organization_resource_cannot_be_attached_across_org_boundary(self):
        course = Course.objects.create(title="Private B", organization=self.org_b, owner_type=Course.OWNER_ORGANIZATION)
        track = ExamTrack.objects.create(title="Private Track B", slug="private-track-b", organization=self.org_b)
        exam = Exam.objects.create(title="Private Exam B", organization=self.org_b, duration_seconds=60)
        self.assertFalse(_platform_or_organization_resource(course, self.org_a))
        self.assertFalse(_platform_or_organization_resource(track, self.org_a))
        self.assertFalse(_platform_or_organization_resource(exam, self.org_a))

    def test_platform_resources_remain_attachable(self):
        course = Course.objects.create(title="Platform Course", owner_type=Course.OWNER_PLATFORM)
        track = ExamTrack.objects.create(title="Platform Track", slug="platform-track")
        exam = Exam.objects.create(title="Platform Exam", duration_seconds=60)
        self.assertTrue(_platform_or_organization_resource(course, self.org_a))
        self.assertTrue(_platform_or_organization_resource(track, self.org_a))
        self.assertTrue(_platform_or_organization_resource(exam, self.org_a))

    def test_assignment_service_rejects_student_from_other_org(self):
        other_student = User.objects.create_user(username="security-student-b", email="security-student-b@example.com", password="password")
        OrganizationMember.objects.create(user=other_student, organization=self.org_b, role=OrganizationRole.STUDENT)
        course = Course.objects.create(title="Assigned Course")
        with self.assertRaises(StudentNotInOrganizationError):
            assign_resource(
                actor=self.admin_a,
                organization=self.org_a,
                student=other_student,
                resource_type=ResourceAssignment.RESOURCE_COURSE,
                resource_id=course.id,
            )

    def test_expired_organization_subscription_does_not_grant_access(self):
        course = Course.objects.create(title="Expired Course")
        plan = SubscriptionPlan.objects.create(name="Security Plan", code="security-plan")
        subscription = Subscription.objects.create(
            organization=self.org_a,
            plan=plan,
            status=Subscription.STATUS_ACTIVE,
            starts_at=timezone.now() - timedelta(days=10),
            expires_at=timezone.now() - timedelta(days=1),
        )
        SubscriptionEntitlement.objects.create(
            subscription=subscription,
            resource_type=SubscriptionEntitlement.RESOURCE_COURSE,
            course=course,
            is_active=True,
        )
        self.assertFalse(AccessService.organization_has_resource(self.org_a, AccessService.RESOURCE_COURSE, course))

    def test_organization_access_requires_matching_assignment(self):
        course = Course.objects.create(title="Assigned Course")
        access = ResourceAccess.objects.create(
            user=self.student_a,
            resource_type=ResourceAccess.RESOURCE_COURSE,
            source=ResourceAccess.SOURCE_ORGANIZATION,
            organization=self.org_a,
            course=course,
            is_active=True,
        )
        self.assertFalse(AccessService.has_access(
            student=self.student_a,
            resource_type=AccessService.RESOURCE_COURSE,
            resource=course,
        ))
        self.assertIsNotNone(access)
