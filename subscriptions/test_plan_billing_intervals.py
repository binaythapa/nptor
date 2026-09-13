from datetime import datetime
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from subscriptions.models import SubscriptionPlan
from subscriptions.services.subscription_service import SubscriptionService


class SubscriptionPlanBillingIntervalTests(TestCase):
    def test_plan_supports_calendar_billing_intervals(self):
        plan = SubscriptionPlan(
            name="Quarterly",
            code="quarterly-test",
            product_type=SubscriptionPlan.PRODUCT_TRACK,
            access_mode=SubscriptionPlan.ACCESS_SINGLE_RESOURCE,
            interval_unit=SubscriptionPlan.INTERVAL_MONTH,
            interval_count=3,
            price=Decimal("799.00"),
            currency="INR",
        )

        plan.full_clean()

        self.assertFalse(plan.is_lifetime())
        self.assertEqual(plan.get_billing_interval_label(), "3 months")

    def test_lifetime_plan_has_no_billing_interval(self):
        plan = SubscriptionPlan(
            name="Lifetime",
            code="lifetime-test",
            product_type=SubscriptionPlan.PRODUCT_TRACK,
            access_mode=SubscriptionPlan.ACCESS_SINGLE_RESOURCE,
            interval_unit=SubscriptionPlan.INTERVAL_LIFETIME,
            interval_count=None,
            price=Decimal("4999.00"),
            currency="INR",
        )

        plan.full_clean()

        self.assertTrue(plan.is_lifetime())
        self.assertEqual(plan.get_billing_interval_label(), "Lifetime")

    def test_subscription_expiry_uses_calendar_months(self):
        plan = SubscriptionPlan(
            name="Monthly",
            code="monthly-calendar-test",
            product_type=SubscriptionPlan.PRODUCT_TRACK,
            access_mode=SubscriptionPlan.ACCESS_SINGLE_RESOURCE,
            interval_unit=SubscriptionPlan.INTERVAL_MONTH,
            interval_count=1,
            price=Decimal("299.00"),
            currency="INR",
        )
        starts_at = timezone.make_aware(datetime(2026, 1, 31, 10, 0, 0))

        expires_at = SubscriptionService.calculate_expiry(plan, starts_at)

        self.assertEqual(expires_at, timezone.make_aware(datetime(2026, 2, 28, 10, 0, 0)))

    def test_subscription_expiry_for_lifetime_is_none(self):
        plan = SubscriptionPlan(
            name="Lifetime",
            code="lifetime-expiry-test",
            product_type=SubscriptionPlan.PRODUCT_TRACK,
            access_mode=SubscriptionPlan.ACCESS_SINGLE_RESOURCE,
            interval_unit=SubscriptionPlan.INTERVAL_LIFETIME,
            interval_count=None,
            price=Decimal("4999.00"),
            currency="INR",
        )

        self.assertIsNone(SubscriptionService.calculate_expiry(plan, timezone.now()))
