# payments/tests.py

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from payments.models import (
    PaymentOrder,
    PaymentTransaction,
    PaymentWebhookEvent,
)

from payments.services.fulfillment_service import (
    PaymentFulfillmentService,
)

from quiz.models import (
    Coupon,
    CouponRedemption,
    Exam,
    ExamTrack,
)

from quiz.services.coupon_service import (
    CouponAlreadyRedeemedError,
    CouponError,
    CouponService,
)

from subscriptions.models import (
    SubscriptionPlan,
)


User = get_user_model()


class PaymentIntegrationBaseTestCase(TestCase):
    """
    Common fixtures for payment/coupon integration tests.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="payment-test-user",
            password="test-password",
        )

        self.now = timezone.now()

        self.track = ExamTrack.objects.create(
            title="Payment Test Track",
            slug="payment-test-track",
            pricing_type=ExamTrack.PRICING_LIFETIME,
            lifetime_price=Decimal("1000.00"),
            currency="INR",
            is_active=True,
        )

        self.exam = Exam.objects.create(
            title="Payment Test Exam",
            track=self.track,
            duration_seconds=3600,
            question_count=10,
            passing_score=50,
            is_free=False,
            price=Decimal("1000.00"),
            currency="INR",
            is_published=True,
        )

        self.plan = SubscriptionPlan.objects.create(
            name="Payment Test Plan",
            code="PAYMENT_TEST_PLAN",
        )

        self.coupon = Coupon.objects.create(
            code="SAVE20",
            percent_off=20,
            valid_from=self.now - timezone.timedelta(days=1),
            valid_to=self.now + timezone.timedelta(days=1),
        )

    # =========================================================
    # HELPERS
    # =========================================================

    def create_exam_order(
        self,
        *,
        amount=Decimal("800.00"),
        original_amount=Decimal("1000.00"),
        discount_amount=Decimal("200.00"),
        coupon=None,
        status=PaymentOrder.STATUS_PENDING,
    ):
        return PaymentOrder.objects.create(
            user=self.user,
            order_number=(
                f"ORD-EXAM-{PaymentOrder.objects.count() + 1}"
            ),
            resource_type=PaymentOrder.RESOURCE_EXAM,
            exam=self.exam,
            original_amount=original_amount,
            discount_amount=discount_amount,
            amount=amount,
            coupon=coupon,
            currency="INR",
            status=status,
        )

    def create_track_order(
        self,
        *,
        amount=Decimal("800.00"),
        original_amount=Decimal("1000.00"),
        discount_amount=Decimal("200.00"),
        coupon=None,
        status=PaymentOrder.STATUS_PENDING,
    ):
        return PaymentOrder.objects.create(
            user=self.user,
            order_number=(
                f"ORD-TRACK-{PaymentOrder.objects.count() + 1}"
            ),
            resource_type=PaymentOrder.RESOURCE_TRACK,
            track=self.track,
            original_amount=original_amount,
            discount_amount=discount_amount,
            amount=amount,
            coupon=coupon,
            currency="INR",
            status=status,
        )

    def create_success_transaction(
        self,
        order,
        transaction_id="TXN-TEST-001",
    ):
        return PaymentTransaction.objects.create(
            order=order,
            gateway="dummy",
            gateway_transaction_id=transaction_id,
            amount=order.amount,
            currency=order.currency,
            status=PaymentTransaction.STATUS_SUCCESS,
        )

    def create_failed_transaction(
        self,
        order,
        transaction_id="TXN-FAILED-001",
    ):
        return PaymentTransaction.objects.create(
            order=order,
            gateway="dummy",
            gateway_transaction_id=transaction_id,
            amount=order.amount,
            currency=order.currency,
            status=PaymentTransaction.STATUS_FAILED,
            failure_reason="Payment failed",
        )


# =============================================================
# COUPON CALCULATION
# =============================================================


class CouponCalculationTests(PaymentIntegrationBaseTestCase):

    def test_percentage_coupon_calculates_correct_discount(self):
        discount = self.coupon.calculate_discount(
            Decimal("1000.00")
        )

        self.assertEqual(
            discount,
            Decimal("200.00"),
        )

    def test_final_amount_is_correct(self):
        original = Decimal("1000.00")

        discount = self.coupon.calculate_discount(
            original
        )

        final_amount = original - discount

        self.assertEqual(
            final_amount,
            Decimal("800.00"),
        )


# =============================================================
# PAYMENT ORDER
# =============================================================


class PaymentOrderCouponTests(PaymentIntegrationBaseTestCase):

    def test_order_stores_coupon_pricing_snapshot(self):
        order = self.create_exam_order(
            coupon=self.coupon,
        )

        self.assertEqual(
            order.original_amount,
            Decimal("1000.00"),
        )

        self.assertEqual(
            order.discount_amount,
            Decimal("200.00"),
        )

        self.assertEqual(
            order.amount,
            Decimal("800.00"),
        )

        self.assertEqual(
            order.coupon,
            self.coupon,
        )

        self.assertEqual(
            order.amount,
            order.original_amount
            - order.discount_amount,
        )


# =============================================================
# COUPON REDEMPTION
# =============================================================


class CouponRedemptionIntegrationTests(
    PaymentIntegrationBaseTestCase
):

    def test_coupon_redemption_creates_audit_record(self):
        order = self.create_exam_order(
            coupon=self.coupon,
            status=PaymentOrder.STATUS_PAID,
        )

        redemption = (
            CouponService.redeem_order_coupon(
                order
            )
        )

        self.assertIsInstance(
            redemption,
            CouponRedemption,
        )

        self.assertEqual(
            redemption.coupon,
            self.coupon,
        )

        self.assertEqual(
            redemption.user,
            self.user,
        )

        self.assertEqual(
            redemption.order,
            order,
        )

        self.assertEqual(
            redemption.original_amount,
            Decimal("1000.00"),
        )

        self.assertEqual(
            redemption.discount_amount,
            Decimal("200.00"),
        )

        self.assertEqual(
            redemption.final_amount,
            Decimal("800.00"),
        )

    def test_coupon_used_count_increases_once(self):
        order = self.create_exam_order(
            coupon=self.coupon,
            status=PaymentOrder.STATUS_PAID,
        )

        CouponService.redeem_order_coupon(
            order
        )

        self.coupon.refresh_from_db()

        self.assertEqual(
            self.coupon.used_count,
            1,
        )

    def test_duplicate_redemption_is_rejected(self):
        order = self.create_exam_order(
            coupon=self.coupon,
            status=PaymentOrder.STATUS_PAID,
        )

        CouponService.redeem_order_coupon(
            order
        )

        with self.assertRaises(
            CouponAlreadyRedeemedError
        ):
            CouponService.redeem_order_coupon(
                order
            )

        self.assertEqual(
            CouponRedemption.objects.filter(
                order=order
            ).count(),
            1,
        )

        self.coupon.refresh_from_db()

        self.assertEqual(
            self.coupon.used_count,
            1,
        )


# =============================================================
# PAYMENT TRANSACTION
# =============================================================


class PaymentTransactionIntegrationTests(
    PaymentIntegrationBaseTestCase
):

    def test_success_transaction_matches_order_amount(self):
        order = self.create_exam_order(
            coupon=self.coupon,
        )

        transaction = (
            self.create_success_transaction(
                order
            )
        )

        self.assertEqual(
            transaction.amount,
            Decimal("800.00"),
        )

        self.assertEqual(
            transaction.amount,
            order.amount,
        )

        self.assertEqual(
            transaction.status,
            PaymentTransaction.STATUS_SUCCESS,
        )

    def test_failed_transaction_does_not_become_success(self):
        order = self.create_exam_order(
            coupon=self.coupon,
        )

        transaction = (
            self.create_failed_transaction(
                order
            )
        )

        self.assertEqual(
            transaction.status,
            PaymentTransaction.STATUS_FAILED,
        )

        self.assertNotEqual(
            transaction.status,
            PaymentTransaction.STATUS_SUCCESS,
        )


# =============================================================
# EXAM PAYMENT FULFILLMENT
# =============================================================


class ExamPaymentFulfillmentTests(
    PaymentIntegrationBaseTestCase
):

    def test_successful_exam_payment_fulfills_order(self):
        self.track.subscription_plans.add(
            self.plan
        )

        order = self.create_exam_order(
            coupon=self.coupon,
        )

        transaction = (
            self.create_success_transaction(
                order,
                "TXN-EXAM-001",
            )
        )

        result = (
            PaymentFulfillmentService.fulfill(
                transaction
            )
        )

        order.refresh_from_db()

        self.assertTrue(
            result["success"]
        )

        self.assertEqual(
            order.status,
            PaymentOrder.STATUS_PAID,
        )

        self.assertIsNotNone(
            order.paid_at
        )

        self.assertIsNotNone(
            result["subscription"]
        )

        self.assertIsNotNone(
            result["entitlement"]
        )

        self.coupon.refresh_from_db()

        self.assertEqual(
            self.coupon.used_count,
            1,
        )

        self.assertEqual(
            CouponRedemption.objects.filter(
                order=order
            ).count(),
            1,
        )

    def test_failed_payment_cannot_be_fulfilled(self):
        order = self.create_exam_order(
            coupon=self.coupon,
        )

        transaction = (
            self.create_failed_transaction(
                order,
                "TXN-EXAM-FAILED",
            )
        )

        with self.assertRaises(
            ValidationError
        ):
            PaymentFulfillmentService.fulfill(
                transaction
            )

        order.refresh_from_db()
        self.coupon.refresh_from_db()

        self.assertEqual(
            order.status,
            PaymentOrder.STATUS_PENDING,
        )

        self.assertEqual(
            self.coupon.used_count,
            0,
        )

        self.assertEqual(
            CouponRedemption.objects.filter(
                order=order
            ).count(),
            0,
        )

    def test_exam_fulfillment_is_idempotent(self):
        self.track.subscription_plans.add(
            self.plan
        )

        order = self.create_exam_order(
            coupon=self.coupon,
        )

        transaction = (
            self.create_success_transaction(
                order,
                "TXN-EXAM-IDEMPOTENT",
            )
        )

        first_result = (
            PaymentFulfillmentService.fulfill(
                transaction
            )
        )

        second_result = (
            PaymentFulfillmentService.fulfill(
                transaction
            )
        )

        self.assertTrue(
            first_result["success"]
        )

        self.assertTrue(
            second_result["success"]
        )

        self.assertTrue(
            second_result["already_fulfilled"]
        )

        self.assertEqual(
            CouponRedemption.objects.filter(
                order=order
            ).count(),
            1,
        )

        self.coupon.refresh_from_db()

        self.assertEqual(
            self.coupon.used_count,
            1,
        )


# =============================================================
# TRACK PAYMENT FULFILLMENT
# =============================================================


class TrackPaymentFulfillmentTests(
    PaymentIntegrationBaseTestCase
):

    def test_successful_track_payment_fulfills_order(self):
        self.track.subscription_plans.add(
            self.plan
        )

        order = self.create_track_order(
            coupon=self.coupon,
        )

        transaction = (
            self.create_success_transaction(
                order,
                "TXN-TRACK-001",
            )
        )

        result = (
            PaymentFulfillmentService.fulfill(
                transaction
            )
        )

        order.refresh_from_db()

        self.assertTrue(
            result["success"]
        )

        self.assertEqual(
            order.status,
            PaymentOrder.STATUS_PAID,
        )

        self.assertIsNotNone(
            order.paid_at
        )

        self.assertIsNotNone(
            result["subscription"]
        )

        self.assertIsNotNone(
            result["entitlement"]
        )

        self.coupon.refresh_from_db()

        self.assertEqual(
            self.coupon.used_count,
            1,
        )

        self.assertEqual(
            CouponRedemption.objects.filter(
                order=order
            ).count(),
            1,
        )


# =============================================================
# COUPON VALIDITY
# =============================================================


class CouponValidityIntegrationTests(
    PaymentIntegrationBaseTestCase
):

    def test_expired_coupon_cannot_be_validated(self):
        # The model requires valid_to > valid_from.
        # Both timestamps are therefore moved into the past.
        self.coupon.valid_from = (
            self.now - timezone.timedelta(days=10)
        )
        self.coupon.valid_to = (
            self.now - timezone.timedelta(days=1)
        )
        self.coupon.save()

        with self.assertRaises(CouponError) as ctx:
            CouponService.validate_coupon(
                self.coupon.code
            )

        self.assertEqual(
            str(ctx.exception),
            "Coupon has expired.",
        )

    def test_inactive_coupon_cannot_be_validated(self):
        self.coupon.is_active = False
        self.coupon.save()

        with self.assertRaises(CouponError) as ctx:
            CouponService.validate_coupon(
                self.coupon.code
            )

        self.assertEqual(
            str(ctx.exception),
            "Coupon is inactive.",
        )

    def test_coupon_usage_limit_is_respected(self):
        self.coupon.usage_limit = 1
        self.coupon.used_count = 1
        self.coupon.save()

        with self.assertRaises(CouponError) as ctx:
            CouponService.validate_coupon(
                self.coupon.code
            )

        self.assertEqual(
            str(ctx.exception),
            "Coupon usage limit has been reached.",
        )



# =============================================================
# WEBHOOK IDEMPOTENCY
# =============================================================


class PaymentWebhookIntegrationTests(
    TestCase
):

    def test_duplicate_gateway_event_is_rejected(self):
        PaymentWebhookEvent.objects.create(
            gateway="dummy",
            event_id="EVENT-001",
            event_type="payment.success",
            payload={
                "payment_id": "PAY-001",
            },
        )

        with self.assertRaises(Exception):
            PaymentWebhookEvent.objects.create(
                gateway="dummy",
                event_id="EVENT-001",
                event_type="payment.success",
                payload={
                    "payment_id": "PAY-001",
                },
            )