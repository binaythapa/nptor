from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from courses.models import Course
from organizations.models import Organization
from organizations.models.membership import OrganizationMember
from organizations.services.public_resource_checkout import (
    create_organization_checkout,
    complete_organization_checkout,
)
from quiz.models import ExamTrack
from subscriptions.models import Payment, Subscription, SubscriptionEntitlement, SubscriptionPlan


class OrganizationPublicResourceCheckoutTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Checkout School",
            slug="checkout-school",
            org_type=Organization.TYPE_SCHOOL,
        )
        self.admin = self._create_user("checkout-admin@example.com")
        OrganizationMember.objects.create(
            organization=self.organization,
            user=self.admin,
            role=OrganizationMember.ROLE_ORG_ADMIN,
            is_active=True,
        )
        self.course = Course.objects.create(
            title="Public Checkout Course",
            slug="public-checkout-course",
            owner_type=Course.OWNER_PLATFORM,
            approval_status=Course.APPROVAL_APPROVED,
            is_published=True,
            is_public=True,
        )
        self.plan = SubscriptionPlan.objects.create(
            name="Checkout Course Plan",
            product_type=SubscriptionPlan.PRODUCT_COURSE,
            access_mode=SubscriptionPlan.ACCESS_SINGLE_RESOURCE,
            price=Decimal("999.00"),
            currency="INR",
            is_active=True,
            interval_unit=SubscriptionPlan.INTERVAL_MONTH,
            interval_count=1,
        )
        self.course.subscription_plans.add(self.plan)

    def _create_user(self, email):
        from django.contrib.auth import get_user_model
        return get_user_model().objects.create_user(
            username=email,
            email=email,
            password="test-password",
        )

    def test_checkout_starts_with_pending_subscription_and_payment(self):
        checkout = create_organization_checkout(
            organization=self.organization,
            actor=self.admin,
            resource_type=SubscriptionEntitlement.RESOURCE_COURSE,
            resource_id=self.course.id,
            plan_id=self.plan.id,
        )

        self.assertEqual(checkout.subscription.status, Subscription.STATUS_PENDING)
        self.assertEqual(checkout.subscription.payment_status, "pending")
        self.assertEqual(checkout.payment.status, Payment.STATUS_PENDING)
        self.assertEqual(checkout.payment.organization, self.organization)
        self.assertEqual(checkout.payment.amount, Decimal("999.00"))
        self.assertFalse(
            SubscriptionEntitlement.objects.filter(subscription=checkout.subscription).exists()
        )

    def test_successful_dummy_checkout_activates_subscription_and_entitlement(self):
        checkout = create_organization_checkout(
            organization=self.organization,
            actor=self.admin,
            resource_type=SubscriptionEntitlement.RESOURCE_COURSE,
            resource_id=self.course.id,
            plan_id=self.plan.id,
        )

        complete_organization_checkout(checkout.payment.id, actor=self.admin)
        checkout.subscription.refresh_from_db()
        checkout.payment.refresh_from_db()

        self.assertEqual(checkout.subscription.status, Subscription.STATUS_ACTIVE)
        self.assertEqual(checkout.subscription.payment_status, "paid")
        self.assertEqual(checkout.payment.status, Payment.STATUS_SUCCESS)
        self.assertTrue(
            SubscriptionEntitlement.objects.filter(
                subscription=checkout.subscription,
                course=self.course,
                is_active=True,
            ).exists()
        )

    def test_checkout_cannot_be_completed_by_different_organization_member(self):
        other_org = Organization.objects.create(
            name="Other School",
            slug="other-school",
            org_type=Organization.TYPE_SCHOOL,
        )
        other_admin = self._create_user("other-admin@example.com")
        OrganizationMember.objects.create(
            organization=other_org,
            user=other_admin,
            role=OrganizationMember.ROLE_ORG_ADMIN,
            is_active=True,
        )
        checkout = create_organization_checkout(
            organization=self.organization,
            actor=self.admin,
            resource_type=SubscriptionEntitlement.RESOURCE_COURSE,
            resource_id=self.course.id,
            plan_id=self.plan.id,
        )

        with self.assertRaises(Exception):
            complete_organization_checkout(checkout.payment.id, actor=other_admin)

        checkout.payment.refresh_from_db()
        self.assertEqual(checkout.payment.status, Payment.STATUS_PENDING)

    def test_checkout_does_not_grant_student_access_before_payment(self):
        from subscriptions.services import AccessService

        student = self._create_user("checkout-student@example.com")
        OrganizationMember.objects.create(
            organization=self.organization,
            user=student,
            role=OrganizationMember.ROLE_STUDENT,
            is_active=True,
        )
        create_organization_checkout(
            organization=self.organization,
            actor=self.admin,
            resource_type=SubscriptionEntitlement.RESOURCE_COURSE,
            resource_id=self.course.id,
            plan_id=self.plan.id,
        )

        self.assertFalse(AccessService.has_course_access(student, self.course))
