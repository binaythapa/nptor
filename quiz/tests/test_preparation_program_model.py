from django.db import IntegrityError
from django.test import TestCase

from courses.models import Course
from quiz.models import ContentVertical, Country, Exam, PreparationProgram


class PreparationProgramModelTests(TestCase):
    def setUp(self):
        self.vertical = ContentVertical.objects.create(
            name="Academic Exam",
            code="academic-exam-test",
            vertical_type=ContentVertical.ACADEMIC_EXAM,
        )
        self.country = Country.objects.create(
            name="Nepal", code="NPL", slug="nepal-test", is_active=True
        )

    def test_program_can_group_reusable_courses_and_exams(self):
        course = Course.objects.create(
            title="Biology Preparation",
            description="Original NPTOR biology preparation.",
            level="beginner",
        )
        exam = Exam.objects.create(
            title="MBBS Biology Mock",
            question_count=20,
            duration_seconds=1800,
        )
        program = PreparationProgram.objects.create(
            content_vertical=self.vertical,
            country=self.country,
            name="MBBS Entrance Preparation",
            code="mbbs-entrance",
            slug="mbbs-entrance-test",
            description="Preparation program for MBBS entrance.",
        )
        program.courses.add(course)
        program.exams.add(exam)

        self.assertEqual(program.courses.count(), 1)
        self.assertEqual(program.exams.count(), 1)
        self.assertEqual(program.courses.get(), course)
        self.assertEqual(program.exams.get(), exam)

    def test_program_code_is_unique_within_a_vertical(self):
        PreparationProgram.objects.create(
            content_vertical=self.vertical,
            name="MBBS Entrance Preparation",
            code="mbbs-entrance",
            slug="mbbs-entrance-test",
        )

        with self.assertRaises(IntegrityError):
            PreparationProgram.objects.create(
                content_vertical=self.vertical,
                name="Duplicate MBBS Preparation",
                code="mbbs-entrance",
                slug="mbbs-entrance-test-2",
            )

    def test_country_is_optional_for_global_programs(self):
        program = PreparationProgram.objects.create(
            content_vertical=self.vertical,
            name="Global Academic Program",
            code="global-academic",
            slug="global-academic-test",
        )

        self.assertIsNone(program.country)
        self.assertTrue(program.is_active)
        self.assertFalse(program.is_published)

    def test_database_index_names_are_mysql_compatible(self):
        index_names = {
            index.name
            for index in PreparationProgram._meta.indexes
        }
        self.assertTrue(index_names)
        self.assertTrue(all(len(name) <= 30 for name in index_names))
