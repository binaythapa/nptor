from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from courses.models import Course
from payments.models import PaymentOrder
from quiz.models import Exam, ExamTrack
from subscriptions.models import SubscriptionPlan


User = get_user_model()


class PaidCheckoutFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="paid-checkout-user",
            password="test-password",
        )
        self.plan = SubscriptionPlan.objects.create(
            name="Paid Checkout Plan",
            code="PAID_CHECKOUT_PLAN",
            duration_days=30,
            price=Decimal("799.00"),
            currency="INR",
            is_active=True,
        )
        self.course = Course.objects.create(
            title="Paid Checkout Course",
            description="Paid checkout regression course",
            level="beginner",
            owner_type=Course.OWNER_PLATFORM,
            is_public=True,
            is_published=True,
            approval_status=Course.APPROVAL_APPROVED,
            created_by=self.user,
        )
        self.course.subscription_plans.add(self.plan)
        self.track = ExamTrack.objects.create(
            title="Paid Checkout Track",
            slug="paid-checkout-track",
            pricing_type=ExamTrack.PRICING_FREE,
            currency="INR",
            is_active=True,
        )
        self.track.subscription_plans.add(self.plan)
        self.exam = Exam.objects.create(
            title="Paid Checkout Exam",
            duration_seconds=3600,
            question_count=20,
            passing_score=70,
            is_free=False,
            price=Decimal("299.00"),
            currency="INR",
            is_published=True,
        )
        self.client.force_login(self.user)

    def test_paid_course_checkout_passes_plan_price_to_payment(self):
        with patch("payments.views.checkout._start_payment") as start_payment:
            start_payment.return_value = object()
            response = self.client.get(
                reverse("payments:course_checkout", kwargs={"course_id": self.course.id})
            )

        self.assertIs(response, start_payment.return_value)
        kwargs = start_payment.call_args.kwargs
        self.assertEqual(kwargs["resource_type"], PaymentOrder.RESOURCE_COURSE)
        self.assertEqual(kwargs["resource"], self.course)
        self.assertEqual(kwargs["amount"], Decimal("799.00"))
        self.assertEqual(kwargs["currency"], "INR")

    def test_paid_track_checkout_passes_plan_price_to_payment(self):
        with patch("payments.views.checkout._start_payment") as start_payment:
            start_payment.return_value = object()
            response = self.client.get(
                reverse("quiz:track_checkout", kwargs={"track_id": self.track.id})
            )

        self.assertIs(response, start_payment.return_value)
        kwargs = start_payment.call_args.kwargs
        self.assertEqual(kwargs["resource_type"], PaymentOrder.RESOURCE_TRACK)
        self.assertEqual(kwargs["resource"], self.track)
        self.assertEqual(kwargs["amount"], Decimal("799.00"))
        self.assertEqual(kwargs["currency"], "INR")

    def test_paid_exam_checkout_passes_exam_price_to_payment(self):
        with patch("payments.views.checkout._start_payment") as start_payment:
            start_payment.return_value = object()
            response = self.client.get(
                reverse("quiz:exam_checkout", kwargs={"exam_id": self.exam.id})
            )

        self.assertIs(response, start_payment.return_value)
        kwargs = start_payment.call_args.kwargs
        self.assertEqual(kwargs["resource_type"], PaymentOrder.RESOURCE_EXAM)
        self.assertEqual(kwargs["resource"], self.exam)
        self.assertEqual(kwargs["amount"], Decimal("299.00"))
        self.assertEqual(kwargs["currency"], "INR")
