from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from courses.models import Course, CourseEnrollment
from organizations.models import ResourceAccess
from subscriptions.models import SubscriptionPlan


User = get_user_model()


class FreeCourseEnrollmentTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="free-course-student",
            password="test-password",
        )
        self.owner = User.objects.create_user(
            username="free-course-owner",
            password="test-password",
        )
        self.free_course = Course.objects.create(
            title="Free Python Course",
            description="Learn Python for free.",
            level="beginner",
            owner_type=Course.OWNER_PLATFORM,
            is_public=True,
            is_published=True,
            approval_status=Course.APPROVAL_APPROVED,
            created_by=self.owner,
        )
        self.paid_course = Course.objects.create(
            title="Paid Python Course",
            description="Advanced Python course.",
            level="advanced",
            owner_type=Course.OWNER_PLATFORM,
            is_public=True,
            is_published=True,
            approval_status=Course.APPROVAL_APPROVED,
            created_by=self.owner,
        )
        plan = SubscriptionPlan.objects.create(
            name="Paid Course Plan",
            code="paid-course-enrollment-test",
            duration_days=30,
            price=Decimal("499.00"),
            currency="INR",
            is_active=True,
        )
        self.paid_course.subscription_plans.add(plan)
        self.client.force_login(self.student)

    def test_free_course_detail_offers_free_enrollment(self):
        response = self.client.get(
            reverse("courses:course_detail", args=[self.free_course.slug])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enroll Free")
        self.assertNotContains(response, "Get Full Access")

    def test_free_course_enrollment_creates_active_enrollment(self):
        response = self.client.post(
            reverse("courses:enroll_free_course", args=[self.free_course.slug])
        )

        self.assertRedirects(
            response,
            reverse("courses:course_learn", args=[self.free_course.slug]),
        )
        enrollment = CourseEnrollment.objects.get(
            user=self.student,
            course=self.free_course,
        )
        self.assertTrue(enrollment.is_active)

        access = ResourceAccess.objects.get(
            user=self.student,
            resource_type=ResourceAccess.RESOURCE_COURSE,
            course=self.free_course,
            source=ResourceAccess.SOURCE_PUBLIC,
        )
        self.assertTrue(access.is_active)
        self.assertTrue(access.is_valid())

    def test_reenrolling_free_course_does_not_create_duplicate(self):
        url = reverse("courses:enroll_free_course", args=[self.free_course.slug])

        self.client.post(url)
        self.client.post(url)

        self.assertEqual(
            CourseEnrollment.objects.filter(
                user=self.student,
                course=self.free_course,
            ).count(),
            1,
        )
        self.assertEqual(
            ResourceAccess.objects.filter(
                user=self.student,
                resource_type=ResourceAccess.RESOURCE_COURSE,
                course=self.free_course,
                source=ResourceAccess.SOURCE_PUBLIC,
            ).count(),
            1,
        )

    def test_paid_course_cannot_use_free_enrollment_endpoint(self):
        response = self.client.post(
            reverse("courses:enroll_free_course", args=[self.paid_course.slug])
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(
            CourseEnrollment.objects.filter(
                user=self.student,
                course=self.paid_course,
            ).exists()
        )

    def test_paid_course_detail_does_not_offer_free_enrollment(self):
        response = self.client.get(
            reverse("courses:course_detail", args=[self.paid_course.slug])
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Enroll Free")
        self.assertContains(response, "Get Full Access")
