from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from quiz.models import Choice, Exam, Question, UserAnswer, UserExam
from quiz.services.answer_persistence import autosave_answers
from quiz.services.grading import grade_exam
from organizations.models.account_request import OrganizationAccountRequest

User = get_user_model()


class BackendIntegrityAndPerformanceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="backend_audit_student",
            password="test-password-123",
            email="backend_student@example.com",
        )
        self.exam = Exam.objects.create(
            title="Backend Performance Exam",
            question_count=3,
            duration_seconds=300,
            passing_score=50,
            is_free=True,
            is_published=True,
        )
        # Single choice question
        self.q_single = Question.objects.create(
            text="Single Choice Question",
            question_type=Question.SINGLE,
            difficulty=Question.EASY,
        )
        self.ch_single_correct = Choice.objects.create(
            question=self.q_single,
            text="Single Correct",
            is_correct=True,
        )
        self.ch_single_wrong = Choice.objects.create(
            question=self.q_single,
            text="Single Wrong",
            is_correct=False,
        )

        # Multi choice question
        self.q_multi = Question.objects.create(
            text="Multi Choice Question",
            question_type=Question.MULTI,
            difficulty=Question.MEDIUM,
        )
        self.ch_multi_c1 = Choice.objects.create(
            question=self.q_multi,
            text="Multi Correct 1",
            is_correct=True,
        )
        self.ch_multi_c2 = Choice.objects.create(
            question=self.q_multi,
            text="Multi Correct 2",
            is_correct=True,
        )
        self.ch_multi_w = Choice.objects.create(
            question=self.q_multi,
            text="Multi Wrong",
            is_correct=False,
        )

        # Order question
        self.q_order = Question.objects.create(
            text="Order Question",
            question_type=Question.ORDERING,
            difficulty=Question.MEDIUM,
        )
        self.ch_order_1 = Choice.objects.create(
            question=self.q_order,
            text="Step 1",
            order=1,
            is_correct=True,
        )
        self.ch_order_2 = Choice.objects.create(
            question=self.q_order,
            text="Step 2",
            order=2,
            is_correct=True,
        )

        self.user_exam = UserExam.objects.create(
            user=self.user,
            exam=self.exam,
            question_order=[self.q_single.id, self.q_multi.id, self.q_order.id],
            current_index=0,
        )

    def test_grade_exam_is_atomic_and_idempotent(self):
        """Calling grade_exam repeatedly returns the locked score without regrading."""
        # Setup initial answers
        ua1 = UserAnswer.objects.create(
            user_exam=self.user_exam,
            question=self.q_single,
            choice=self.ch_single_correct,
            is_correct=True,
        )
        ua2 = UserAnswer.objects.create(
            user_exam=self.user_exam,
            question=self.q_multi,
            selections=[self.ch_multi_c1.id, self.ch_multi_c2.id],
        )
        ua3 = UserAnswer.objects.create(
            user_exam=self.user_exam,
            question=self.q_order,
            selections=[self.ch_order_1.id, self.ch_order_2.id],
        )

        score, passed = grade_exam(self.user_exam, None)
        self.assertAlmostEqual(score, 100.0, places=1)
        self.assertTrue(passed)

        first_submitted_at = self.user_exam.submitted_at
        self.assertIsNotNone(first_submitted_at)

        # Second submission attempt with bogus post_data must not alter score or submitted_at
        fake_post = {f"question_{self.q_single.id}": str(self.ch_single_wrong.id)}
        second_score, second_passed = grade_exam(self.user_exam, fake_post)

        self.assertEqual(second_score, score)
        self.assertEqual(second_passed, passed)
        self.user_exam.refresh_from_db()
        self.assertEqual(self.user_exam.submitted_at, first_submitted_at)
        ua1.refresh_from_db()
        self.assertEqual(ua1.choice, self.ch_single_correct)

    def test_autosave_answers_rejected_after_exam_submitted(self):
        """Late in-flight autosave requests cannot alter submitted answers."""
        ua1 = UserAnswer.objects.create(
            user_exam=self.user_exam,
            question=self.q_single,
            choice=self.ch_single_correct,
        )
        # Finalize exam
        self.user_exam.submit(score=100.0)

        # In-flight autosave attempts to change answer to wrong choice
        class FakePost(dict):
            def getlist(self, key):
                return self.get(key, [])

        late_post = FakePost({f"question_{self.q_single.id}": [str(self.ch_single_wrong.id)]})
        autosave_answers(self.user_exam, late_post)

        ua1.refresh_from_db()
        self.assertEqual(ua1.choice, self.ch_single_correct)

    def test_exam_result_uses_prefetched_choices_without_n_plus_one_queries(self):
        """exam_result view efficiently uses prefetched choices without per-question queries."""
        UserAnswer.objects.create(
            user_exam=self.user_exam,
            question=self.q_single,
            choice=self.ch_single_correct,
        )
        UserAnswer.objects.create(
            user_exam=self.user_exam,
            question=self.q_multi,
            selections=[self.ch_multi_c1.id, self.ch_multi_c2.id],
        )
        UserAnswer.objects.create(
            user_exam=self.user_exam,
            question=self.q_order,
            selections=[self.ch_order_1.id, self.ch_order_2.id],
        )
        grade_exam(self.user_exam, None)

        self.client.force_login(self.user)
        result_url = reverse("quiz:exam_result", args=[self.user_exam.id])

        # Assert bounded query count on result page
        with self.assertNumQueries(14):
            response = self.client.get(result_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Single Correct")
        self.assertContains(response, "Multi Correct 1")
        self.assertContains(response, "Step 1")

    def test_organization_account_request_indexes_match_migrations(self):
        """OrganizationAccountRequest model index names match migration 0003."""
        index_names = {idx.name for idx in OrganizationAccountRequest._meta.indexes}
        self.assertIn("org_accreq_status_created_idx", index_names)
        self.assertIn("org_accreq_user_status_idx", index_names)

    def test_student_dashboard_kpis_aggregate_correctly(self):
        """Student dashboard calculates total, passed, and average score accurately."""
        # Create completed attempts
        ue1 = UserExam.objects.create(
            user=self.user,
            exam=self.exam,
            score=80.0,
            passed=True,
            submitted_at=timezone.now(),
            status=UserExam.STATUS_SUBMITTED,
        )
        ue2 = UserExam.objects.create(
            user=self.user,
            exam=self.exam,
            score=40.0,
            passed=False,
            submitted_at=timezone.now(),
            status=UserExam.STATUS_SUBMITTED,
        )

        self.client.force_login(self.user)
        response = self.client.get(reverse("quiz:student_dashboard"))
        self.assertEqual(response.status_code, 200)

        # In context:
        self.assertEqual(response.context["total_attempts"], 2)
        self.assertEqual(response.context["passed_attempts"], 1)
        self.assertEqual(response.context["average_score"], 60.0)

    def test_matching_and_ordering_scoring_edge_cases(self):
        """Test matching and ordering question grading including POST submission and edge cases."""
        # Matching question
        q_match = Question.objects.create(
            text="Match capital cities",
            question_type=Question.MATCHING,
            difficulty=Question.EASY,
            matching_pairs={"France": "Paris", "Japan": "Tokyo"},
        )
        exam_match = Exam.objects.create(
            title="Match Exam",
            question_count=1,
            duration_seconds=300,
            passing_score=50,
            is_free=True,
            is_published=True,
        )
        ue_match = UserExam.objects.create(
            user=self.user,
            exam=exam_match,
            question_order=[q_match.id],
            current_index=0,
        )

        # 1. Full correct match via selections dict
        ua_match = UserAnswer.objects.create(
            user_exam=ue_match,
            question=q_match,
            selections={"France": "Paris", "Japan": "Tokyo"},
        )
        score, passed = grade_exam(ue_match, None)
        self.assertEqual(score, 100.0)
        self.assertTrue(passed)

        # 2. Reset and test partial/wrong match
        ue_match.submitted_at = None
        ue_match.status = UserExam.STATUS_STARTED
        ue_match.save()
        ua_match.selections = {"France": "Paris", "Japan": "Kyoto"}
        ua_match.save()
        score, passed = grade_exam(ue_match, None)
        self.assertEqual(score, 0.0)
        self.assertFalse(passed)

        # 3. Test ordering question with reversed order (wrong)
        exam_order = Exam.objects.create(
            title="Ordering Exam",
            question_count=1,
            duration_seconds=300,
            passing_score=50,
            is_free=True,
            is_published=True,
        )
        ue_order = UserExam.objects.create(
            user=self.user,
            exam=exam_order,
            question_order=[self.q_order.id],
            current_index=0,
        )
        ua_order = UserAnswer.objects.create(
            user_exam=ue_order,
            question=self.q_order,
            selections=[self.ch_order_2.id, self.ch_order_1.id],  # Reversed order
        )
        score_rev, passed_rev = grade_exam(ue_order, None)
        self.assertEqual(score_rev, 0.0)
        self.assertFalse(passed_rev)
