from django.contrib.auth import get_user_model
from django.test import TestCase

from courses.models import Course
from subscriptions.models import SubscriptionEntitlement, SubscriptionPlan
from subscriptions.services.course_access_service import CourseAccessService


User = get_user_model()


class CourseAccessServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="course-access-user", password="test-pass")
        self.course = Course.objects.create(
            title="Course Access Test",
            description="Test course",
            level="beginner",
            is_published=True,
        )
        self.plan = SubscriptionPlan.objects.create(
            name="Course Annual",
            code="course-annual-test",
            duration_days=365,
            price=100,
            currency="INR",
            is_active=True,
            scope=SubscriptionPlan.SCOPE_RESOURCE,
        )
        self.course.subscription_plans.add(self.plan)

    def test_grant_course_access_creates_course_entitlement_and_access(self):
        subscription, entitlement = CourseAccessService.grant_admin_access(
            user=self.user,
            course=self.course,
            plan=self.plan,
            granted_by=self.user,
        )

        self.assertEqual(entitlement.resource_type, SubscriptionEntitlement.RESOURCE_COURSE)
        self.assertEqual(entitlement.course_id, self.course.id)
        self.assertTrue(entitlement.is_active)
        self.assertEqual(subscription.user_id, self.user.id)
        self.assertTrue(
            self.user.resource_access.filter(
                resource_type="course",
                course=self.course,
                is_active=True,
            ).exists()
        )
