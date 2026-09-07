from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from courses.models import Course
from subscriptions.models import Subscription, SubscriptionEntitlement, SubscriptionPlan


class MySQLSafeEntitlementUniquenessTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="entitlement-user")
        self.plan = SubscriptionPlan.objects.create(
            name="Test Plan",
            code="mysql-safe-test-plan",
            price=0,
        )
        self.subscription = Subscription.objects.create(
            user=self.user,
            plan=self.plan,
            status=Subscription.STATUS_ACTIVE,
        )
        self.course = Course.objects.create(
            title="Entitled Course",
            description="Test course",
            level="beginner",
            created_by=self.user,
        )

    def test_duplicate_course_entitlement_is_rejected(self):
        SubscriptionEntitlement.objects.create(
            subscription=self.subscription,
            resource_type=SubscriptionEntitlement.RESOURCE_COURSE,
            course=self.course,
        )
        with self.assertRaises(ValidationError):
            SubscriptionEntitlement.objects.create(
                subscription=self.subscription,
                resource_type=SubscriptionEntitlement.RESOURCE_COURSE,
                course=self.course,
            )

    def test_different_resource_types_can_be_added(self):
        first = SubscriptionEntitlement.objects.create(
            subscription=self.subscription,
            resource_type=SubscriptionEntitlement.RESOURCE_COURSE,
            course=self.course,
        )
        self.assertIsNotNone(first.pk)
        self.assertEqual(self.subscription.entitlements.count(), 1)
