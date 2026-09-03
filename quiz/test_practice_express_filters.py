from django.test import TestCase
from django.urls import reverse

from quiz.models import Category, Choice, Domain, Question


class PracticeExpressFilterTests(TestCase):
    def setUp(self):
        self.aws = Domain.objects.create(
            name="[TEST] Express AWS",
            slug="test-express-aws",
            is_active=True,
        )
        self.azure = Domain.objects.create(
            name="[TEST] Express Azure",
            slug="test-express-azure",
            is_active=True,
        )

        self.aws_root = Category.objects.create(
            domain=self.aws,
            name="Compute",
            slug="test-express-aws-compute",
            is_active=True,
        )
        self.aws_child = Category.objects.create(
            domain=self.aws,
            parent=self.aws_root,
            name="EC2",
            slug="test-express-aws-ec2",
            is_active=True,
        )
        self.aws_storage = Category.objects.create(
            domain=self.aws,
            name="Storage",
            slug="test-express-aws-storage",
            is_active=True,
        )
        self.azure_compute = Category.objects.create(
            domain=self.azure,
            name="Compute",
            slug="test-express-azure-compute",
            is_active=True,
        )

        self.aws_primary_question = self._question(
            "Express AWS primary question",
            self.aws_child,
        )
        self.aws_m2m_question = self._question(
            "Express AWS M2M question",
            self.aws_storage,
            primary_category=None,
        )
        self.azure_question = self._question(
            "Express Azure question",
            self.azure_compute,
        )
        self.aws_hard_question = self._question(
            "Express AWS hard question",
            self.aws_storage,
            difficulty=Question.HARD,
        )

    def _question(self, text, category, primary_category=True, difficulty=Question.EASY):
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

    def test_next_filters_questions_by_domain_and_category_relations(self):
        response = self.client.get(
            reverse("quiz:practice_express_next"),
            {"domain": self.aws.id},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(response.json()["id"], {
            self.aws_primary_question.id,
            self.aws_m2m_question.id,
            self.aws_hard_question.id,
        })

        response = self.client.get(
            reverse("quiz:practice_express_next"),
            {
                "domain": self.aws.id,
                "category": self.aws_root.id,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], self.aws_primary_question.id)

    def test_next_filters_by_difficulty(self):
        response = self.client.get(
            reverse("quiz:practice_express_next"),
            {
                "domain": self.aws.id,
                "difficulty": Question.HARD,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], self.aws_hard_question.id)

    def test_next_switching_domain_returns_only_new_domain(self):
        first = self.client.get(
            reverse("quiz:practice_express_next"),
            {"domain": self.aws.id},
        )
        self.assertEqual(first.status_code, 200)

        second = self.client.get(
            reverse("quiz:practice_express_next"),
            {"domain": self.azure.id},
        )

        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()["id"], self.azure_question.id)
        self.assertEqual(second.json()["progress_total"], 1)
