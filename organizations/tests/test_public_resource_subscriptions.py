from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from courses.models import Course
from organizations.models import Organization, OrganizationMember
from organizations.services.assignments import assign_resource, ResourceNotAvailableError
from organizations.services.public_resource_subscriptions import (
    subscribe_organization_to_public_resource,
)
from quiz.models import ExamTrack
from subscriptions.models import Subscription, SubscriptionEntitlement, SubscriptionPlan


class OrganizationPublicResourceSubscriptionTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(username="org-admin", password="test")
        self.student = User.objects.create_user(username="student", password="test")
        self.other_student = User.objects.create_user(username="other-student", password="test")

        self.organization = Organization.objects.create(
            name="Test School",
            slug="test-school",
            org_type=Organization.TYPE_SCHOOL,
        )
        OrganizationMember.objects.create(
            user=self.admin,
            organization=self.organization,
            role=OrganizationMember.ROLE_ORG_ADMIN,
        )
        OrganizationMember.objects.create(
            user=self.student,
            organization=self.organization,
            role=OrganizationMember.ROLE_STUDENT,
        )

        self.course_plan = SubscriptionPlan.objects.create(
            name="Course Plan",
            code="test-course-plan",
            product_type=SubscriptionPlan.PRODUCT_COURSE,
            access_mode=SubscriptionPlan.ACCESS_SINGLE_RESOURCE,
            interval_unit=SubscriptionPlan.INTERVAL_MONTH,
            interval_count=1,
            price=100,
            currency="INR",
        )
        self.course = Course.objects.create(
            title="Public Course",
            description="Public course",
            level="beginner",
            owner_type=Course.OWNER_PLATFORM,
            is_public=True,
            is_published=True,
            approval_status=Course.APPROVAL_APPROVED,
        )
        self.course.subscription_plans.add(self.course_plan)

        self.track_plan = SubscriptionPlan.objects.create(
            name="Track Plan",
            code="test-track-plan",
            product_type=SubscriptionPlan.PRODUCT_TRACK,
            access_mode=SubscriptionPlan.ACCESS_SINGLE_RESOURCE,
            interval_unit=SubscriptionPlan.INTERVAL_MONTH,
            interval_count=1,
            price=200,
            currency="INR",
        )
        self.track = ExamTrack.objects.create(
            title="Public Track",
            slug="public-track",
            organization=None,
            is_active=True,
        )
        self.track.subscription_plans.add(self.track_plan)

    def test_public_course_subscription_creates_org_entitlement(self):
        subscription, entitlement, created = subscribe_organization_to_public_resource(
            organization=self.organization,
            actor=self.admin,
            resource_type=SubscriptionEntitlement.RESOURCE_COURSE,
            resource_id=self.course.id,
            plan_id=self.course_plan.id,
        )

        self.assertTrue(created)
        self.assertEqual(subscription.organization_id, self.organization.id)
        self.assertIsNone(subscription.user_id)
        self.assertTrue(subscription.is_valid())
        self.assertEqual(entitlement.course_id, self.course.id)
        self.assertEqual(entitlement.subscription_id, subscription.id)

    def test_public_course_cannot_be_assigned_without_subscription(self):
        with self.assertRaises(ResourceNotAvailableError):
            assign_resource(
                actor=self.admin,
                organization=self.organization,
                student=self.student,
                resource_type="course",
                resource_id=self.course.id,
            )

    def test_subscribed_public_course_can_be_assigned_to_org_student(self):
        subscribe_organization_to_public_resource(
            organization=self.organization,
            actor=self.admin,
            resource_type=SubscriptionEntitlement.RESOURCE_COURSE,
            resource_id=self.course.id,
            plan_id=self.course_plan.id,
        )

        result = assign_resource(
            actor=self.admin,
            organization=self.organization,
            student=self.student,
            resource_type=SubscriptionEntitlement.RESOURCE_COURSE,
            resource_id=self.course.id,
        )

        self.assertTrue(result.access.is_valid())
        self.assertEqual(result.access.subscription.organization_id, self.organization.id)
        self.assertEqual(result.assignment.organization_id, self.organization.id)

    def test_subscription_does_not_grant_unassigned_student_access(self):
        subscribe_organization_to_public_resource(
            organization=self.organization,
            actor=self.admin,
            resource_type=SubscriptionEntitlement.RESOURCE_COURSE,
            resource_id=self.course.id,
            plan_id=self.course_plan.id,
        )

        from subscriptions.services import AccessService

        self.assertFalse(AccessService.has_course_access(self.student, self.course))
        self.assertFalse(AccessService.has_course_access(self.other_student, self.course))

    def test_public_track_subscription_can_be_assigned(self):
        subscribe_organization_to_public_resource(
            organization=self.organization,
            actor=self.admin,
            resource_type=SubscriptionEntitlement.RESOURCE_TRACK,
            resource_id=self.track.id,
            plan_id=self.track_plan.id,
        )

        result = assign_resource(
            actor=self.admin,
            organization=self.organization,
            student=self.student,
            resource_type=SubscriptionEntitlement.RESOURCE_TRACK,
            resource_id=self.track.id,
        )

        self.assertTrue(result.access.is_valid())
        self.assertEqual(result.access.subscription.organization_id, self.organization.id)
