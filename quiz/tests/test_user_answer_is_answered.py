from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from quiz.models import Exam, Question, Choice, UserExam, UserAnswer, Category, Domain
from quiz.services.grading import grade_exam

User = get_user_model()


class UserAnswerIsAnsweredTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="test_is_answered_user", password="password123")
        self.domain = Domain.objects.create(name="Tech Domain", slug="tech-domain")
        self.category = Category.objects.create(name="Tech Category", slug="tech-category", domain=self.domain)
        self.exam = Exam.objects.create(
            title="IsAnswered Test Exam",
            duration_seconds=1800,
            question_count=7,
            passing_score=70,
            is_published=True,
            allow_review=True,
        )
        self.exam.categories.add(self.category)
        self.user_exam = UserExam.objects.create(
            user=self.user,
            exam=self.exam,
            status="in_progress",
            started_at=timezone.now(),
            question_order=[],
        )

    def test_single_choice_is_answered(self):
        q = Question.objects.create(primary_category=self.category, question_type="single", text="Single?")
        c = Choice.objects.create(question=q, text="Option 1", is_correct=True, order=1)
        ua = UserAnswer(user_exam=self.user_exam, question=q)
        self.assertFalse(ua.is_answered)

        ua.choice = c
        self.assertTrue(ua.is_answered)

    def test_true_false_and_dropdown_is_answered(self):
        q_tf = Question.objects.create(primary_category=self.category, question_type="tf", text="TF?")
        c_tf = Choice.objects.create(question=q_tf, text="True", is_correct=True, order=1)
        ua_tf = UserAnswer(user_exam=self.user_exam, question=q_tf)
        self.assertFalse(ua_tf.is_answered)
        ua_tf.choice = c_tf
        self.assertTrue(ua_tf.is_answered)

        q_drop = Question.objects.create(primary_category=self.category, question_type="dropdown", text="Drop?")
        c_drop = Choice.objects.create(question=q_drop, text="Choice", is_correct=True, order=1)
        ua_drop = UserAnswer(user_exam=self.user_exam, question=q_drop)
        self.assertFalse(ua_drop.is_answered)
        ua_drop.choice = c_drop
        self.assertTrue(ua_drop.is_answered)

    def test_multiple_choice_is_answered(self):
        q = Question.objects.create(primary_category=self.category, question_type="multi", text="Multi?")
        ua = UserAnswer(user_exam=self.user_exam, question=q, selections=[])
        self.assertFalse(ua.is_answered)

        ua.selections = [10, 20]
        self.assertTrue(ua.is_answered)

    def test_matching_is_answered(self):
        q = Question.objects.create(primary_category=self.category, question_type="match", text="Match?")
        ua = UserAnswer(user_exam=self.user_exam, question=q, selections={})
        self.assertFalse(ua.is_answered)

        ua.selections = {"left_1": "right_2"}
        self.assertTrue(ua.is_answered)

    def test_ordering_is_answered(self):
        q = Question.objects.create(primary_category=self.category, question_type="order", text="Order?")
        ua = UserAnswer(user_exam=self.user_exam, question=q, selections=[])
        self.assertFalse(ua.is_answered)

        ua.selections = [3, 1, 2]
        self.assertTrue(ua.is_answered)

    def test_fill_in_the_blank_and_numeric_is_answered(self):
        q_fill = Question.objects.create(primary_category=self.category, question_type="fill", text="Fill?")
        ua_fill = UserAnswer(user_exam=self.user_exam, question=q_fill, raw_answer="")
        self.assertFalse(ua_fill.is_answered)
        ua_fill.raw_answer = "   "
        self.assertFalse(ua_fill.is_answered)
        ua_fill.raw_answer = "Django"
        self.assertTrue(ua_fill.is_answered)

        q_num = Question.objects.create(primary_category=self.category, question_type="numeric", text="Num?")
        ua_num = UserAnswer(user_exam=self.user_exam, question=q_num, raw_answer="")
        self.assertFalse(ua_num.is_answered)
        ua_num.raw_answer = "42.5"
        self.assertTrue(ua_num.is_answered)

    def test_is_answered_property_does_not_affect_grading(self):
        q = Question.objects.create(primary_category=self.category, question_type="single", text="Grading test?")
        c1 = Choice.objects.create(question=q, text="Correct", is_correct=True, order=1)
        Choice.objects.create(question=q, text="Incorrect", is_correct=False, order=2)

        self.user_exam.question_order = [q.id]
        self.user_exam.save()

        ua = UserAnswer.objects.create(user_exam=self.user_exam, question=q, choice=c1)
        self.assertTrue(ua.is_answered)

        # Call grading service
        result = grade_exam(self.user_exam, None)
        self.assertTrue(self.user_exam.submitted_at is not None)
        self.assertEqual(self.user_exam.score, 100.0)
        self.assertTrue(self.user_exam.passed)
        ua.refresh_from_db()
        self.assertTrue(ua.is_correct)
        self.assertTrue(ua.is_answered)

    def test_exam_review_template_renders_card_status_correctly(self):
        q1 = Question.objects.create(primary_category=self.category, question_type="single", text="Review Q1?")
        c1 = Choice.objects.create(question=q1, text="Ans 1", is_correct=True, order=1)
        q2 = Question.objects.create(primary_category=self.category, question_type="single", text="Review Q2?")
        Choice.objects.create(question=q2, text="Ans 2", is_correct=True, order=1)

        self.user_exam.question_order = [q1.id, q2.id]
        self.user_exam.save()

        # Answer only Q1
        UserAnswer.objects.create(user_exam=self.user_exam, question=q1, choice=c1)

        client = Client()
        client.force_login(self.user)
        response = client.get(reverse("quiz:exam_review", kwargs={"user_exam_id": self.user_exam.id}))
        self.assertEqual(response.status_code, 200)

        # Q1 should be answered
        self.assertContains(response, 'data-card-status="answered"')
        # Q2 should be unanswered
        self.assertContains(response, 'data-card-status="unanswered"')
        self.assertContains(response, "is-unanswered")

        # Check summary chips
        self.assertContains(response, "Total:</strong> 2")
        self.assertContains(response, "Answered:</strong> 1")
        self.assertContains(response, "Unanswered:</strong> 1")

        # Check filter buttons
        self.assertContains(response, 'data-filter="all"')
        self.assertContains(response, 'data-filter="answered"')
        self.assertContains(response, 'data-filter="unanswered"')
