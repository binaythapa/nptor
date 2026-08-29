# quiz/tests/test_coupon_service.py

from decimal import Decimal
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from payments.models import PaymentOrder
from quiz.models import Coupon, CouponRedemption
from quiz.services.coupon_service import (
    CouponService,
    CouponError,
    InvalidCouponError,
    CouponNotApplicableError,
    CouponUsageLimitError,
    CouponAlreadyRedeemedError,
)


User = get_user_model()


class CouponServiceTests(TestCase):

    def setUp(self):
        self.now = timezone.now()

        self.user = User.objects.create_user(
            username="coupon_student",
            email="coupon@example.com",
            password="TestPassword123!",
        )

    # =========================================================
    # HELPERS
    # =========================================================

    def create_coupon(self, **kwargs):
        defaults = {
            "code": "SAVE20",
            "percent_off": 20,
            "valid_from": self.now - timedelta(days=1),
            "valid_to": self.now + timedelta(days=1),
            "is_active": True,
        }

        defaults.update(kwargs)

        return Coupon.objects.create(**defaults)

    def create_order(
        self,
        *,
        amount=Decimal("800.00"),
        original_amount=Decimal("1000.00"),
        discount_amount=Decimal("200.00"),
        coupon=None,
    ):
        return PaymentOrder.objects.create(
            order_number=(
                f"ORD-{timezone.now().timestamp()}"
                .replace(".", "")
            ),
            user=self.user,
            resource_type=PaymentOrder.RESOURCE_COURSE,
            amount=amount,
            original_amount=original_amount,
            discount_amount=discount_amount,
            coupon=coupon,
            currency="INR",
            status=PaymentOrder.STATUS_PENDING,
        )

    # =========================================================
    # NORMALIZATION
    # =========================================================

    def test_normalize_code(self):
        result = CouponService.normalize_code(
            "  save20  "
        )

        self.assertEqual(
            result,
            "SAVE20",
        )

    def test_normalize_none_returns_empty_string(self):
        self.assertEqual(
            CouponService.normalize_code(None),
            "",
        )

    # =========================================================
    # GET COUPON
    # =========================================================

    def test_get_coupon(self):
        coupon = self.create_coupon()

        result = CouponService.get_coupon(
            "save20"
        )

        self.assertEqual(
            result,
            coupon,
        )

    def test_get_coupon_invalid_code(self):
        with self.assertRaises(
            InvalidCouponError
        ):
            CouponService.get_coupon(
                "DOESNOTEXIST"
            )

    def test_get_coupon_empty_code(self):
        with self.assertRaises(
            InvalidCouponError
        ):
            CouponService.get_coupon("")

    # =========================================================
    # VALIDATION
    # =========================================================

    def test_validate_valid_coupon(self):
        coupon = self.create_coupon()

        result = CouponService.validate_coupon(
            "SAVE20"
        )

        self.assertEqual(
            result,
            coupon,
        )

    def test_validate_inactive_coupon(self):
        self.create_coupon(
            is_active=False
        )

        with self.assertRaises(
            InvalidCouponError
        ):
            CouponService.validate_coupon(
                "SAVE20"
            )

    def test_validate_future_coupon(self):
        self.create_coupon(
            valid_from=self.now + timedelta(days=1),
            valid_to=self.now + timedelta(days=2),
        )

        with self.assertRaises(
            InvalidCouponError
        ):
            CouponService.validate_coupon(
                "SAVE20",
                at=self.now,
            )

    def test_validate_expired_coupon(self):
        self.create_coupon(
            valid_from=self.now - timedelta(days=3),
            valid_to=self.now - timedelta(days=1),
        )

        with self.assertRaises(
            InvalidCouponError
        ):
            CouponService.validate_coupon(
                "SAVE20",
                at=self.now,
            )

    def test_validate_usage_limit(self):
        self.create_coupon(
            usage_limit=5,
            used_count=5,
        )

        with self.assertRaises(
            CouponUsageLimitError
        ):
            CouponService.validate_coupon(
                "SAVE20"
            )

    # =========================================================
    # CHECK COUPON
    # =========================================================

    def test_check_coupon_returns_coupon_and_none(self):
        coupon = self.create_coupon()

        result, error = CouponService.check_coupon(
            "SAVE20"
        )

        self.assertEqual(
            result,
            coupon,
        )

        self.assertIsNone(error)

    def test_check_coupon_returns_error(self):
        coupon, error = CouponService.check_coupon(
            "INVALID"
        )

        self.assertIsNone(
            coupon
        )

        self.assertTrue(
            error
        )

    # =========================================================
    # DISCOUNT
    # =========================================================

    def test_calculate_percentage_discount(self):
        coupon = self.create_coupon(
            percent_off=20
        )

        discount = CouponService.calculate_discount(
            coupon,
            Decimal("1000.00"),
        )

        self.assertEqual(
            discount,
            Decimal("200.00"),
        )

    def test_calculate_flat_discount(self):
        coupon = self.create_coupon(
            code="FLAT100",
            percent_off=None,
            flat_off=Decimal("100.00"),
        )

        discount = CouponService.calculate_discount(
            coupon,
            Decimal("1000.00"),
        )

        self.assertEqual(
            discount,
            Decimal("100.00"),
        )

    def test_discount_cannot_exceed_amount(self):
        coupon = self.create_coupon(
            code="BIGOFF",
            percent_off=None,
            flat_off=Decimal("2000.00"),
        )

        discount = CouponService.calculate_discount(
            coupon,
            Decimal("1000.00"),
        )

        self.assertEqual(
            discount,
            Decimal("1000.00"),
        )

    def test_invalid_coupon_instance_for_discount(self):
        with self.assertRaises(
            ValidationError
        ):
            CouponService.calculate_discount(
                object(),
                Decimal("1000.00"),
            )

    # =========================================================
    # PRICE CALCULATION
    # =========================================================

    def test_calculate_price_without_coupon(self):
        result = CouponService.calculate_price(
            Decimal("1000.00")
        )

        self.assertEqual(
            result["original_amount"],
            Decimal("1000.00"),
        )

        self.assertEqual(
            result["discount_amount"],
            Decimal("0.00"),
        )

        self.assertEqual(
            result["final_amount"],
            Decimal("1000.00"),
        )

    def test_calculate_price_with_coupon(self):
        coupon = self.create_coupon(
            percent_off=20
        )

        result = CouponService.calculate_price(
            Decimal("1000.00"),
            coupon,
        )

        self.assertEqual(
            result["original_amount"],
            Decimal("1000.00"),
        )

        self.assertEqual(
            result["discount_amount"],
            Decimal("200.00"),
        )

        self.assertEqual(
            result["final_amount"],
            Decimal("800.00"),
        )

    # =========================================================
    # REDEMPTION
    # =========================================================

    def test_redeem_creates_redemption(self):
        coupon = self.create_coupon(
            usage_limit=10,
            used_count=0,
        )

        order = self.create_order(
            amount=Decimal("800.00"),
            original_amount=Decimal("1000.00"),
            discount_amount=Decimal("200.00"),
            coupon=coupon,
        )

        redemption = CouponService.redeem(
            coupon,
            user=self.user,
            order=order,
            original_amount=Decimal("1000.00"),
            discount_amount=Decimal("200.00"),
            final_amount=Decimal("800.00"),
        )

        self.assertIsNotNone(
            redemption.pk
        )

        self.assertEqual(
            CouponRedemption.objects.count(),
            1,
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

    def test_redeem_increments_used_count(self):
        coupon = self.create_coupon(
            usage_limit=10,
            used_count=0,
        )

        order = self.create_order(
            amount=Decimal("800.00"),
            original_amount=Decimal("1000.00"),
            discount_amount=Decimal("200.00"),
            coupon=coupon,
        )

        CouponService.redeem(
            coupon,
            user=self.user,
            order=order,
            original_amount=Decimal("1000.00"),
            discount_amount=Decimal("200.00"),
            final_amount=Decimal("800.00"),
        )

        coupon.refresh_from_db()

        self.assertEqual(
            coupon.used_count,
            1,
        )

    def test_duplicate_redemption_is_rejected(self):
        coupon = self.create_coupon(
            usage_limit=10,
        )

        order = self.create_order(
            amount=Decimal("800.00"),
            original_amount=Decimal("1000.00"),
            discount_amount=Decimal("200.00"),
            coupon=coupon,
        )

        CouponService.redeem(
            coupon,
            user=self.user,
            order=order,
            original_amount=Decimal("1000.00"),
            discount_amount=Decimal("200.00"),
            final_amount=Decimal("800.00"),
        )

        with self.assertRaises(
            CouponAlreadyRedeemedError
        ):
            CouponService.redeem(
                coupon,
                user=self.user,
                order=order,
                original_amount=Decimal("1000.00"),
                discount_amount=Decimal("200.00"),
                final_amount=Decimal("800.00"),
            )

    # =========================================================
    # ORDER OWNERSHIP
    # =========================================================

    def test_redeem_rejects_wrong_user(self):
        coupon = self.create_coupon()

        order = self.create_order(
            amount=Decimal("800.00"),
            original_amount=Decimal("1000.00"),
            discount_amount=Decimal("200.00"),
            coupon=coupon,
        )

        another_user = User.objects.create_user(
            username="another_student",
            email="another@example.com",
            password="TestPassword123!",
        )

        with self.assertRaises(
            ValidationError
        ):
            CouponService.redeem(
                coupon,
                user=another_user,
                order=order,
                original_amount=Decimal("1000.00"),
                discount_amount=Decimal("200.00"),
                final_amount=Decimal("800.00"),
            )

    # =========================================================
    # COUPON ↔ ORDER
    # =========================================================

    def test_redeem_rejects_coupon_not_attached_to_order(self):
        coupon = self.create_coupon()

        order = self.create_order(
            amount=Decimal("1000.00"),
            original_amount=Decimal("1000.00"),
            discount_amount=Decimal("0.00"),
            coupon=None,
        )

        with self.assertRaises(
            ValidationError
        ):
            CouponService.redeem(
                coupon,
                user=self.user,
                order=order,
                original_amount=Decimal("1000.00"),
                discount_amount=Decimal("0.00"),
                final_amount=Decimal("1000.00"),
            )

    # =========================================================
    # FINANCIAL INTEGRITY
    # =========================================================

    def test_redeem_rejects_discount_greater_than_original(self):
        coupon = self.create_coupon()

        order = self.create_order(
            amount=Decimal("0.00"),
            original_amount=Decimal("1000.00"),
            discount_amount=Decimal("1000.00"),
            coupon=coupon,
        )

        with self.assertRaises(
            ValidationError
        ):
            CouponService.redeem(
                coupon,
                user=self.user,
                order=order,
                original_amount=Decimal("1000.00"),
                discount_amount=Decimal("1001.00"),
                final_amount=Decimal("0.00"),
            )

    def test_redeem_rejects_wrong_final_amount(self):
        coupon = self.create_coupon()

        order = self.create_order(
            amount=Decimal("800.00"),
            original_amount=Decimal("1000.00"),
            discount_amount=Decimal("200.00"),
            coupon=coupon,
        )

        with self.assertRaises(
            ValidationError
        ):
            CouponService.redeem(
                coupon,
                user=self.user,
                order=order,
                original_amount=Decimal("1000.00"),
                discount_amount=Decimal("200.00"),
                final_amount=Decimal("900.00"),
            )

    # =========================================================
    # REDEEM ORDER COUPON
    # =========================================================

    def test_redeem_order_coupon_without_coupon_returns_none(self):
        order = self.create_order(
            amount=Decimal("1000.00"),
            original_amount=Decimal("1000.00"),
            discount_amount=Decimal("0.00"),
            coupon=None,
        )

        result = CouponService.redeem_order_coupon(
            order
        )

        self.assertIsNone(
            result
        )

    def test_redeem_order_coupon(self):
        coupon = self.create_coupon(
            usage_limit=10,
        )

        order = self.create_order(
            amount=Decimal("800.00"),
            original_amount=Decimal("1000.00"),
            discount_amount=Decimal("200.00"),
            coupon=coupon,
        )

        redemption = CouponService.redeem_order_coupon(
            order
        )

        self.assertIsNotNone(
            redemption
        )

        self.assertEqual(
            redemption.order_id,
            order.id,
        )

        self.assertEqual(
            redemption.coupon_id,
            coupon.id,
        )

        coupon.refresh_from_db()

        self.assertEqual(
            coupon.used_count,
            1,
        )