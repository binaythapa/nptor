from django.core.management import call_command
from django.test import TestCase

from quiz.models import Category, Domain, Exam, ExamTrack, Question


class SeedTestDataCommandTests(TestCase):
    def test_seed_is_repeatable_without_overwriting_unrelated_records(self):
        Domain.objects.create(name="Production Domain", slug="aws-cloud")

        call_command("seed_test_data")
        first_counts = (
            Domain.objects.filter(name__startswith="[SEED]").count(),
            Category.objects.filter(name__startswith="[SEED]").count(),
            Question.objects.filter(text__startswith="[SEED]").count(),
            ExamTrack.objects.filter(title__startswith="[SEED]").count(),
            Exam.objects.filter(title__startswith="[SEED]").count(),
        )

        call_command("seed_test_data")
        second_counts = (
            Domain.objects.filter(name__startswith="[SEED]").count(),
            Category.objects.filter(name__startswith="[SEED]").count(),
            Question.objects.filter(text__startswith="[SEED]").count(),
            ExamTrack.objects.filter(title__startswith="[SEED]").count(),
            Exam.objects.filter(title__startswith="[SEED]").count(),
        )

        self.assertEqual(first_counts, second_counts)
        self.assertEqual(Domain.objects.filter(name="Production Domain").count(), 1)

    def test_reset_removes_only_seed_records(self):
        production = Domain.objects.create(name="Production Domain", slug="production-domain")

        call_command("seed_test_data")
        call_command("seed_test_data", reset=True)

        self.assertEqual(Domain.objects.filter(pk=production.pk).count(), 1)
        self.assertEqual(Domain.objects.filter(name__startswith="[SEED]").count(), 0)
        self.assertEqual(Category.objects.filter(name__startswith="[SEED]").count(), 0)
        self.assertEqual(Question.objects.filter(text__startswith="[SEED]").count(), 0)
        self.assertEqual(ExamTrack.objects.filter(title__startswith="[SEED]").count(), 0)
        self.assertEqual(Exam.objects.filter(title__startswith="[SEED]").count(), 0)
