from decimal import Decimal
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from organizations.models.access import ResourceAccess
from organizations.models.organization import Organization

from quiz.models import Exam, ExamTrack

from subscriptions.models import (
    Subscription,
    SubscriptionEntitlement,
    SubscriptionPlan,
)

from subscriptions.services.access_service import AccessService

User = get_user_model()

class SubscriptionModelTests(TestCase):
    """Tests for Subscription and SubscriptionEntitlement models."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="subscription_user",
            password="testpass123",
        )

        self.organization = Organization.objects.create(
            name="Test Organization",
            slug="test-organization",
            org_type=Organization.TYPE_SCHOOL,
        )

        self.plan = SubscriptionPlan.objects.create(
            name="Monthly Plan",
            code="monthly-plan",
            duration_days=30,
            price=Decimal("999.00"),
            currency="INR",
            is_active=True,
        )

        self.lifetime_plan = SubscriptionPlan.objects.create(
            name="Lifetime Plan",
            code="lifetime-plan",
            duration_days=None,
            price=Decimal("1999.00"),
            currency="INR",
            is_active=True,
        )


    def create_subscription(self, **overrides):
        defaults = {
            "plan": self.plan,
            "user": self.user,
            "organization": None,
            "status": Subscription.STATUS_ACTIVE,
            "starts_at": timezone.now() - timedelta(days=1),
            "expires_at": timezone.now() + timedelta(days=29),
            "amount": self.plan.price,
            "currency": self.plan.currency,
            "payment_status": "paid",
        }

        defaults.update(overrides)

        return Subscription.objects.create(**defaults)

    def test_active_subscription_is_valid(self):
        subscription = self.create_subscription()

        self.assertTrue(subscription.is_valid())

    def test_expired_subscription_is_not_valid(self):
        subscription = self.create_subscription(
            starts_at=timezone.now() - timedelta(days=31),
            expires_at=timezone.now() - timedelta(days=1),
        )

        self.assertFalse(subscription.is_valid())

    def test_cancelled_subscription_is_not_valid(self):
        subscription = self.create_subscription(
            status=Subscription.STATUS_CANCELLED,
            cancelled_at=timezone.now(),
            cancellation_reason="Test cancellation",
        )

        self.assertFalse(subscription.is_valid())

    def test_pending_subscription_is_not_valid(self):
        subscription = self.create_subscription(
            status=Subscription.STATUS_PENDING,
        )

        self.assertFalse(subscription.is_valid())

    def test_lifetime_subscription_is_valid(self):
        subscription = self.create_subscription(
            plan=self.lifetime_plan,
            expires_at=None,
            amount=self.lifetime_plan.price,
        )

        self.assertTrue(subscription.is_valid())

    def test_subscription_can_be_created_for_user(self):
        subscription = self.create_subscription()

        self.assertEqual(
            subscription.user,
            self.user,
        )

        self.assertIsNone(
            subscription.organization,
        )

        self.assertTrue(
            subscription.is_user_subscription()
        )

    def test_subscription_can_be_created_for_organization(self):
        subscription = self.create_subscription(
            user=None,
            organization=self.organization,
        )

        self.assertIsNone(subscription.user)

        self.assertEqual(
            subscription.organization,
            self.organization,
        )

        self.assertTrue(
            subscription.is_organization_subscription()
        )

    def test_subscription_requires_owner(self):
        subscription = Subscription(
            plan=self.plan,
            user=None,
            organization=None,
            status=Subscription.STATUS_ACTIVE,
            starts_at=timezone.now(),
            expires_at=timezone.now() + timedelta(days=30),
            amount=self.plan.price,
            currency=self.plan.currency,
            payment_status="paid",
        )

        from django.core.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            subscription.full_clean()

    def test_subscription_cannot_have_two_owners(self):
        subscription = Subscription(
            plan=self.plan,
            user=self.user,
            organization=self.organization,
            status=Subscription.STATUS_ACTIVE,
            starts_at=timezone.now(),
            expires_at=timezone.now() + timedelta(days=30),
            amount=self.plan.price,
            currency=self.plan.currency,
            payment_status="paid",
        )

        from django.core.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            subscription.full_clean()

    def test_subscription_entitlement_can_be_created_for_track(self):
        subscription = self.create_subscription()

        track = ExamTrack.objects.create(
            title="Test Track",
            is_active=True,
        )

        entitlement = SubscriptionEntitlement.objects.create(
            subscription=subscription,
            resource_type=SubscriptionEntitlement.RESOURCE_TRACK,
            track=track,
            is_active=True,
        )

        self.assertEqual(
            entitlement.track,
            track,
        )

        self.assertEqual(
            entitlement.get_resource(),
            track,
        )

        self.assertTrue(
            entitlement.is_valid()
        )




    def test_subscription_entitlement_can_be_created_for_exam(self):
        subscription = self.create_subscription()

        exam = Exam.objects.create(
            title="Test Exam",
            duration_seconds=3600,
            is_published=True,
        )

        entitlement = SubscriptionEntitlement.objects.create(
            subscription=subscription,
            resource_type=SubscriptionEntitlement.RESOURCE_EXAM,
            exam=exam,
            is_active=True,
        )

        self.assertEqual(
            entitlement.exam,
            exam,
        )

        self.assertEqual(
            entitlement.get_resource(),
            exam,
        )

        self.assertTrue(
            entitlement.is_valid()
        )






    def test_inactive_entitlement_is_not_valid(self):
        subscription = self.create_subscription()

        track = ExamTrack.objects.create(
            title="Inactive Entitlement Track",
            is_active=True,
        )

        entitlement = SubscriptionEntitlement.objects.create(
            subscription=subscription,
            resource_type=SubscriptionEntitlement.RESOURCE_TRACK,
            track=track,
            is_active=False,
        )

        self.assertFalse(
            entitlement.is_valid()
        )

    def test_entitlement_with_expired_subscription_is_not_valid(self):
        subscription = self.create_subscription(
            starts_at=timezone.now() - timedelta(days=31),
            expires_at=timezone.now() - timedelta(days=1),
        )

        track = ExamTrack.objects.create(
            title="Expired Track",
            is_active=True,
        )

        entitlement = SubscriptionEntitlement.objects.create(
            subscription=subscription,
            resource_type=SubscriptionEntitlement.RESOURCE_TRACK,
            track=track,
            is_active=True,
        )

        self.assertFalse(
            entitlement.is_valid()
        )

    def test_entitlement_requires_correct_resource(self):
        subscription = self.create_subscription()

        entitlement = SubscriptionEntitlement(
            subscription=subscription,
            resource_type=SubscriptionEntitlement.RESOURCE_TRACK,
            track=None,
            course=None,
            exam=None,
            is_active=True,
        )

        from django.core.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            entitlement.full_clean()

    def test_subscription_owner_helper_returns_owner(self):
        subscription = self.create_subscription()

        self.assertEqual(
            subscription.get_owner(),
            self.user,
        )






class AccessServiceTests(TestCase):
    """
    Tests the centralized ResourceAccess authorization layer.

    Main flows:

        Direct access
        Subscription-backed access
        Track -> Exam inheritance
        Organization subscription
        Organization entitlement
        Student assignment
        Organization ResourceAccess
    """

    # =========================================================
    # HELPERS
    # =========================================================

    def create_user(
        self,
        username,
    ):
        return User.objects.create_user(
            username=username,
            password="TestPassword123!",
        )

    def create_plan(
        self,
        name="Monthly Plan",
        price=Decimal("999.00"),
        duration_days=30,
    ):
        return SubscriptionPlan.objects.create(
            name=name,
            price=price,
            currency="INR",
            duration_days=duration_days,
            is_active=True,
        )

    def create_track(
        self,
        title="SnowPro Core",
        slug="snowpro-core",
    ):
        return ExamTrack.objects.create(
            title=title,
            slug=slug,
            description="Test track",
            subscription_scope=ExamTrack.TRACK,
            pricing_type=ExamTrack.PRICING_MONTHLY,
            currency="INR",
            is_active=True,
        )

    def create_exam(
        self,
        title="SnowPro Core Exam",
        track=None,
    ):
        return Exam.objects.create(
            title=title,
            track=track,
            question_count=10,
            duration_seconds=3600,
            level=1,
            passing_score=50.0,
            is_free=False,
            price=Decimal("999.00"),
            currency="INR",
            is_published=True,
        )

    def create_subscription(
        self,
        *,
        user=None,
        organization=None,
        plan=None,
        status=None,
        starts_at=None,
        expires_at=None,
        payment_status="paid",
    ):
        plan = (
            plan
            or self.create_plan()
        )

        starts_at = (
            starts_at
            or timezone.now()
        )

        if (
            expires_at is None
            and plan.duration_days is not None
        ):
            expires_at = (
                starts_at
                + timedelta(
                    days=plan.duration_days
                )
            )

        return Subscription.objects.create(
            user=user,
            organization=organization,
            plan=plan,
            status=(
                status
                or Subscription.STATUS_ACTIVE
            ),
            starts_at=starts_at,
            expires_at=expires_at,
            amount=plan.price,
            currency=plan.currency,
            payment_status=payment_status,
        )

    def create_organization(
        self,
        name="Test Organization",
        slug="test-organization",
    ):
        return Organization.objects.create(
            name=name,
            slug=slug,
            org_type=Organization.TYPE_INSTITUTE,
            is_active=True,
        )

    # =========================================================
    # 1. NO ACCESS
    # =========================================================

    def test_student_has_no_access_without_resource_access(
        self,
    ):
        student = self.create_user(
            "no_access_student"
        )

        exam = self.create_exam()

        result = AccessService.has_access(
            student=student,
            resource_type=(
                AccessService.RESOURCE_EXAM
            ),
            resource=exam,
        )

        self.assertFalse(result)

    # =========================================================
    # 2. DIRECT EXAM ACCESS
    # =========================================================

    def test_direct_exam_access_is_allowed(
        self,
    ):
        student = self.create_user(
            "direct_exam_student"
        )

        exam = self.create_exam()

        AccessService.grant_access(
            user=student,
            resource_type=(
                AccessService.RESOURCE_EXAM
            ),
            resource=exam,
            source=(
                ResourceAccess.SOURCE_ADMIN
            ),
        )

        result = AccessService.has_access(
            student=student,
            resource_type=(
                AccessService.RESOURCE_EXAM
            ),
            resource=exam,
        )

        self.assertTrue(result)

    # =========================================================
    # 3. REVOKED DIRECT ACCESS
    # =========================================================

    def test_revoked_direct_exam_access_is_denied(
        self,
    ):
        student = self.create_user(
            "revoked_exam_student"
        )

        exam = self.create_exam()

        access, created = (
            AccessService.grant_access(
                user=student,
                resource_type=(
                    AccessService.RESOURCE_EXAM
                ),
                resource=exam,
                source=(
                    ResourceAccess.SOURCE_ADMIN
                ),
            )
        )

        self.assertTrue(created)

        access.revoke()

        result = AccessService.has_access(
            student=student,
            resource_type=(
                AccessService.RESOURCE_EXAM
            ),
            resource=exam,
        )

        self.assertFalse(result)

    # =========================================================
    # 4. VALID SUBSCRIPTION-BACKED EXAM ACCESS
    # =========================================================

    def test_valid_subscription_exam_access_is_allowed(
        self,
    ):
        student = self.create_user(
            "subscription_exam_student"
        )

        plan = self.create_plan()

        subscription = self.create_subscription(
            user=student,
            plan=plan,
        )

        exam = self.create_exam()

        AccessService.grant_access(
            user=student,
            resource_type=(
                AccessService.RESOURCE_EXAM
            ),
            resource=exam,
            source=(
                ResourceAccess.SOURCE_INDIVIDUAL
            ),
            subscription=subscription,
        )

        result = AccessService.has_access(
            student=student,
            resource_type=(
                AccessService.RESOURCE_EXAM
            ),
            resource=exam,
        )

        self.assertTrue(result)

    # =========================================================
    # 5. EXPIRED SUBSCRIPTION DENIES ACCESS
    # =========================================================
        # =========================================================
    # 5. EXPIRED SUBSCRIPTION DENIES ACCESS
    # =========================================================

    def test_expired_subscription_exam_access_is_denied(
        self,
    ):
        """
        An expired ResourceAccess record must deny exam access.

        The access record is created through AccessService so all
        ResourceAccess business rules are respected. The timestamps
        are then moved into a valid historical period.
        """

        student = self.create_user(
            "expired_exam_student"
        )

        exam = self.create_exam()

        # Create a normal, valid access record through the
        # centralized access service.
        access, created = (
            AccessService.grant_access(
                user=student,
                resource_type=(
                    AccessService.RESOURCE_EXAM
                ),
                resource=exam,
                source=(
                    ResourceAccess.SOURCE_INDIVIDUAL
                ),
            )
        )

        self.assertTrue(created)

        # Move the valid access window into the past.
        granted_at = (
            timezone.now()
            - timedelta(days=10)
        )

        expires_at = (
            granted_at
            + timedelta(days=1)
        )

        access.granted_at = granted_at
        access.expires_at = expires_at

        # Use update_fields so the existing access record is
        # persisted without recreating it through the model's
        # constructor.
        access.save(
            update_fields=[
                "granted_at",
                "expires_at",
            ]
        )

        result = AccessService.has_access(
            student=student,
            resource_type=(
                AccessService.RESOURCE_EXAM
            ),
            resource=exam,
        )

        self.assertFalse(result)




            # =========================================================
    # 6. TRACK ACCESS INHERITS TO EXAM
    # =========================================================

    def test_track_access_grants_exam_access(
        self,
    ):
        student = self.create_user(
            "track_student"
        )

        plan = self.create_plan()

        subscription = self.create_subscription(
            user=student,
            plan=plan,
        )

        track = self.create_track()

        exam = self.create_exam(
            track=track,
        )

        AccessService.grant_access(
            user=student,
            resource_type=(
                AccessService.RESOURCE_TRACK
            ),
            resource=track,
            source=(
                ResourceAccess.SOURCE_INDIVIDUAL
            ),
            subscription=subscription,
        )

        result = AccessService.has_access(
            student=student,
            resource_type=(
                AccessService.RESOURCE_EXAM
            ),
            resource=exam,
        )

        self.assertTrue(result)

    # =========================================================
    # 7. TRACK ACCESS DOES NOT GRANT UNRELATED EXAM ACCESS
    # =========================================================

    def test_track_access_does_not_grant_unrelated_exam_access(
        self,
    ):
        student = self.create_user(
            "unrelated_exam_student"
        )

        plan = self.create_plan()

        subscription = self.create_subscription(
            user=student,
            plan=plan,
        )

        track_one = self.create_track(
            title="Track One",
            slug="track-one",
        )

        track_two = ExamTrack.objects.create(
            title="Track Two",
            slug="track-two",
            description="Second test track",
            subscription_scope=ExamTrack.TRACK,
            pricing_type=ExamTrack.PRICING_MONTHLY,
            currency="INR",
            is_active=True,
        )

        exam = self.create_exam(
            title="Track Two Exam",
            track=track_two,
        )

        AccessService.grant_access(
            user=student,
            resource_type=(
                AccessService.RESOURCE_TRACK
            ),
            resource=track_one,
            source=(
                ResourceAccess.SOURCE_INDIVIDUAL
            ),
            subscription=subscription,
        )

        result = AccessService.has_access(
            student=student,
            resource_type=(
                AccessService.RESOURCE_EXAM
            ),
            resource=exam,
        )

        self.assertFalse(result)

    # =========================================================
    # 8. REVOKED TRACK DENIES INHERITED EXAM ACCESS
    # =========================================================

    def test_revoked_track_access_denies_exam_access(
        self,
    ):
        student = self.create_user(
            "revoked_track_student"
        )

        plan = self.create_plan()

        subscription = self.create_subscription(
            user=student,
            plan=plan,
        )

        track = self.create_track()

        exam = self.create_exam(
            track=track,
        )

        access, created = (
            AccessService.grant_access(
                user=student,
                resource_type=(
                    ResourceAccess.RESOURCE_TRACK
                ),
                resource=track,
                source=(
                    ResourceAccess.SOURCE_INDIVIDUAL
                ),
                subscription=subscription,
            )
        )

        self.assertTrue(created)

        access.revoke()

        result = AccessService.has_access(
            student=student,
            resource_type=(
                AccessService.RESOURCE_EXAM
            ),
            resource=exam,
        )

        self.assertFalse(result)

    # =========================================================
    # 9. ORGANIZATION ENTITLEMENT
    # =========================================================

    def test_organization_entitlement_is_detected(
        self,
    ):
        student = self.create_user(
            "organization_student"
        )

        organization = self.create_organization()

        plan = self.create_plan()

        subscription = self.create_subscription(
            organization=organization,
            plan=plan,
        )

        track = self.create_track()

        entitlement = (
            SubscriptionEntitlement.objects.create(
                subscription=subscription,
                resource_type=(
                    SubscriptionEntitlement.RESOURCE_TRACK
                ),
                track=track,
                is_active=True,
            )
        )

        result = (
            AccessService.get_organization_entitlement(
                organization=organization,
                resource_type=(
                    AccessService.RESOURCE_TRACK
                ),
                resource=track,
            )
        )

        self.assertEqual(
            result,
            entitlement,
        )

    # =========================================================
    # 10. ORGANIZATION CAN GRANT TRACK TO STUDENT
    # =========================================================

    def test_organization_can_grant_track_to_student(
        self,
    ):
        student = self.create_user(
            "assigned_track_student"
        )

        organization = self.create_organization()

        plan = self.create_plan()

        subscription = self.create_subscription(
            organization=organization,
            plan=plan,
        )

        track = self.create_track()

        SubscriptionEntitlement.objects.create(
            subscription=subscription,
            resource_type=(
                SubscriptionEntitlement.RESOURCE_TRACK
            ),
            track=track,
            is_active=True,
        )

        result = (
            AccessService.grant_student_access(
                student=student,
                organization=organization,
                resource_type=(
                    AccessService.RESOURCE_TRACK
                ),
                resource=track,
            )
        )

        self.assertTrue(
            result["assignment_created"]
        )

        self.assertTrue(
            result["access"].is_active
        )

        self.assertEqual(
            result["assignment"].student,
            student,
        )

        self.assertEqual(
            result["assignment"].organization,
            organization,
        )

        self.assertEqual(
            result["assignment"].track,
            track,
        )

    # =========================================================
    # 11. ORGANIZATION TRACK GRANTS EXAM ACCESS
    # =========================================================

    def test_organization_track_access_grants_exam_access(
        self,
    ):
        student = self.create_user(
            "organization_exam_student"
        )

        organization = self.create_organization()

        plan = self.create_plan()

        subscription = self.create_subscription(
            organization=organization,
            plan=plan,
        )

        track = self.create_track()

        exam = self.create_exam(
            track=track,
        )

        SubscriptionEntitlement.objects.create(
            subscription=subscription,
            resource_type=(
                SubscriptionEntitlement.RESOURCE_TRACK
            ),
            track=track,
            is_active=True,
        )

        AccessService.grant_student_access(
            student=student,
            organization=organization,
            resource_type=(
                AccessService.RESOURCE_TRACK
            ),
            resource=track,
        )

        result = AccessService.has_access(
            student=student,
            resource_type=(
                AccessService.RESOURCE_EXAM
            ),
            resource=exam,
        )

        self.assertTrue(result)

    # =========================================================
    # 12. ORGANIZATION ACCESS IS STUDENT-SPECIFIC
    # =========================================================

    def test_organization_track_access_is_student_specific(
        self,
    ):
        student_one = self.create_user(
            "organization_student_one"
        )

        student_two = self.create_user(
            "organization_student_two"
        )

        organization = self.create_organization()

        plan = self.create_plan()

        subscription = self.create_subscription(
            organization=organization,
            plan=plan,
        )

        track = self.create_track()

        exam = self.create_exam(
            track=track,
        )

        SubscriptionEntitlement.objects.create(
            subscription=subscription,
            resource_type=(
                SubscriptionEntitlement.RESOURCE_TRACK
            ),
            track=track,
            is_active=True,
        )

        AccessService.grant_student_access(
            student=student_one,
            organization=organization,
            resource_type=(
                AccessService.RESOURCE_TRACK
            ),
            resource=track,
        )

        student_one_access = (
            AccessService.has_access(
                student=student_one,
                resource_type=(
                    AccessService.RESOURCE_EXAM
                ),
                resource=exam,
            )
        )

        student_two_access = (
            AccessService.has_access(
                student=student_two,
                resource_type=(
                    AccessService.RESOURCE_EXAM
                ),
                resource=exam,
            )
        )

        self.assertTrue(
            student_one_access
        )

        self.assertFalse(
            student_two_access
        )

    # =========================================================
    # 13. ORGANIZATION CANNOT ASSIGN WITHOUT ENTITLEMENT
    # =========================================================

    def test_organization_cannot_grant_without_entitlement(
        self,
    ):
        student = self.create_user(
            "no_org_entitlement_student"
        )

        organization = self.create_organization()

        track = self.create_track()

        with self.assertRaises(
            ValueError
        ) as context:

            AccessService.grant_student_access(
                student=student,
                organization=organization,
                resource_type=(
                    AccessService.RESOURCE_TRACK
                ),
                resource=track,
            )

        self.assertIn(
            "active subscription entitlement",
            str(context.exception),
        )

    # =========================================================
    # 14. EXAM WITHOUT TRACK DOES NOT INHERIT TRACK ACCESS
    # =========================================================

    def test_exam_without_track_has_no_inherited_access(
        self,
    ):
        student = self.create_user(
            "standalone_exam_student"
        )

        plan = self.create_plan()

        subscription = self.create_subscription(
            user=student,
            plan=plan,
        )

        track = self.create_track()

        standalone_exam = self.create_exam(
            title="Standalone Exam",
            track=None,
        )

        AccessService.grant_access(
            user=student,
            resource_type=(
                ResourceAccess.RESOURCE_TRACK
            ),
            resource=track,
            source=(
                ResourceAccess.SOURCE_INDIVIDUAL
            ),
            subscription=subscription,
        )

        result = AccessService.has_access(
            student=student,
            resource_type=(
                AccessService.RESOURCE_EXAM
            ),
            resource=standalone_exam,
        )

        self.assertFalse(result)