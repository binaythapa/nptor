from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from quiz.models import ContentVertical, Country, PreparationProgram


class PreparationProgramSeedTests(TestCase):
    def test_seed_creates_the_initial_local_exam_programs(self):
        call_command("seed_preparation_programs", stdout=StringIO())

        self.assertEqual(
            PreparationProgram.objects.filter(
                content_vertical__vertical_type=ContentVertical.ACADEMIC_EXAM,
                country__code="NPL",
            ).count(),
            3,
        )
        self.assertTrue(
            PreparationProgram.objects.filter(
                code="mbbs-entrance",
                name="MBBS Entrance Preparation",
            ).exists()
        )
        self.assertTrue(
            PreparationProgram.objects.filter(
                code="ioe-entrance",
                name="IOE Entrance Preparation",
            ).exists()
        )
        self.assertTrue(
            PreparationProgram.objects.filter(
                code="class-11-entrance",
                name="Class 11 Entrance Preparation",
            ).exists()
        )

    def test_seed_is_idempotent(self):
        call_command("seed_preparation_programs", stdout=StringIO())
        call_command("seed_preparation_programs", stdout=StringIO())

        self.assertEqual(
            PreparationProgram.objects.filter(country__code="NPL").count(),
            3,
        )
        self.assertEqual(Country.objects.filter(code="NPL").count(), 1)
        self.assertEqual(
            ContentVertical.objects.filter(
                vertical_type=ContentVertical.ACADEMIC_EXAM
            ).count(),
            1,
        )
