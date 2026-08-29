# quiz/tests/test_coupons.py

from decimal import Decimal
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from quiz.models import Coupon


User = get_user_model()


class CouponModelTests(TestCase):
    """
    Tests for the Coupon model itself.

    These tests deliberately focus on model-level business rules.
    CouponService tests should cover service-level validation and
    redemption behavior separately.
    """

    def setUp(self):
        self.now = timezone.now()

    # =========================================================
    # HELPERS
    # =========================================================

    def make_coupon(self, **kwargs):
        defaults = {
            "code": "SAVE20",
            "percent_off": 20,
            "valid_from": self.now - timedelta(days=1),
            "valid_to": self.now + timedelta(days=1),
        }

        defaults.update(kwargs)

        return Coupon.objects.create(**defaults)

    # =========================================================
    # CODE NORMALIZATION
    # =========================================================

    def test_coupon_code_is_normalized_to_uppercase(self):
        coupon = self.make_coupon(
            code="  save20  "
        )

        self.assertEqual(
            coupon.code,
            "SAVE20",
        )

    # =========================================================
    # PERCENTAGE DISCOUNT
    # =========================================================

    def test_percentage_discount(self):
        coupon = self.make_coupon(
            percent_off=20,
        )

        discount = coupon.calculate_discount(
            Decimal("1000.00")
        )

        self.assertEqual(
            discount,
            Decimal("200.00"),
        )

    # =========================================================
    # FLAT DISCOUNT
    # =========================================================

    def test_flat_discount(self):
        coupon = self.make_coupon(
            code="FLAT100",
            percent_off=None,
            flat_off=Decimal("100.00"),
        )

        discount = coupon.calculate_discount(
            Decimal("1000.00")
        )

        self.assertEqual(
            discount,
            Decimal("100.00"),
        )

    # =========================================================
    # DISCOUNT CANNOT EXCEED PRICE
    # =========================================================

    def test_discount_is_capped_at_purchase_amount(self):
        coupon = self.make_coupon(
            code="FLAT2000",
            percent_off=None,
            flat_off=Decimal("2000.00"),
        )

        discount = coupon.calculate_discount(
            Decimal("1000.00")
        )

        self.assertEqual(
            discount,
            Decimal("1000.00"),
        )

    # =========================================================
    # NEGATIVE PURCHASE AMOUNT
    # =========================================================

    def test_negative_purchase_amount_is_rejected(self):
        coupon = self.make_coupon()

        with self.assertRaises(ValidationError):
            coupon.calculate_discount(
                Decimal("-100.00")
            )

    # =========================================================
    # PERCENTAGE VALIDATION
    # =========================================================

    def test_zero_percent_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.make_coupon(
                percent_off=0,
            )

    def test_percentage_above_100_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.make_coupon(
                percent_off=101,
            )

    # =========================================================
    # DISCOUNT TYPE VALIDATION
    # =========================================================

    def test_both_discount_types_are_rejected(self):
        with self.assertRaises(ValidationError):
            self.make_coupon(
                percent_off=20,
                flat_off=Decimal("100.00"),
            )

    def test_no_discount_type_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.make_coupon(
                percent_off=None,
                flat_off=None,
            )

    # =========================================================
    # FLAT DISCOUNT VALIDATION
    # =========================================================

    def test_zero_flat_discount_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.make_coupon(
                percent_off=None,
                flat_off=Decimal("0.00"),
            )

    def test_negative_flat_discount_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.make_coupon(
                percent_off=None,
                flat_off=Decimal("-10.00"),
            )

    # =========================================================
    # VALIDITY PERIOD
    # =========================================================

    def test_coupon_is_valid_inside_validity_window(self):
        coupon = self.make_coupon()

        self.assertTrue(
            coupon.is_valid(at=self.now)
        )

    def test_inactive_coupon_is_invalid(self):
        coupon = self.make_coupon(
            is_active=False,
        )

        self.assertFalse(
            coupon.is_valid(at=self.now)
        )

    def test_coupon_before_valid_from_is_invalid(self):
        coupon = self.make_coupon(
            valid_from=self.now + timedelta(days=1),
            valid_to=self.now + timedelta(days=2),
        )

        self.assertFalse(
            coupon.is_valid(at=self.now)
        )

    def test_coupon_after_valid_to_is_invalid(self):
        coupon = self.make_coupon(
            valid_from=self.now - timedelta(days=2),
            valid_to=self.now - timedelta(days=1),
        )

        self.assertFalse(
            coupon.is_valid(at=self.now)
        )

    # =========================================================
    # USAGE LIMIT
    # =========================================================

    def test_unlimited_coupon_has_usage_remaining(self):
        coupon = self.make_coupon(
            usage_limit=None,
        )

        self.assertTrue(
            coupon.has_usage_remaining()
        )

    def test_coupon_with_remaining_usage_is_valid(self):
        coupon = self.make_coupon(
            usage_limit=5,
            used_count=4,
        )

        self.assertTrue(
            coupon.has_usage_remaining()
        )

        self.assertTrue(
            coupon.is_valid(at=self.now)
        )

    def test_coupon_at_usage_limit_is_invalid(self):
        coupon = self.make_coupon(
            usage_limit=5,
            used_count=5,
        )

        self.assertFalse(
            coupon.has_usage_remaining()
        )

        self.assertFalse(
            coupon.is_valid(at=self.now)
        )

    # =========================================================
    # USAGE LIMIT VALIDATION
    # =========================================================

    def test_zero_usage_limit_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.make_coupon(
                usage_limit=0,
            )

    def test_used_count_cannot_exceed_usage_limit(self):
        with self.assertRaises(ValidationError):
            self.make_coupon(
                usage_limit=5,
                used_count=6,
            )

    # =========================================================
    # VALIDITY DATE VALIDATION
    # =========================================================

    def test_valid_to_must_be_after_valid_from(self):
        with self.assertRaises(ValidationError):
            self.make_coupon(
                valid_from=self.now,
                valid_to=self.now,
            )

    # =========================================================
    # GLOBAL COUPON
    # =========================================================

    def test_coupon_without_resource_is_global(self):
        coupon = self.make_coupon()

        self.assertTrue(
            coupon.is_global
        )

    # =========================================================
    # RESOURCE APPLICABILITY
    # =========================================================

    def test_global_coupon_applies_to_any_resource(self):
        coupon = self.make_coupon()

        self.assertTrue(
            coupon.applies_to()
        )

    # =========================================================
    # EXTRA TRIAL DAYS
    # =========================================================

    def test_extra_trial_days_defaults_to_zero(self):
        coupon = self.make_coupon()

        self.assertEqual(
            coupon.extra_trial_days,
            0,
        )


class CouponRedemptionModelTests(TestCase):
    """
    Tests the financial integrity rules of CouponRedemption.

    Actual redemption/usage behavior belongs in CouponService tests.
    """

    def setUp(self):
        self.now = timezone.now()

    def test_redemption_model_can_be_imported(self):
        from quiz.models import CouponRedemption

        self.assertIsNotNone(
            CouponRedemption
        )