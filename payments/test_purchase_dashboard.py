from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from courses.models import Course
from organizations.models.access import ResourceAccess
from payments.models import PaymentOrder
from quiz.models import Exam
from subscriptions.models import SubscriptionEntitlement, SubscriptionPlan
from subscriptions.services import SubscriptionService


User = get_user_model()


class PurchasedLearningDashboardTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="dashboard-purchase-user",
            password="test-password",
        )
        self.plan = SubscriptionPlan.objects.create(
            name="Dashboard Purchase Plan",
            code="DASHBOARD_PURCHASE_PLAN",
            price=Decimal("100.00"),
            currency="INR",
            is_active=True,
        )
        self.client.force_login(self.user)

    def _course(self):
        course = Course.objects.create(
            title="Purchased AWS Course",
            description="Dashboard test course",
            level="beginner",
            is_public=True,
            is_published=True,
            approval_status=Course.APPROVAL_APPROVED,
        )
        course.subscription_plans.add(self.plan)
        return course

    def _subscription(self, order_id):
        return SubscriptionService.create_subscription(
            plan=self.plan,
            user=self.user,
            organization=None,
            granted_by=None,
            subscribed_by_admin=False,
            payment_status="success",
            order_id=order_id,
            start_at=None,
        )

    def test_individual_course_access_appears_on_dashboard(self):
        course = self._course()
        subscription = self._subscription("DASH-COURSE-1")
        SubscriptionEntitlement.objects.create(
            subscription=subscription,
            resource_type=SubscriptionEntitlement.RESOURCE_COURSE,
            course=course,
            is_active=True,
        )
        ResourceAccess.objects.create(
            user=self.user,
            resource_type=ResourceAccess.RESOURCE_COURSE,
            course=course,
            source=ResourceAccess.SOURCE_INDIVIDUAL,
            subscription=subscription,
            is_active=True,
        )

        response = self.client.get(reverse("quiz:student_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, course.title)

    def test_individual_exam_access_appears_on_dashboard(self):
        exam = Exam.objects.create(
            title="Purchased AWS Exam",
            question_count=10,
            duration_seconds=1800,
            passing_score=70,
            is_published=True,
            is_free=False,
            price=Decimal("100.00"),
        )
        subscription = self._subscription("DASH-EXAM-1")
        SubscriptionEntitlement.objects.create(
            subscription=subscription,
            resource_type=SubscriptionEntitlement.RESOURCE_EXAM,
            exam=exam,
            is_active=True,
        )
        ResourceAccess.objects.create(
            user=self.user,
            resource_type=ResourceAccess.RESOURCE_EXAM,
            exam=exam,
            source=ResourceAccess.SOURCE_INDIVIDUAL,
            subscription=subscription,
            is_active=True,
        )

        response = self.client.get(reverse("quiz:student_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, exam.title)

    def test_success_page_points_user_to_owned_resource(self):
        course = self._course()
        order = PaymentOrder.objects.create(
            user=self.user,
            resource_type=PaymentOrder.RESOURCE_COURSE,
            course=course,
            amount=Decimal("100.00"),
            currency="INR",
            status=PaymentOrder.STATUS_PAID,
        )

        response = self.client.get(
            reverse(
                "payments:payment_success",
                kwargs={"order_number": order.order_number},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Start Learning")

    def test_unpaid_order_cannot_render_success_page(self):
        course = self._course()
        order = PaymentOrder.objects.create(
            user=self.user,
            resource_type=PaymentOrder.RESOURCE_COURSE,
            course=course,
            amount=Decimal("100.00"),
            currency="INR",
            status=PaymentOrder.STATUS_PENDING,
        )

        response = self.client.get(
            reverse(
                "payments:payment_success",
                kwargs={"order_number": order.order_number},
            )
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn(
            reverse(
                "payments:payment_checkout",
                kwargs={"order_number": order.order_number},
            ),
            response.url,
        )
