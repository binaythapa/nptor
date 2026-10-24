from decimal import Decimal
from django.apps import apps
from django.contrib.auth import get_user_model
from django.test import TestCase

from courses.models import Course
from payments.models import PaymentOrder, PaymentTransaction
from payments.services.fulfillment_service import PaymentFulfillmentService
from orders.models import Order, OrderItem, OrderPayment, SubOrder
from subscriptions.models import SubscriptionPlan

User = get_user_model()


class EducationalIsolationRegressionTests(TestCase):
    """
    Guarantees strict schema isolation between educational payments and Store commerce,
    and proves that educational payment creation and fulfillment continue to work.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="edu_learner",
            email="learner@example.com",
            password="pass",
        )
        self.course = Course.objects.create(
            title="Isolated Educational Course",
            slug="isolated-educational-course",
            approval_status=Course.APPROVAL_APPROVED,
        )
        self.plan = SubscriptionPlan.objects.create(
            name="Course Single Plan",
            code="COURSE_SINGLE_ISOLATION",
            product_type=SubscriptionPlan.PRODUCT_COURSE,
            access_mode=SubscriptionPlan.ACCESS_SINGLE_RESOURCE,
            price=Decimal("1500.00"),
            currency="INR",
            is_active=True,
        )
        self.course.subscription_plans.add(self.plan)

    def test_payment_order_schema_isolation(self):
        """
        Verify that PaymentOrder has zero fields, foreign keys, or reverse relations
        pointing to or originating from the Store apps (store, orders, vendors, cart).
        """
        payment_order_fields = [f.name for f in PaymentOrder._meta.get_fields()]
        store_app_names = {"store", "orders", "vendors", "cart"}

        for field in PaymentOrder._meta.get_fields():
            if field.is_relation and field.related_model:
                app_label = field.related_model._meta.app_label
                self.assertNotIn(
                    app_label,
                    store_app_names,
                    f"PaymentOrder field '{field.name}' is coupled to Store app '{app_label}'!",
                )

        # Confirm PaymentOrder default currency is still INR
        currency_field = PaymentOrder._meta.get_field("currency")
        self.assertEqual(currency_field.default, "INR")

    def test_store_order_schema_isolation(self):
        """
        Verify that Store Order, SubOrder, and OrderPayment do not reference PaymentOrder.
        """
        for model in (Order, SubOrder, OrderPayment, OrderItem):
            for field in model._meta.get_fields():
                if field.is_relation and field.related_model:
                    self.assertNotEqual(
                        field.related_model,
                        PaymentOrder,
                        f"{model.__name__} has an illegal foreign key to PaymentOrder!",
                    )
                    self.assertNotEqual(
                        field.related_model,
                        PaymentTransaction,
                        f"{model.__name__} has an illegal foreign key to PaymentTransaction!",
                    )

    def test_educational_course_payment_order_creation_regression(self):
        """
        Ensure creating and validating an educational PaymentOrder continues to work
        with standard educational validation logic.
        """
        order = PaymentOrder.objects.create(
            user=self.user,
            order_number="ORD-EDU-ISOLATION-001",
            resource_type=PaymentOrder.RESOURCE_COURSE,
            course=self.course,
            amount=Decimal("1500.00"),
            currency="INR",
            status=PaymentOrder.STATUS_PENDING,
        )
        order.full_clean()
        self.assertEqual(order.currency, "INR")
        self.assertEqual(order.resource_type, "course")
        self.assertEqual(order.get_resource(), self.course)

    def test_educational_course_payment_fulfillment_regression(self):
        """
        Ensure PaymentFulfillmentService successfully fulfills an educational Course order.
        """
        order = PaymentOrder.objects.create(
            user=self.user,
            order_number="ORD-EDU-ISOLATION-002",
            resource_type=PaymentOrder.RESOURCE_COURSE,
            course=self.course,
            amount=Decimal("1500.00"),
            currency="INR",
            status=PaymentOrder.STATUS_PENDING,
        )
        txn = PaymentTransaction.objects.create(
            order=order,
            amount=Decimal("1500.00"),
            currency="INR",
            status=PaymentTransaction.STATUS_SUCCESS,
            gateway="dummy",
            gateway_transaction_id="TXN-DUMMY-002",
        )

        result = PaymentFulfillmentService.fulfill(txn)
        self.assertTrue(result["success"])
        order.refresh_from_db()
        self.assertEqual(order.status, PaymentOrder.STATUS_PAID)
        self.assertIsNotNone(order.paid_at)
        self.assertIsNotNone(result.get("subscription"))
