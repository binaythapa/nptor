import datetime
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from quiz.models import (
    StudyPlan,
    Question,
    Choice,
    Category,
    Domain,
    Exam,
)
from quiz.services.study_plan_service import (
    generate_study_plan,
    get_today_questions,
    get_today_topics,
    get_today_recommended_courses,
    handle_missed_day,
)

User = get_user_model()


class StudyPlanPhase2Tests(TestCase):
    """
    Comprehensive verification suite for Phase 2.1 Study Plan improvements:
    1. 15-Day Study Plan creation and configuration
    2. Target exam and domain objective selection
    3. Dynamic scaling for small question pools
    4. Daily tasks, topic extraction and daily schedule generation
    5. Missed days calculation and auto-extension
    6. Extension day question serving
    7. Dashboard and Create Plan views
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="student_tester",
            email="student@nptor.test",
            password="SecurePassword123!",
        )
        self.client = Client()
        self.client.force_login(self.user)

        # Create Domain & Categories
        self.domain = Domain.objects.create(name="Public Administration", is_active=True)
        self.cat1 = Category.objects.create(name="Governance", domain=self.domain)
        self.cat2 = Category.objects.create(name="Constitution", domain=self.domain)

        # Create Target Exam
        self.exam = Exam.objects.create(
            title="Section Officer Examination",
            duration_seconds=3600,
            question_count=50,
            passing_score=50.0,
            is_published=True,
        )
        self.exam.categories.add(self.cat1, self.cat2)

        # Create 60 Questions (30 in cat1, 30 in cat2)
        self.questions = []
        for i in range(60):
            cat = self.cat1 if i % 2 == 0 else self.cat2
            q = Question.objects.create(
                text=f"Sample Question {i + 1}",
                question_type=Question.SINGLE,
                difficulty=Question.MEDIUM,
                primary_category=cat,
                is_active=True,
                is_deleted=False,
            )
            Choice.objects.create(question=q, text="Option A", is_correct=True, order=1)
            Choice.objects.create(question=q, text="Option B", is_correct=False, order=2)
            self.questions.append(q)

    def test_15_day_study_plan_generation_defaults(self):
        """Test creating a default 15-day balanced study plan."""
        plan = generate_study_plan(user=self.user, plan_type=15)

        self.assertEqual(plan.plan_type, 15)
        self.assertEqual(plan.total_days, 15)
        self.assertTrue(plan.is_active)
        self.assertFalse(plan.is_completed)
        self.assertEqual(plan.extension_days, 0)
        # Because we only have 60 questions, per_day is scaled: 60 // 15 = 4
        self.assertEqual(plan.questions_per_day, 4)
        self.assertEqual(len(plan.question_ids), 60)
        self.assertEqual(plan.get_day_index(), 0)

    def test_study_plan_with_target_exam_focus(self):
        """Test study plan created specifically for a target exam."""
        # Create an unrelated category and questions
        other_domain = Domain.objects.create(name="Foreign Service", is_active=True)
        other_cat = Category.objects.create(name="Diplomacy", domain=other_domain)
        for i in range(10):
            Question.objects.create(
                text=f"Diplomacy Q {i}",
                question_type=Question.SINGLE,
                primary_category=other_cat,
                is_active=True,
                is_deleted=False,
            )

        plan = generate_study_plan(user=self.user, plan_type=15, exam=self.exam)

        self.assertEqual(plan.exam, self.exam)
        # Check all questions in the plan belong to the exam's categories
        plan_questions = Question.objects.filter(id__in=plan.question_ids)
        for q in plan_questions:
            self.assertIn(q.primary_category_id, [self.cat1.id, self.cat2.id])
            self.assertNotEqual(q.primary_category_id, other_cat.id)

    def test_study_plan_with_domain_objective(self):
        """Test study plan created with a domain objective focus."""
        plan = generate_study_plan(user=self.user, plan_type=15, domain=self.domain)
        self.assertEqual(plan.domain, self.domain)
        self.assertEqual(len(plan.question_ids), 60)

    def test_dynamic_scaling_small_pool(self):
        """Test that study plan scales questions-per-day rather than raising ValueError."""
        # Create a category with only 15 questions
        small_cat = Category.objects.create(name="Niche Topic", domain=self.domain)
        small_q_ids = []
        for i in range(15):
            q = Question.objects.create(
                text=f"Niche Q {i}",
                question_type=Question.SINGLE,
                primary_category=small_cat,
                is_active=True,
                is_deleted=False,
            )
            small_q_ids.append(q.id)

        small_exam = Exam.objects.create(
            title="Niche Exam",
            duration_seconds=1800,
            question_count=15,
            is_published=True,
        )
        small_exam.categories.add(small_cat)

        plan = generate_study_plan(user=self.user, plan_type=15, exam=small_exam)
        self.assertEqual(plan.total_days, 15)
        self.assertEqual(plan.questions_per_day, 1)
        self.assertEqual(len(plan.question_ids), 15)

    def test_dynamic_scaling_very_small_pool_cycles(self):
        """Test that if questions < total_days, questions cycle evenly across the 15 days."""
        micro_cat = Category.objects.create(name="Micro Topic", domain=self.domain)
        for i in range(5):
            Question.objects.create(
                text=f"Micro Q {i}",
                question_type=Question.SINGLE,
                primary_category=micro_cat,
                is_active=True,
                is_deleted=False,
            )

        micro_exam = Exam.objects.create(
            title="Micro Exam",
            duration_seconds=900,
            question_count=5,
            is_published=True,
        )
        micro_exam.categories.add(micro_cat)

        plan = generate_study_plan(user=self.user, plan_type=15, exam=micro_exam)
        self.assertEqual(plan.total_days, 15)
        self.assertEqual(plan.questions_per_day, 1)
        self.assertEqual(len(plan.question_ids), 15)

    def test_empty_pool_raises_value_error(self):
        """Test that an empty pool raises a clean ValueError."""
        empty_cat = Category.objects.create(name="Empty Topic", domain=self.domain)
        empty_exam = Exam.objects.create(
            title="Empty Exam",
            duration_seconds=900,
            question_count=0,
            is_published=True,
        )
        empty_exam.categories.add(empty_cat)

        with self.assertRaises(ValueError) as ctx:
            generate_study_plan(user=self.user, plan_type=15, exam=empty_exam)
        self.assertIn("No questions available", str(ctx.exception))

    def test_daily_progress_tracking_and_schedule(self):
        """Test daily progress, schedule generation, and completion."""
        plan = generate_study_plan(user=self.user, plan_type=15)

        # Day 0: 0 completed initially
        self.assertEqual(plan.get_today_completed_count(), 0)
        self.assertEqual(len(plan.get_today_question_ids()), plan.questions_per_day)

        # Increment progress
        plan.increment_today_progress()
        self.assertEqual(plan.get_today_completed_count(), 1)

        # Check daily schedule structure
        schedule = plan.get_daily_schedule()
        self.assertEqual(len(schedule), 15)

        day_0 = schedule[0]
        self.assertEqual(day_0["day_number"], 1)
        self.assertTrue(day_0["is_today"])
        self.assertEqual(day_0["completed"], 1)
        self.assertEqual(day_0["target"], plan.questions_per_day)

    def test_missed_days_calculation(self):
        """Test get_missed_days_count when days elapse without completing targets."""
        plan = generate_study_plan(user=self.user, plan_type=15)

        # Simulate start_date was 3 days ago
        plan.start_date = timezone.now().date() - datetime.timedelta(days=3)
        plan.daily_progress = {"0": plan.questions_per_day, "1": 1, "2": 0}
        plan.save()

        # Day 0 was completed, Day 1 was partial (missed), Day 2 was 0 (missed)
        self.assertEqual(plan.get_missed_days_count(), 2)
        self.assertEqual(plan.get_completed_days_count(), 1)

    def test_auto_extension_and_extension_day_questions(self):
        """Test auto-extension up to MAX_EXTENSION_DAYS and question serving on extension days."""
        plan = generate_study_plan(user=self.user, plan_type=15)

        # Simulate 16 days have elapsed (past 15-day planned duration)
        plan.start_date = timezone.now().date() - datetime.timedelta(days=16)
        plan.save()

        # Auto extend
        plan.auto_extend_if_needed()
        self.assertGreater(plan.extension_days, 0)
        self.assertLessEqual(plan.extension_days, StudyPlan.MAX_EXTENSION_DAYS)
        self.assertEqual(plan.total_plan_days(), 15 + plan.extension_days)

        # Verify extension day serves questions without returning empty list
        ext_questions = plan.get_today_question_ids()
        self.assertGreater(len(ext_questions), 0)

    def test_topics_and_courses_integration(self):
        """Test topic extraction and recommended course lookups."""
        plan = generate_study_plan(user=self.user, plan_type=15, domain=self.domain)
        topics = get_today_topics(plan)
        self.assertTrue(len(topics) > 0)
        self.assertTrue(any(t in ["Governance", "Constitution"] for t in topics))

    def test_views_create_and_dashboard(self):
        """Test HTTP views: create_study_plan and study_plan_dashboard."""
        # 1. GET create_study_plan
        response = self.client.get("/quiz/study-plan/create/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create Personalized Study Plan")
        self.assertContains(response, "15-Day Balanced Plan")
        self.assertContains(response, "Section Officer Examination")

        # 2. POST create_study_plan
        post_data = {
            "plan_type": "15",
            "exam": str(self.exam.id),
            "domain": str(self.domain.id),
        }
        post_response = self.client.post("/quiz/study-plan/create/", post_data, follow=True)
        self.assertEqual(post_response.status_code, 200)
        self.assertContains(post_response, "Active Plan")
        self.assertContains(post_response, "15-Day Balanced Plan")
        self.assertContains(post_response, "Study Plan Timeline")

        # 3. GET study_plan_dashboard
        dash_response = self.client.get("/quiz/study-plan/")
        self.assertEqual(dash_response.status_code, 200)
        self.assertContains(dash_response, "Mission")
        self.assertContains(dash_response, "Day 1 of 15")
