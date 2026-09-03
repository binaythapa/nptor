from django.test import TestCase
from django.urls import reverse

from quiz.models import Category, Choice, Domain, Question


class PracticeFilterTests(TestCase):
    def setUp(self):
        self.aws = Domain.objects.create(
            name="[TEST] AWS",
            slug="test-aws",
            is_active=True,
        )
        self.azure = Domain.objects.create(
            name="[TEST] Azure",
            slug="test-azure",
            is_active=True,
        )

        self.aws_root = Category.objects.create(
            domain=self.aws,
            name="Compute",
            slug="test-aws-compute",
            is_active=True,
        )
        self.aws_child = Category.objects.create(
            domain=self.aws,
            parent=self.aws_root,
            name="EC2",
            slug="test-aws-ec2",
            is_active=True,
        )
        self.aws_storage = Category.objects.create(
            domain=self.aws,
            name="Storage",
            slug="test-aws-storage",
            is_active=True,
        )
        self.azure_compute = Category.objects.create(
            domain=self.azure,
            name="Compute",
            slug="test-azure-compute",
            is_active=True,
        )

        self.aws_compute_question = self._question(
            "AWS compute question",
            self.aws_child,
        )
        self.aws_storage_question = self._question(
            "AWS storage question",
            self.aws_storage,
            difficulty=Question.HARD,
        )
        self.aws_multi_category_question = self._question(
            "AWS multi-category question",
            self.aws_child,
            primary_category=None,
        )
        self.azure_question = self._question(
            "Azure compute question",
            self.azure_compute,
        )

    def _question(
        self,
        text,
        category,
        primary_category=True,
        difficulty=Question.EASY,
    ):
        question = Question.objects.create(
            primary_category=category if primary_category is not None else None,
            question_type=Question.SINGLE,
            difficulty=difficulty,
            text=text,
            is_active=True,
            is_deleted=False,
        )
        Choice.objects.create(
            question=question,
            text="Correct",
            is_correct=True,
        )
        question.categories.add(category)
        return question

    def _session(self):
        return self.client.session

    def test_domain_filter_uses_question_categories(self):
        response = self.client.get(
            reverse("quiz:practice"),
            {"domain": self.aws.id},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._session()["p_total"], 3)
        self.assertEqual(
            response.context["domain_id"],
            str(self.aws.id),
        )
        self.assertEqual(
            response.context["categories"].count(),
            3,
        )

    def test_all_categories_with_domain_keeps_entire_domain_pool(self):
        response = self.client.get(
            reverse("quiz:practice"),
            {"domain": self.aws.id},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["category_id"])
        self.assertEqual(self._session()["p_total"], 3)

    def test_category_filter_includes_descendants_and_m2m_categories(self):
        response = self.client.get(
            reverse("quiz:practice"),
            {
                "domain": self.aws.id,
                "category": self.aws_root.id,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._session()["p_total"], 2)
        self.assertEqual(
            response.context["category_id"],
            str(self.aws_root.id),
        )

    def test_difficulty_filter_limits_domain_question_pool(self):
        response = self.client.get(
            reverse("quiz:practice"),
            {
                "domain": self.aws.id,
                "difficulty": Question.HARD,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._session()["p_total"], 1)
        self.assertEqual(
            response.context["difficulty"],
            Question.HARD,
        )
        self.assertEqual(
            response.context["question"].id,
            self.aws_storage_question.id,
        )

    def test_switching_domain_resets_previous_question_state(self):
        first = self.client.get(
            reverse("quiz:practice"),
            {"domain": self.aws.id},
        )
        self.assertEqual(first.status_code, 200)
        first_qid = self._session()["p_qid"]
        self._session()["p_seen"] = [first_qid]
        self._session().save()

        second = self.client.get(
            reverse("quiz:practice"),
            {"domain": self.azure.id},
        )

        self.assertEqual(second.status_code, 200)
        session = self._session()
        self.assertEqual(session["p_seen"], [])
        self.assertEqual(session["p_total"], 1)
        self.assertEqual(session["p_qid"], self.azure_question.id)
        self.assertNotEqual(session["p_qid"], first_qid)
