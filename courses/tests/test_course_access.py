from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from courses.models import Course
from subscriptions.models import SubscriptionPlan


User = get_user_model()


class CourseAccessTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="course-owner",
            password="test-password",
        )
        self.student = User.objects.create_user(
            username="course-student",
            password="test-password",
        )

        self.plan = SubscriptionPlan.objects.create(
            name="Paid Course Plan",
            code="paid-course-plan-test",
            duration_days=30,
            price=Decimal("499.00"),
            currency="INR",
            is_active=True,
        )

        self.course = Course.objects.create(
            title="Paid Public Course",
            description="A paid course used for access-control testing.",
            level="beginner",
            owner_type=Course.OWNER_PLATFORM,
            is_public=True,
            is_published=True,
            approval_status=Course.APPROVAL_APPROVED,
            created_by=self.owner,
        )
        self.course.subscription_plans.add(self.plan)

    def test_unsubscribed_student_cannot_open_paid_public_course(self):
        self.client.force_login(self.student)

        response = self.client.get(
            f"/courses/{self.course.slug}/learn/"
        )

        self.assertEqual(response.status_code, 404)
