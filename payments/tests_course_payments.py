from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from courses.models import Course
from payments.models import PaymentOrder, PaymentTransaction
from payments.services.fulfillment_service import PaymentFulfillmentService
from payments.services.order_service import OrderService
from subscriptions.models import SubscriptionEntitlement, SubscriptionPlan


User = get_user_model()


class CoursePaymentTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="course-payment-user",
            password="test-password",
        )
        self.course = Course.objects.create(
            title="Payment Course",
            description="Course used by payment regression tests.",
            level="beginner",
            owner_type=Course.OWNER_PLATFORM,
            is_public=True,
            is_published=True,
            approval_status=Course.APPROVAL_APPROVED,
            created_by=self.user,
        )
        self.plan = SubscriptionPlan.objects.create(
            name="Course Test Plan",
            code="course-test-plan",
            duration_days=30,
            price=Decimal("499.00"),
            currency="INR",
            is_active=True,
        )
        self.course.subscription_plans.add(self.plan)

    def test_order_uses_canonical_course_plan_price(self):
        order = OrderService.create_order(
            user=self.user,
            resource_type=PaymentOrder.RESOURCE_COURSE,
            resource=self.course,
            amount=Decimal("499.00"),
            currency="INR",
        )
        self.assertEqual(order.original_amount, Decimal("499.00"))
        self.assertEqual(order.amount, Decimal("499.00"))
        self.assertEqual(order.currency, "INR")

    def test_order_rejects_tampered_course_price(self):
        with self.assertRaises(ValidationError):
            OrderService.create_order(
                user=self.user,
                resource_type=PaymentOrder.RESOURCE_COURSE,
                resource=self.course,
                amount=Decimal("1.00"),
                currency="INR",
            )

    def test_successful_course_payment_grants_course_access(self):
        order = PaymentOrder.objects.create(
            user=self.user,
            order_number="ORD-COURSE-TEST-1",
            resource_type=PaymentOrder.RESOURCE_COURSE,
            course=self.course,
            original_amount=Decimal("499.00"),
            discount_amount=Decimal("0.00"),
            amount=Decimal("499.00"),
            currency="INR",
            status=PaymentOrder.STATUS_PENDING,
        )
        transaction = PaymentTransaction.objects.create(
            order=order,
            gateway="dummy",
            gateway_transaction_id="TXN-COURSE-TEST-1",
            amount=order.amount,
            currency=order.currency,
            status=PaymentTransaction.STATUS_SUCCESS,
        )

        result = PaymentFulfillmentService.fulfill(transaction)

        self.assertTrue(result["success"])
        self.assertEqual(order.__class__.objects.get(pk=order.pk).status, PaymentOrder.STATUS_PAID)
        self.assertTrue(
            SubscriptionEntitlement.objects.filter(
                subscription__user=self.user,
                resource_type=SubscriptionEntitlement.RESOURCE_COURSE,
                course=self.course,
                is_active=True,
            ).exists()
        )
