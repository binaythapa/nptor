import datetime
import zoneinfo
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from quiz.models import (
    Question,
    Choice,
    Category,
    Domain,
    UserPracticeStreak,
    DailyPracticeLog,
)
from quiz.services.streak_service import (
    get_business_today,
    record_qualifying_practice,
    get_student_streak_summary,
    KATHMANDU_TZ,
)

User = get_user_model()


class PracticeStreaksPhase2Tests(TestCase):
    """
    Comprehensive verification suite for Phase 2.2 Practice Streaks:
    1. Qualifying practice activity tracking for authenticated students
    2. Single active day counted per calendar day (Asia/Kathmandu)
    3. Consecutive days streak progression and longest streak tracking
    4. Missed days reset streak rules
    5. Effective streak calculation (grace period until end of today)
    6. Weekly activity summary generation
    7. Duplicate submission prevention & idempotency
    8. Invalid/abandoned/anonymous submissions do not qualify
    9. Integration with Student Dashboard (KPI + weekly tracker)
    10. Timezone boundary consistency (Asia/Kathmandu UTC+5:45)
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="streak_student",
            email="streak_student@nptor.test",
            password="SecurePassword123!",
        )
        self.client = Client()
        self.client.force_login(self.user)

        self.domain = Domain.objects.create(name="Civil Engineering", is_active=True)
        self.category = Category.objects.create(name="Structural Analysis", domain=self.domain)

        self.question = Question.objects.create(
            text="What is the unit of bending moment?",
            question_type=Question.SINGLE,
            difficulty=Question.EASY,
            primary_category=self.category,
            is_active=True,
            is_deleted=False,
        )
        self.choice1 = Choice.objects.create(question=self.question, text="kNm", is_correct=True, order=1)
        self.choice2 = Choice.objects.create(question=self.question, text="kN/m", is_correct=False, order=2)

    def test_record_qualifying_practice_creates_streak_and_log(self):
        """Test that first qualifying practice creates a DailyPracticeLog and initializes UserPracticeStreak."""
        streak, log = record_qualifying_practice(
            user=self.user,
            question=self.question,
            is_correct=True,
            source="practice",
        )

        today = get_business_today()
        self.assertIsNotNone(streak)
        self.assertIsNotNone(log)
        self.assertEqual(streak.current_streak, 1)
        self.assertEqual(streak.longest_streak, 1)
        self.assertEqual(streak.last_activity_date, today)
        self.assertEqual(streak.total_active_days, 1)
        self.assertEqual(streak.total_questions_practiced, 1)
        self.assertEqual(streak.total_questions_correct, 1)

        self.assertEqual(log.activity_date, today)
        self.assertEqual(log.questions_practiced, 1)
        self.assertEqual(log.questions_correct, 1)

    def test_single_active_day_per_calendar_day_no_duplicate_streak(self):
        """Test that multiple answers on the same day do NOT increment streak count twice."""
        today = get_business_today()

        # Submit 5 questions on the same calendar day
        for i in range(5):
            streak, log = record_qualifying_practice(
                user=self.user,
                question=self.question,
                is_correct=(i % 2 == 0),
                source="practice",
            )

        # Streak must remain 1 (1 day of activity)
        self.assertEqual(streak.current_streak, 1)
        self.assertEqual(streak.longest_streak, 1)
        self.assertEqual(streak.total_active_days, 1)
        self.assertEqual(streak.total_questions_practiced, 5)
        self.assertEqual(streak.total_questions_correct, 3)

        # Exactly 1 log record exists for today
        logs = DailyPracticeLog.objects.filter(user=self.user, activity_date=today)
        self.assertEqual(logs.count(), 1)
        self.assertEqual(logs.first().questions_practiced, 5)

    def test_consecutive_days_streak_progression(self):
        """Test streak advances day by day when user practices on consecutive days."""
        today = get_business_today()

        # Simulate Day 1 (yesterday)
        streak_obj = UserPracticeStreak.objects.create(
            user=self.user,
            current_streak=1,
            longest_streak=1,
            last_activity_date=today - datetime.timedelta(days=1),
            total_active_days=1,
            total_questions_practiced=5,
            total_questions_correct=4,
        )
        DailyPracticeLog.objects.create(
            user=self.user,
            activity_date=today - datetime.timedelta(days=1),
            questions_practiced=5,
            questions_correct=4,
        )

        # Student practices today
        streak, log = record_qualifying_practice(
            user=self.user,
            question=self.question,
            is_correct=True,
            source="practice",
        )

        self.assertEqual(streak.current_streak, 2)
        self.assertEqual(streak.longest_streak, 2)
        self.assertEqual(streak.total_active_days, 2)
        self.assertEqual(streak.last_activity_date, today)

    def test_missed_day_resets_streak(self):
        """Test that missing a day resets current streak back to 1 while preserving longest streak."""
        today = get_business_today()

        # User had a 5-day streak that ended 2 days ago (missed yesterday)
        streak_obj = UserPracticeStreak.objects.create(
            user=self.user,
            current_streak=5,
            longest_streak=5,
            last_activity_date=today - datetime.timedelta(days=2),
            total_active_days=5,
            total_questions_practiced=50,
            total_questions_correct=40,
        )

        # User practices today
        streak, log = record_qualifying_practice(
            user=self.user,
            question=self.question,
            is_correct=True,
            source="practice",
        )

        # Current streak must reset to 1
        self.assertEqual(streak.current_streak, 1)
        # Longest streak remains 5
        self.assertEqual(streak.longest_streak, 5)
        self.assertEqual(streak.total_active_days, 6)
        self.assertEqual(streak.last_activity_date, today)

    def test_effective_current_streak_grace_period(self):
        """Test that if user practiced yesterday but has not yet practiced today, streak is still intact."""
        today = get_business_today()

        streak_obj = UserPracticeStreak.objects.create(
            user=self.user,
            current_streak=4,
            longest_streak=7,
            last_activity_date=today - datetime.timedelta(days=1),
            total_active_days=10,
        )

        summary = get_student_streak_summary(self.user, today=today)
        # Still 4 days because today isn't over yet
        self.assertEqual(summary["current_streak"], 4)
        self.assertEqual(summary["longest_streak"], 7)
        self.assertFalse(summary["is_active_today"])

        # If last activity was 2 days ago, effective streak is 0
        streak_obj.last_activity_date = today - datetime.timedelta(days=2)
        streak_obj.save()

        summary2 = get_student_streak_summary(self.user, today=today)
        self.assertEqual(summary2["current_streak"], 0)
        self.assertEqual(summary2["longest_streak"], 7)

    def test_weekly_summary_last_7_days(self):
        """Test that weekly summary contains exactly 7 days with active/inactive indicators."""
        today = get_business_today()

        # Create activity for 3 specific days within the past week
        DailyPracticeLog.objects.create(
            user=self.user,
            activity_date=today - datetime.timedelta(days=3),
            questions_practiced=10,
            questions_correct=8,
        )
        DailyPracticeLog.objects.create(
            user=self.user,
            activity_date=today - datetime.timedelta(days=1),
            questions_practiced=15,
            questions_correct=12,
        )
        DailyPracticeLog.objects.create(
            user=self.user,
            activity_date=today,
            questions_practiced=20,
            questions_correct=18,
        )

        UserPracticeStreak.objects.create(
            user=self.user,
            current_streak=2,
            longest_streak=2,
            last_activity_date=today,
            total_active_days=3,
            total_questions_practiced=45,
            total_questions_correct=38,
        )

        summary = get_student_streak_summary(self.user, today=today)
        weekly = summary["weekly_summary"]

        self.assertEqual(len(weekly), 7)
        # Check today is last item
        self.assertEqual(weekly[-1]["date"], today)
        self.assertTrue(weekly[-1]["is_today"])
        self.assertTrue(weekly[-1]["is_active"])
        self.assertEqual(weekly[-1]["questions_count"], 20)

        # Check yesterday is active
        self.assertTrue(weekly[-2]["is_active"])
        self.assertEqual(weekly[-2]["questions_count"], 15)

        # Check 2 days ago was inactive
        self.assertFalse(weekly[-3]["is_active"])
        self.assertEqual(weekly[-3]["questions_count"], 0)

        # Check 3 days ago was active
        self.assertTrue(weekly[-4]["is_active"])

    def test_anonymous_and_invalid_submissions_do_not_qualify(self):
        """Test that unauthenticated requests do not record practice activity."""
        from django.contrib.auth.models import AnonymousUser
        anon = AnonymousUser()

        streak, log = record_qualifying_practice(user=anon, question=self.question, is_correct=True)
        self.assertIsNone(streak)
        self.assertIsNone(log)
        self.assertEqual(DailyPracticeLog.objects.count(), 0)

    def test_practice_ajax_endpoint_updates_streak(self):
        """Test HTTP AJAX answer submission automatically triggers practice streak tracking."""
        today = get_business_today()

        response = self.client.post("/quiz/practice/answer/ajax/", {
            "question_id": str(self.question.id),
            "choice": str(self.choice1.id),
        })
        self.assertEqual(response.status_code, 200)

        # Verify UserPracticeStreak and DailyPracticeLog were created
        streak = UserPracticeStreak.objects.filter(user=self.user).first()
        self.assertIsNotNone(streak)
        self.assertEqual(streak.current_streak, 1)
        self.assertEqual(streak.last_activity_date, today)

        log = DailyPracticeLog.objects.filter(user=self.user, activity_date=today).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.questions_practiced, 1)

    def test_practice_express_save_updates_streak(self):
        """Test HTTP practice express save endpoint updates streak and returns effective streak."""
        today = get_business_today()

        response = self.client.post("/quiz/practice/express/save/", {
            "question_id": str(self.question.id),
            "is_correct": "true",
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["streak"], 1)

        streak = UserPracticeStreak.objects.filter(user=self.user).first()
        self.assertIsNotNone(streak)
        self.assertEqual(streak.current_streak, 1)
        self.assertEqual(streak.last_activity_date, today)

    def test_student_dashboard_overview_displays_streak_and_weekly_summary(self):
        """Test that the student dashboard renders the streak KPI and weekly habit tracker."""
        # Record activity
        record_qualifying_practice(user=self.user, question=self.question, is_correct=True)

        response = self.client.get("/quiz/dashboard/student/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "PRACTICE STREAK")
        self.assertContains(response, "1 Day")
        self.assertContains(response, "Weekly Practice Activity")
        self.assertContains(response, "Practiced Today")

    def test_timezone_boundary_kathmandu(self):
        """Test that dates are calculated consistently using Asia/Kathmandu (UTC+5:45)."""
        today_ktm = get_business_today()
        # Verify timezone calculation matches timezone.now().astimezone(KATHMANDU_TZ).date()
        expected = timezone.now().astimezone(KATHMANDU_TZ).date()
        self.assertEqual(today_ktm, expected)
