from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from courses.models import Course, CourseExam
from quiz.models import Exam, ExamTrack, TrackExam
from subscriptions.models import SubscriptionPlan
from subscriptions.services import AccessService
from subscriptions.services.account_access_service import AccountAccessService
from subscriptions.services.course_access_service import CourseAccessService
from subscriptions.services.subscription_service import SubscriptionService


User = get_user_model()


class ProductAccessArchitectureTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="product-access-user", password="test-pass")
        self.other = User.objects.create_user(username="product-access-other", password="test-pass")
        self.course_a = Course.objects.create(title="Course A", description="A", level="beginner", is_published=True)
        self.course_b = Course.objects.create(title="Course B", description="B", level="beginner", is_published=True)
        self.track = ExamTrack.objects.create(title="Track B", slug="track-b", is_active=True)
        self.exam = Exam.objects.create(title="Reusable Exam", duration_seconds=60, question_count=1, is_published=True)
        CourseExam.objects.create(course=self.course_a, exam=self.exam)
        CourseExam.objects.create(course=self.course_b, exam=self.exam)
        TrackExam.objects.create(track=self.track, exam=self.exam)

    def _plan(self, *, code, product_type, access_mode=SubscriptionPlan.ACCESS_SINGLE_RESOURCE, max_courses=None, max_tracks=None):
        return SubscriptionPlan.objects.create(
            name=code,
            code=code,
            product_type=product_type,
            access_mode=access_mode,
            max_courses=max_courses,
            max_tracks=max_tracks,
            duration_days=30,
            price=0,
            currency="INR",
            is_active=True,
        )

    def test_exam_is_reusable_across_multiple_courses_and_track(self):
        self.assertEqual(CourseExam.objects.filter(exam=self.exam).count(), 2)
        self.assertEqual(TrackExam.objects.filter(exam=self.exam).count(), 1)

    def test_course_subscription_does_not_grant_track_access(self):
        plan = self._plan(code="course-a-plan", product_type=SubscriptionPlan.PRODUCT_COURSE)
        self.course_a.subscription_plans.add(plan)
        CourseAccessService.grant_admin_access(user=self.user, course=self.course_a, plan=plan, granted_by=self.user)

        self.assertTrue(AccessService.has_course_access(self.user, self.course_a))
        self.assertFalse(AccessService.has_track_access(self.user, self.track))
        self.assertTrue(AccessService.has_exam_access(self.user, self.exam))

    def test_track_subscription_does_not_grant_course_access(self):
        plan = self._plan(code="track-plan", product_type=SubscriptionPlan.PRODUCT_TRACK)
        self.track.subscription_plans.add(plan)
        SubscriptionService.create_or_reactivate_subscription(
            user=self.user,
            resource_type="track",
            resource=self.track,
            plan=plan,
            granted_by=self.user,
        )

        self.assertTrue(AccessService.has_track_access(self.user, self.track))
        self.assertFalse(AccessService.has_course_access(self.user, self.course_a))
        self.assertTrue(AccessService.has_exam_access(self.user, self.exam))

    def test_all_access_account_plan_grants_courses_tracks_and_exams(self):
        plan = self._plan(code="account-all", product_type=SubscriptionPlan.PRODUCT_ACCOUNT, access_mode=SubscriptionPlan.ACCESS_ALL)
        subscription = SubscriptionService.create_subscription(plan=plan, user=self.user, payment_status="not_required")

        self.assertTrue(subscription.is_valid())
        self.assertTrue(AccessService.has_course_access(self.user, self.course_a))
        self.assertTrue(AccessService.has_course_access(self.user, self.course_b))
        self.assertTrue(AccessService.has_track_access(self.user, self.track))
        self.assertTrue(AccessService.has_exam_access(self.user, self.exam))

    def test_limited_account_plan_enforces_user_selectable_course_and_track_quotas(self):
        plan = self._plan(
            code="account-limited",
            product_type=SubscriptionPlan.PRODUCT_ACCOUNT,
            access_mode=SubscriptionPlan.ACCESS_LIMITED,
            max_courses=1,
            max_tracks=1,
        )
        subscription = SubscriptionService.create_subscription(plan=plan, user=self.user, payment_status="not_required")

        AccountAccessService.select_course(subscription=subscription, course=self.course_a)
        AccountAccessService.select_track(subscription=subscription, track=self.track)

        self.assertTrue(AccessService.has_course_access(self.user, self.course_a))
        self.assertFalse(AccessService.has_course_access(self.user, self.course_b))
        self.assertTrue(AccessService.has_track_access(self.user, self.track))
        self.assertTrue(AccessService.has_exam_access(self.user, self.exam))

        with self.assertRaises(ValidationError):
            AccountAccessService.select_course(subscription=subscription, course=self.course_b)

    def test_other_user_does_not_inherit_account_selection(self):
        plan = self._plan(
            code="account-user-specific",
            product_type=SubscriptionPlan.PRODUCT_ACCOUNT,
            access_mode=SubscriptionPlan.ACCESS_LIMITED,
            max_courses=1,
        )
        subscription = SubscriptionService.create_subscription(plan=plan, user=self.user, payment_status="not_required")
        AccountAccessService.select_course(subscription=subscription, course=self.course_a)

        self.assertTrue(AccessService.has_course_access(self.user, self.course_a))
        self.assertFalse(AccessService.has_course_access(self.other, self.course_a))
