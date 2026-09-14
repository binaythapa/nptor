from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from organizations.models import Organization, OrganizationMember
from subscriptions.models import Subscription, SubscriptionPlan


class UserMonitoringTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="global-admin",
            email="admin@example.test",
            password="test-password",
        )
        self.user = User.objects.create_user(
            username="rohan",
            first_name="Rohan",
            last_name="Karki",
            email="rohan@example.test",
            password="test-password",
        )
        self.organization = Organization.objects.create(
            name="ABC College",
            slug="abc-college",
            org_type=Organization.TYPE_COLLEGE,
        )
        OrganizationMember.objects.create(
            user=self.user,
            organization=self.organization,
            role=OrganizationMember.ROLE_STUDENT,
            is_active=True,
        )
        self.plan = SubscriptionPlan.objects.create(
            name="Premium Account",
            code="premium-account",
            product_type=SubscriptionPlan.PRODUCT_ACCOUNT,
            access_mode=SubscriptionPlan.ACCESS_ALL,
            interval_unit=SubscriptionPlan.INTERVAL_MONTH,
            interval_count=1,
            price=1999,
            currency="INR",
        )
        Subscription.objects.create(
            user=self.user,
            plan=self.plan,
            status=Subscription.STATUS_ACTIVE,
            starts_at=timezone.now(),
            expires_at=timezone.now() + timedelta(days=30),
        )
        self.client.force_login(self.admin)

    def test_user_directory_shows_organization_role_and_subscription(self):
        response = self.client.get(reverse("accounts:user_monitoring"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ABC College")
        self.assertContains(response, "Student")
        self.assertContains(response, "Premium Account")
        self.assertContains(
            response,
            reverse("accounts:user_monitoring_detail", args=[self.user.pk]),
        )

    def test_user_detail_shows_membership_and_subscription_information(self):
        response = self.client.get(
            reverse("accounts:user_monitoring_detail", args=[self.user.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "User 360")
        self.assertContains(response, "ABC College")
        self.assertContains(response, "Organization Student")
        self.assertContains(response, "Premium Account")
        self.assertContains(response, "Active")
