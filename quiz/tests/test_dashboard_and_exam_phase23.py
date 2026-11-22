import json
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from courses.models import Course, CourseEnrollment
from courses.models.subscription import CourseSubscription
from quiz.models import (
    Category,
    Choice,
    Domain,
    Exam,
    Question,
    StudyPlan,
    UserAnswer,
    UserExam,
)
from quiz.models.practice import UserPracticeStreak, DailyPracticeLog

User = get_user_model()


class DashboardAndExamPhase23Tests(TestCase):
    """
    Empirical test suite for Phase 2.3:
    - Examination experience improvements (instructions, timer, palette, mark-for-review, autosave, expiry)
    - Diagnostic topic-wise performance breakdown and recommended practice/courses
    - Centralized student dashboard (study plan, streak, enrolled courses, pending tasks, subscriptions)
    - Security and user isolation
    """

    def setUp(self):
        self.client = Client()
        self.password = "Secr3tP@ssw0rd!"

        self.user = User.objects.create_user(
            username="student_p23",
            email="student_p23@nptor.test",
            password=self.password,
            first_name="Rohan",
            last_name="Shrestha",
        )
        self.other_user = User.objects.create_user(
            username="other_student",
            email="other@nptor.test",
            password=self.password,
            first_name="Bikash",
        )

        self.domain = Domain.objects.create(name="Engineering", slug="engineering")
        self.cat_math = Category.objects.create(name="Mathematics", domain=self.domain, slug="math")
        self.cat_physics = Category.objects.create(name="Physics", domain=self.domain, slug="physics")

        self.exam = Exam.objects.create(
            title="Loksewa Civil Engineering Fundamentals",
            duration_seconds=1800,  # 30 minutes
            passing_score=60.0,
            question_count=4,
            is_published=True,
            is_free=True,
            level=2,
        )
        self.exam.categories.add(self.cat_math, self.cat_physics)

        # Create 4 questions: 2 in Mathematics, 2 in Physics
        self.q1 = Question.objects.create(
            text="What is the derivative of x^2?",
            question_type="single",
            primary_category=self.cat_math,
            is_active=True,
        )
        self.c1_correct = Choice.objects.create(question=self.q1, text="2x", is_correct=True)
        self.c1_wrong = Choice.objects.create(question=self.q1, text="x", is_correct=False)

        self.q2 = Question.objects.create(
            text="Integral of 1/x dx is?",
            question_type="single",
            primary_category=self.cat_math,
            is_active=True,
        )
        self.c2_correct = Choice.objects.create(question=self.q2, text="ln|x| + C", is_correct=True)
        self.c2_wrong = Choice.objects.create(question=self.q2, text="e^x", is_correct=False)

        self.q3 = Question.objects.create(
            text="Newton's second law is?",
            question_type="single",
            primary_category=self.cat_physics,
            is_active=True,
        )
        self.c3_correct = Choice.objects.create(question=self.q3, text="F = ma", is_correct=True)
        self.c3_wrong = Choice.objects.create(question=self.q3, text="E = mc^2", is_correct=False)

        self.q4 = Question.objects.create(
            text="Unit of electrical resistance?",
            question_type="single",
            primary_category=self.cat_physics,
            is_active=True,
        )
        self.c4_correct = Choice.objects.create(question=self.q4, text="Ohm", is_correct=True)
        self.c4_wrong = Choice.objects.create(question=self.q4, text="Watt", is_correct=False)

        # Create published course for recommendation testing
        self.course_physics = Course.objects.create(
            title="Complete Engineering Physics Bootcamp",
            slug="engineering-physics-bootcamp",
            category=self.domain,
            is_published=True,
            description="Master core physics concepts for engineering exams.",
        )

        # Setup an active exam attempt for self.user
        self.user_exam = UserExam.objects.create(
            user=self.user,
            exam=self.exam,
            question_order=[self.q1.id, self.q2.id, self.q3.id, self.q4.id],
            current_index=0,
        )
        self.ua1 = UserAnswer.objects.create(user_exam=self.user_exam, question=self.q1)
        self.ua2 = UserAnswer.objects.create(user_exam=self.user_exam, question=self.q2)
        self.ua3 = UserAnswer.objects.create(user_exam=self.user_exam, question=self.q3)
        self.ua4 = UserAnswer.objects.create(user_exam=self.user_exam, question=self.q4)

    # =========================================================
    # PART B: EXAMINATION EXPERIENCE TESTS
    # =========================================================

    def test_exam_detail_clear_instructions(self):
        """Verify exam detail template contract includes clear rules, instructions, timer, and scoring requirements."""
        from pathlib import Path
        template_path = Path(__file__).resolve().parent.parent.parent / "templates/quiz/student/exam/exam_detail.html"
        html = template_path.read_text(encoding="utf-8")
        self.assertIn("Exam instructions &amp; rules", html)
        self.assertIn("Passing score", html)
        self.assertIn("Timed attempt", html)
        self.assertIn("Question Navigation", html)
        self.assertIn("Mark for Review", html)
        self.assertIn("Automatic Saving", html)
        self.assertIn("Submission Confirmation", html)

    def test_exam_question_view_and_palette_rendering(self):
        """Verify exam question renders timer, question, palette, and navigation."""
        self.client.login(username="student_p23", password=self.password)
        response = self.client.get(reverse("quiz:exam_question", args=[self.user_exam.id, 0]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Time Remaining")
        self.assertContains(response, "Question Navigator")
        self.assertContains(response, "Mark for Review")
        self.assertContains(response, "What is the derivative of x^2?")
        self.assertIn("palette", response.context)
        self.assertEqual(len(response.context["palette"]), 4)
        self.assertEqual(response.context["palette"][0]["is_current"], True)

    def test_question_navigation_next_prev_and_goto(self):
        """Verify next, previous, and jump-to-question navigation persist user position."""
        self.client.login(username="student_p23", password=self.password)

        # Answer Q1 and click next
        post_data = {
            f"question_{self.q1.id}": self.c1_correct.id,
            "nav": "next",
        }
        res_next = self.client.post(reverse("quiz:exam_question", args=[self.user_exam.id, 0]), post_data)
        self.assertRedirects(res_next, reverse("quiz:exam_question", args=[self.user_exam.id, 1]))

        # Verify Q1 answer was persisted
        self.ua1.refresh_from_db()
        self.assertEqual(self.ua1.choice_id, self.c1_correct.id)

        # Jump directly to Q3 (index 2) via palette goto
        post_goto = {
            f"question_{self.q2.id}": self.c2_correct.id,
            "nav": "goto:2",
        }
        res_goto = self.client.post(reverse("quiz:exam_question", args=[self.user_exam.id, 1]), post_goto)
        self.assertRedirects(res_goto, reverse("quiz:exam_question", args=[self.user_exam.id, 2]))

        # Navigate previous from Q3 (index 2)
        res_prev = self.client.post(reverse("quiz:exam_question", args=[self.user_exam.id, 2]), {"nav": "prev"})
        self.assertRedirects(res_prev, reverse("quiz:exam_question", args=[self.user_exam.id, 1]))

    def test_mark_for_review_post_and_persistence(self):
        """Verify mark for review can be toggled via POST and persists across refreshes and palette."""
        self.client.login(username="student_p23", password=self.password)

        # Flag question 1 via POST
        post_flag = {
            f"question_{self.q1.id}": self.c1_correct.id,
            "is_marked_for_review": "1",
            "nav": "next",
        }
        self.client.post(reverse("quiz:exam_question", args=[self.user_exam.id, 0]), post_flag)

        self.ua1.refresh_from_db()
        self.assertTrue(self.ua1.is_marked_for_review)

        # Return to Q1 and verify view reflects flagged state
        res = self.client.get(reverse("quiz:exam_question", args=[self.user_exam.id, 0]))
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.context["is_marked_for_review"])
        self.assertEqual(res.context["marked_count"], 1)

        # Verify palette tile for Q1 is flagged
        tile_q1 = next(item for item in res.context["palette"] if item["question_id"] == self.q1.id)
        self.assertTrue(tile_q1["is_marked_for_review"])

    def test_autosave_ajax_answer_and_flag_toggle(self):
        """Verify AJAX autosave updates both question choice and mark_for_review state."""
        self.client.login(username="student_p23", password=self.password)

        # Autosave answer for Q2
        res = self.client.post(
            reverse("quiz:exam_autosave", args=[self.user_exam.id]),
            {f"question_{self.q2.id}": str(self.c2_correct.id)},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("status"), "ok")

        self.ua2.refresh_from_db()
        self.assertEqual(self.ua2.choice_id, self.c2_correct.id)

        # Autosave flag toggle for Q2
        res_flag = self.client.post(
            reverse("quiz:exam_autosave", args=[self.user_exam.id]),
            {"question_id": str(self.q2.id), "is_marked_for_review": "1"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(res_flag.status_code, 200)
        self.ua2.refresh_from_db()
        self.assertTrue(self.ua2.is_marked_for_review)

    def test_server_side_expiry_enforcement(self):
        """Verify exam with elapsed duration auto-grades immediately upon request."""
        self.client.login(username="student_p23", password=self.password)

        # Set started_at back by 35 minutes (duration is 30 mins)
        self.user_exam.started_at = timezone.now() - timedelta(minutes=35)
        self.user_exam.save()

        self.assertLessEqual(self.user_exam.time_remaining(), 0)

        # Requesting exam_question must auto-grade and redirect to exam_result
        res = self.client.get(reverse("quiz:exam_question", args=[self.user_exam.id, 0]))
        self.assertRedirects(res, reverse("quiz:exam_result", args=[self.user_exam.id]))

        self.user_exam.refresh_from_db()
        self.assertIsNotNone(self.user_exam.submitted_at)

    def test_exam_result_topic_wise_breakdown_and_recommendations(self):
        """Verify detailed results breakdown: 100% Math, 0% Physics, and Physics course recommendation."""
        self.client.login(username="student_p23", password=self.password)

        # Answer Math questions correctly
        self.ua1.choice = self.c1_correct
        self.ua1.is_correct = True
        self.ua1.save()

        self.ua2.choice = self.c2_correct
        self.ua2.is_correct = True
        self.ua2.save()

        # Answer Physics questions incorrectly
        self.ua3.choice = self.c3_wrong
        self.ua3.is_correct = False
        self.ua3.save()

        self.ua4.choice = self.c4_wrong
        self.ua4.is_correct = False
        self.ua4.save()

        # Submit exam
        res_submit = self.client.post(reverse("quiz:exam_submit", args=[self.user_exam.id]))
        self.assertRedirects(res_submit, reverse("quiz:exam_result", args=[self.user_exam.id]))

        # View result page
        res_result = self.client.get(reverse("quiz:exam_result", args=[self.user_exam.id]))
        self.assertEqual(res_result.status_code, 200)

        # Verify summary stats
        self.assertEqual(res_result.context["correct_count"], 2)
        self.assertEqual(res_result.context["incorrect_count"], 2)
        self.assertEqual(res_result.context["total_count"], 4)
        self.assertEqual(res_result.context["accuracy_rate"], 50.0)

        # Verify topic breakdown in context
        topic_breakdown = res_result.context["topic_breakdown"]
        self.assertEqual(len(topic_breakdown), 2)

        math_topic = next(t for t in topic_breakdown if t["name"] == "Mathematics")
        physics_topic = next(t for t in topic_breakdown if t["name"] == "Physics")

        self.assertEqual(math_topic["score"], 100.0)
        self.assertEqual(math_topic["status_label"], "Proficient")

        self.assertEqual(physics_topic["score"], 0.0)
        self.assertEqual(physics_topic["status_label"], "Needs Practice")

        # Verify recommended courses contains Physics bootcamp
        recommended = res_result.context["recommended_courses"]
        self.assertTrue(any(c.slug == "engineering-physics-bootcamp" for c in recommended))

    # =========================================================
    # PART A: STUDENT DASHBOARD CENTRALIZATION TESTS
    # =========================================================

    def test_student_dashboard_centralized_aggregation(self):
        """Verify student dashboard aggregates active study plan, streak, enrolled courses, and pending tasks."""
        self.client.login(username="student_p23", password=self.password)

        # 1. Create an active study plan for user
        plan = StudyPlan.objects.create(
            user=self.user,
            exam=self.exam,
            plan_type=StudyPlan.PLAN_15,
            total_days=15,
            questions_per_day=10,
            question_ids=list(range(1, 151)),
            daily_progress={"0": 4},  # 4 of 10 done today
            start_date=timezone.now().date(),
            is_active=True,
        )

        # 2. Create streak record
        UserPracticeStreak.objects.create(
            user=self.user,
            current_streak=5,
            longest_streak=12,
            last_activity_date=timezone.now().date(),
        )

        # 3. Create course enrollment
        CourseEnrollment.objects.create(
            user=self.user,
            course=self.course_physics,
            is_active=True,
        )

        # 4. Request centralized dashboard
        response = self.client.get(reverse("quiz:student_dashboard"))
        self.assertEqual(response.status_code, 200)

        # Verify Active Study Plan in context & HTML
        study_plan_data = response.context["study_plan_data"]
        self.assertIsNotNone(study_plan_data)
        self.assertEqual(study_plan_data["day_number"], 1)
        self.assertEqual(study_plan_data["today_completed"], 4)
        self.assertEqual(study_plan_data["today_target"], 10)
        self.assertEqual(study_plan_data["today_percent"], 40)
        self.assertFalse(study_plan_data["is_today_completed"])
        self.assertContains(response, "Active Study Plan")
        self.assertContains(response, self.exam.title)

        # Verify Streak Summary in context & HTML
        streak = response.context["streak_summary"]
        self.assertEqual(streak["current_streak"], 5)
        self.assertEqual(streak["longest_streak"], 12)
        self.assertContains(response, "5 Days")

        # Verify Enrolled Courses in context & HTML
        enrolled_courses = response.context["enrolled_courses"]
        self.assertEqual(len(enrolled_courses), 1)
        self.assertEqual(enrolled_courses[0].slug, "engineering-physics-bootcamp")
        self.assertContains(response, "Complete Engineering Physics Bootcamp")

        # Verify Pending Tasks in context
        pending = response.context["pending_tasks"]
        self.assertTrue(any("Resume Exam" in t["title"] for t in pending))
        self.assertTrue(any("Study Plan Mission" in t["title"] for t in pending))

    # =========================================================
    # USER ISOLATION TESTS
    # =========================================================

    def test_user_cannot_access_other_users_exam_attempt(self):
        """Verify Student B is strictly forbidden from accessing or submitting Student A's exam attempt."""
        self.client.login(username="other_student", password=self.password)

        # Student B attempts to access Student A's exam question
        res_q = self.client.get(reverse("quiz:exam_question", args=[self.user_exam.id, 0]))
        self.assertEqual(res_q.status_code, 404)

        # Student B attempts to autosave to Student A's exam attempt
        res_auto = self.client.post(
            reverse("quiz:exam_autosave", args=[self.user_exam.id]),
            {f"question_{self.q1.id}": str(self.c1_correct.id)},
        )
        self.assertEqual(res_auto.status_code, 404)

        # Student B attempts to submit Student A's exam
        res_sub = self.client.post(reverse("quiz:exam_submit", args=[self.user_exam.id]))
        self.assertEqual(res_sub.status_code, 404)
