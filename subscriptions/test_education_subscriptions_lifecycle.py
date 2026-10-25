from decimal import Decimal
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from courses.models import Course
from orders.models import Order, OrderItem, ShippingAddress, SubOrder
from organizations.models import (
    Organization,
    OrganizationMember,
    OrganizationRole,
    ResourceAccess,
    ResourceAssignment,
)
from payments.models import PaymentOrder, PaymentTransaction
from payments.services.fulfillment_service import PaymentFulfillmentService
from quiz.models import Exam, ExamTrack, TrackExam
from store.models import Category, Product, ProductVariant
from subscriptions.models import (
    AccountSubscriptionSelection,
    Payment,
    Subscription,
    SubscriptionEntitlement,
    SubscriptionPlan,
)
from subscriptions.services import AccessService, SubscriptionService


User = get_user_model()


class EducationSubscriptionsLifecycleTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="edu_student",
            email="edu_student@example.com",
            password="testpassword123",
        )
        self.other_user = User.objects.create_user(
            username="other_student",
            email="other_student@example.com",
            password="testpassword123",
        )
        self.client.force_login(self.user)

        self.all_access_plan = SubscriptionPlan.objects.create(
            name="All-Access Annual",
            code="all-access-annual",
            product_type=SubscriptionPlan.PRODUCT_ACCOUNT,
            access_mode=SubscriptionPlan.ACCESS_ALL,
            interval_unit=SubscriptionPlan.INTERVAL_YEAR,
            interval_count=1,
            price=Decimal("1200.00"),
            currency="INR",
            is_active=True,
        )

        self.course_plan = SubscriptionPlan.objects.create(
            name="Course Single Plan",
            code="course-single-plan",
            product_type=SubscriptionPlan.PRODUCT_COURSE,
            access_mode=SubscriptionPlan.ACCESS_SINGLE_RESOURCE,
            interval_unit=SubscriptionPlan.INTERVAL_MONTH,
            interval_count=6,
            price=Decimal("300.00"),
            currency="INR",
            is_active=True,
        )

        self.course = Course.objects.create(
            title="Advanced Machine Learning",
            slug="advanced-machine-learning",
            level="advanced",
            is_published=True,
            is_public=True,
            approval_status=Course.APPROVAL_APPROVED,
        )
        self.course.subscription_plans.add(self.course_plan)

        self.track = ExamTrack.objects.create(
            title="Cloud Architect Certification Track",
            slug="cloud-architect-track",
            is_active=True,
        )
        self.track_plan = SubscriptionPlan.objects.create(
            name="Track Plan",
            code="track-plan",
            product_type=SubscriptionPlan.PRODUCT_TRACK,
            access_mode=SubscriptionPlan.ACCESS_SINGLE_RESOURCE,
            interval_unit=SubscriptionPlan.INTERVAL_YEAR,
            interval_count=1,
            price=Decimal("500.00"),
            currency="INR",
            is_active=True,
        )
        self.track.subscription_plans.add(self.track_plan)

        self.exam = Exam.objects.create(
            title="Cloud Architecture Assessment",
            duration_seconds=3600,
            question_count=20,
            is_published=True,
        )
        TrackExam.objects.create(track=self.track, exam=self.exam)

    def test_plan_selection_view_shows_active_plans_and_status(self):
        # 1. Without active subscription
        url = reverse("payments:subscription_plans")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "All-Access Annual")
        self.assertContains(response, "1200.00")
        self.assertNotContains(response, "Current Active Subscription")

        # 2. With active subscription
        sub = SubscriptionService.create_subscription(
            plan=self.all_access_plan,
            user=self.user,
            payment_status=Payment.STATUS_SUCCESS,
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Current Active Subscription")
        self.assertContains(response, "All-Access Annual")
        self.assertContains(response, "Manage Subscriptions")

    def test_unified_dashboard_displays_education_subscriptions_and_entitlements(self):
        sub = SubscriptionService.create_subscription(
            plan=self.course_plan,
            user=self.user,
            payment_status=Payment.STATUS_SUCCESS,
        )
        ent = SubscriptionEntitlement.objects.create(
            subscription=sub,
            resource_type=SubscriptionEntitlement.RESOURCE_COURSE,
            course=self.course,
            is_active=True,
        )
        AccessService.grant_access(
            user=self.user,
            resource_type=ResourceAccess.RESOURCE_COURSE,
            resource=self.course,
            source=ResourceAccess.SOURCE_INDIVIDUAL,
            subscription=sub,
            expires_at=sub.expires_at,
        )

        url = reverse("subscriptions:subscription_history")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Course Single Plan")
        self.assertContains(response, "Advanced Machine Learning")
        self.assertContains(response, "Paid")
        self.assertContains(response, "Active")
        self.assertTrue(AccessService.has_course_access(self.user, self.course))

    def test_user_can_cancel_active_subscription_and_revokes_access(self):
        sub = SubscriptionService.create_subscription(
            plan=self.course_plan,
            user=self.user,
            payment_status=Payment.STATUS_SUCCESS,
        )
        SubscriptionEntitlement.objects.create(
            subscription=sub,
            resource_type=SubscriptionEntitlement.RESOURCE_COURSE,
            course=self.course,
            is_active=True,
        )
        AccessService.grant_access(
            user=self.user,
            resource_type=ResourceAccess.RESOURCE_COURSE,
            resource=self.course,
            source=ResourceAccess.SOURCE_INDIVIDUAL,
            subscription=sub,
            expires_at=sub.expires_at,
        )
        self.assertTrue(AccessService.has_course_access(self.user, self.course))

        cancel_url = reverse("subscriptions:cancel_subscription", kwargs={"subscription_id": sub.id})
        response = self.client.post(cancel_url)
        self.assertRedirects(response, reverse("subscriptions:subscription_history"))

        sub.refresh_from_db()
        self.assertEqual(sub.status, Subscription.STATUS_CANCELLED)
        self.assertIsNotNone(sub.cancelled_at)
        self.assertFalse(sub.is_valid())

        # Access is revoked
        self.assertFalse(AccessService.has_course_access(self.user, self.course))

    def test_overdue_subscription_is_marked_expired_on_dashboard_visit(self):
        past_time = timezone.now() - timedelta(days=2)
        sub = Subscription.objects.create(
            plan=self.course_plan,
            user=self.user,
            status=Subscription.STATUS_ACTIVE,
            starts_at=past_time - timedelta(days=30),
            expires_at=past_time,
            amount=self.course_plan.price,
            currency="INR",
            payment_status="paid",
        )
        self.assertTrue(sub.has_expired())

        # Visit dashboard
        self.client.get(reverse("subscriptions:subscription_history"))
        sub.refresh_from_db()
        self.assertEqual(sub.status, Subscription.STATUS_EXPIRED)

    def test_store_orders_appear_in_unified_dashboard_separately(self):
        # Create Store Order
        category = Category.objects.create(name="Study Books", slug="study-books")
        product = Product.objects.create(
            title="Civil Engineering Handbook",
            slug="civil-handbook",
            category=category,
            product_type=Product.TYPE_PHYSICAL,
            is_active=True,
        )
        variant = ProductVariant.objects.create(
            product=product,
            sku="BOOK-CIVIL-001",
            price=Decimal("750.00"),
            is_active=True,
        )
        address = ShippingAddress.objects.create(
            user=self.user,
            full_name="Student Test",
            phone="9800000000",
            street_address_1="Kathmandu",
            city="Kathmandu",
        )
        store_order = Order.objects.create(
            user=self.user,
            order_number="ORD-STORE-TEST-1",
            shipping_address=address,
            payment_method=Order.PAYMENT_METHOD_COD,
            total_items_amount=Decimal("750.00"),
            shipping_amount=Decimal("50.00"),
            grand_total=Decimal("800.00"),
        )
        suborder = SubOrder.objects.create(
            master_order=store_order,
            suborder_number="SUB-STORE-TEST-1",
            items_subtotal=Decimal("750.00"),
            customer_shipping_charge=Decimal("50.00"),
            vendor_payout_amount=Decimal("650.00"),
            platform_commission=Decimal("100.00"),
            fulfillment_status=SubOrder.FULFILLMENT_SHIPPED,
        )
        OrderItem.objects.create(
            suborder=suborder,
            variant=variant,
            product_title_snapshot=product.title,
            sku_snapshot=variant.sku,
            unit_price=variant.price,
            quantity=1,
            total_price=Decimal("750.00"),
        )

        # Check tab=orders
        url = reverse("subscriptions:subscription_history") + "?tab=orders"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ORD-STORE-TEST-1")
        self.assertContains(response, "NPR 800.00")
        self.assertContains(response, "Cash on Delivery")
        self.assertContains(response, "Independent Store Marketplace Orders")

        # Confirm Store order did not grant any subscription or course access
        self.assertEqual(Subscription.objects.filter(user=self.user).count(), 0)
        self.assertFalse(AccessService.has_course_access(self.user, self.course))

    def test_track_payment_fulfillment_updates_sub_payment_record(self):
        order = PaymentOrder.objects.create(
            user=self.user,
            order_number="ORD-TRK-TEST-99",
            resource_type=PaymentOrder.RESOURCE_TRACK,
            track=self.track,
            amount=self.track_plan.price,
            currency=self.track_plan.currency,
            status=PaymentOrder.STATUS_PENDING,
        )
        txn = PaymentTransaction.objects.create(
            order=order,
            gateway="dummy",
            gateway_transaction_id="TXN-TRK-DUMMY-99",
            amount=order.amount,
            currency=order.currency,
            status=PaymentTransaction.STATUS_SUCCESS,
        )

        result = PaymentFulfillmentService.fulfill(txn)
        self.assertTrue(result["success"])

        order.refresh_from_db()
        self.assertEqual(order.status, PaymentOrder.STATUS_PAID)

        # Track access is active
        self.assertTrue(AccessService.has_track_access(self.user, self.track))
        # Inherited exam access is active
        self.assertTrue(AccessService.has_exam_access(self.user, self.exam))

        # Check Payment model in subscriptions
        sub = Subscription.objects.filter(user=self.user, plan=self.track_plan).first()
        self.assertIsNotNone(sub)
        self.assertEqual(sub.payment_status, "paid")

        sub_payment = Payment.objects.filter(subscription=sub).first()
        self.assertIsNotNone(sub_payment)
        self.assertEqual(sub_payment.status, Payment.STATUS_SUCCESS)

    def test_organization_subscription_isolation_and_learner_allocation(self):
        org = Organization.objects.create(
            name="Kathmandu Tech Academy",
            slug="ktm-tech-academy",
            org_type=Organization.TYPE_SCHOOL,
            is_active=True,
        )
        staff = User.objects.create_user(
            username="org_staff",
            email="staff@example.com",
            password="testpassword123",
        )
        OrganizationMember.objects.create(
            user=staff,
            organization=org,
            role=OrganizationRole.STAFF,
        )
        OrganizationMember.objects.create(
            user=self.user,
            organization=org,
            role=OrganizationRole.STUDENT,
        )

        # 1. Org purchases course subscription
        org_sub = SubscriptionService.create_subscription(
            plan=self.course_plan,
            organization=org,
            user=None,
            payment_status=Payment.STATUS_SUCCESS,
        )
        SubscriptionEntitlement.objects.create(
            subscription=org_sub,
            resource_type=SubscriptionEntitlement.RESOURCE_COURSE,
            course=self.course,
            is_active=True,
        )

        # Student does NOT have access merely because org owns it
        self.assertFalse(AccessService.has_course_access(self.user, self.course))

        # 2. Org assigns course to student
        assignment_result = AccessService.grant_student_access(
            student=self.user,
            organization=org,
            resource_type=AccessService.RESOURCE_COURSE,
            resource=self.course,
        )
        self.assertIsNotNone(assignment_result["assignment"])
        self.assertTrue(AccessService.has_course_access(self.user, self.course))

        # Other user (non-member / unassigned) has no access
        self.assertFalse(AccessService.has_course_access(self.other_user, self.course))

        # 3. Org revokes student access
        AccessService.revoke_student_access(
            student=self.user,
            organization=org,
            resource_type=AccessService.RESOURCE_COURSE,
            resource=self.course,
        )
        self.assertFalse(AccessService.has_course_access(self.user, self.course))

    def test_unauthorized_user_cannot_cancel_another_users_subscription(self):
        sub = SubscriptionService.create_subscription(
            plan=self.course_plan,
            user=self.other_user,
            payment_status=Payment.STATUS_SUCCESS,
        )
        cancel_url = reverse("subscriptions:cancel_subscription", kwargs={"subscription_id": sub.id})
        # Logged in as self.user
        response = self.client.post(cancel_url)
        self.assertEqual(response.status_code, 404)
        sub.refresh_from_db()
        self.assertEqual(sub.status, Subscription.STATUS_ACTIVE)

    def test_payment_order_allows_account_plans(self):
        limited_account_plan = SubscriptionPlan.objects.create(
            name="Limited Bundle Plan",
            code="limited-bundle-plan",
            product_type=SubscriptionPlan.PRODUCT_ACCOUNT,
            access_mode=SubscriptionPlan.ACCESS_LIMITED,
            max_courses=2,
            max_tracks=1,
            interval_unit=SubscriptionPlan.INTERVAL_YEAR,
            interval_count=1,
            price=Decimal("800.00"),
            currency="INR",
            is_active=True,
        )
        order = PaymentOrder(
            user=self.user,
            order_number="ORD-ACCT-TEST-1",
            resource_type=PaymentOrder.RESOURCE_SUBSCRIPTION,
            subscription_plan=limited_account_plan,
            amount=Decimal("800.00"),
            original_amount=Decimal("800.00"),
            currency="INR",
        )
        # full_clean should succeed without ValidationError
        order.full_clean()
        order.save()
        self.assertEqual(order.resource_type, PaymentOrder.RESOURCE_SUBSCRIPTION)

    def test_cancelled_track_subscription_revokes_inherited_exam_access(self):
        sub = SubscriptionService.create_subscription(
            plan=self.track_plan,
            user=self.user,
            payment_status=Payment.STATUS_SUCCESS,
        )
        SubscriptionEntitlement.objects.create(
            subscription=sub,
            resource_type=SubscriptionEntitlement.RESOURCE_TRACK,
            track=self.track,
            is_active=True,
        )
        AccessService.grant_access(
            user=self.user,
            resource_type=ResourceAccess.RESOURCE_TRACK,
            resource=self.track,
            source=ResourceAccess.SOURCE_INDIVIDUAL,
            subscription=sub,
            expires_at=sub.expires_at,
        )
        self.assertTrue(AccessService.has_track_access(self.user, self.track))
        self.assertTrue(AccessService.has_exam_access(self.user, self.exam))

        # Cancel subscription
        cancel_url = reverse("subscriptions:cancel_subscription", kwargs={"subscription_id": sub.id})
        self.client.post(cancel_url)

        self.assertFalse(AccessService.has_track_access(self.user, self.track))
        self.assertFalse(AccessService.has_exam_access(self.user, self.exam))

