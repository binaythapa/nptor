from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from courses.models import Course
from payments.models import PaymentOrder
from subscriptions.models import SubscriptionPlan


User = get_user_model()


class CourseCheckoutAuthorizationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="checkout-security-user",
            password="test-password",
        )
        self.plan = SubscriptionPlan.objects.create(
            name="Checkout Security Plan",
            code="CHECKOUT_SECURITY_PLAN",
            price=Decimal("100.00"),
            currency="INR",
            is_active=True,
        )

    def _course(self, *, public, published, approval_status, organization=None):
        course = Course.objects.create(
            title="Checkout Security Course",
            description="Security test course",
            level="beginner",
            is_public=public,
            is_published=published,
            approval_status=approval_status,
            organization=organization,
        )
        course.subscription_plans.add(self.plan)
        return course

    def _checkout_url(self, course):
        return reverse(
            "payments:course_checkout",
            kwargs={"course_id": course.id},
        )

    def test_private_course_cannot_start_checkout(self):
        course = self._course(
            public=False,
            published=True,
            approval_status=Course.APPROVAL_APPROVED,
        )
        self.client.force_login(self.user)

        with patch("payments.views.checkout._start_payment") as start_payment:
            response = self.client.get(self._checkout_url(course))

        self.assertEqual(response.status_code, 302)
        start_payment.assert_not_called()

    def test_unpublished_course_cannot_start_checkout(self):
        course = self._course(
            public=True,
            published=False,
            approval_status=Course.APPROVAL_APPROVED,
        )
        self.client.force_login(self.user)

        with patch("payments.views.checkout._start_payment") as start_payment:
            response = self.client.get(self._checkout_url(course))

        self.assertEqual(response.status_code, 302)
        start_payment.assert_not_called()

    def test_unapproved_course_cannot_start_checkout(self):
        course = self._course(
            public=True,
            published=True,
            approval_status=Course.APPROVAL_PENDING,
        )
        self.client.force_login(self.user)

        with patch("payments.views.checkout._start_payment") as start_payment:
            response = self.client.get(self._checkout_url(course))

        self.assertEqual(response.status_code, 302)
        start_payment.assert_not_called()

    def test_public_approved_published_paid_course_can_start_checkout(self):
        course = self._course(
            public=True,
            published=True,
            approval_status=Course.APPROVAL_APPROVED,
        )
        self.client.force_login(self.user)

        with patch("payments.views.checkout._start_payment") as start_payment:
            start_payment.return_value = object()
            response = self.client.get(self._checkout_url(course))

        self.assertIs(response, start_payment.return_value)
        start_payment.assert_called_once()
        kwargs = start_payment.call_args.kwargs
        self.assertEqual(kwargs["resource_type"], PaymentOrder.RESOURCE_COURSE)
        self.assertEqual(kwargs["resource"], course)
        self.assertEqual(kwargs["amount"], self.plan.price)
        self.assertEqual(kwargs["currency"], self.plan.currency)
