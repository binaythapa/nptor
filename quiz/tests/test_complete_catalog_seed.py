from django.core.management import call_command
from django.test import TestCase

from courses.models import Course, CourseSection, Lesson
from quiz.models import Category, Exam, ExamTrack, Question, TrackExam


class CompleteCatalogSeedTests(TestCase):
    def run_seed(self):
        call_command("seed_nptor_catalog", verbosity=0)

    def test_complete_catalog_contains_major_preparation_families(self):
        self.run_seed()

        expected_courses = {
            "mba-complete-preparation",
            "mbbs-complete-preparation",
            "ioe-complete-preparation",
            "class11-complete-preparation",
            "snowflake-complete-preparation",
            "aws-complete-preparation",
            "azure-complete-preparation",
        }
        self.assertTrue(expected_courses.issubset(set(Course.objects.values_list("slug", flat=True))))
        self.assertGreaterEqual(Category.objects.filter(organization=None).count(), 32)
        self.assertGreaterEqual(Question.objects.filter(organization=None, is_deleted=False).count(), 160)
        self.assertGreaterEqual(Exam.objects.filter(organization=None).count(), 7)
        self.assertGreaterEqual(ExamTrack.objects.filter(organization=None).count(), 7)
        self.assertGreaterEqual(TrackExam.objects.count(), 7)

    def test_courses_have_all_four_lesson_types(self):
        self.run_seed()

        for slug in (
            "mba-complete-preparation",
            "mbbs-complete-preparation",
            "ioe-complete-preparation",
            "class11-complete-preparation",
            "snowflake-complete-preparation",
            "aws-complete-preparation",
            "azure-complete-preparation",
        ):
            course = Course.objects.get(slug=slug)
            lesson_types = set(course.sections.values_list("lessons__lesson_type", flat=True))
            self.assertTrue({Lesson.TYPE_ARTICLE, Lesson.TYPE_VIDEO, Lesson.TYPE_PRACTICE, Lesson.TYPE_QUIZ}.issubset(lesson_types), slug)

    def test_all_supported_question_types_are_seeded(self):
        self.run_seed()

        types = set(Question.objects.filter(organization=None, is_deleted=False).values_list("question_type", flat=True))
        self.assertTrue({
            Question.SINGLE,
            Question.MULTI,
            Question.TRUE_FALSE,
            Question.DROPDOWN,
            Question.FILL_BLANK,
            Question.NUMERIC,
            Question.MATCHING,
            Question.ORDERING,
        }.issubset(types))

    def test_seed_is_idempotent(self):
        self.run_seed()
        counts_before = (
            Category.objects.filter(organization=None).count(),
            Question.objects.filter(organization=None, is_deleted=False).count(),
            Exam.objects.filter(organization=None).count(),
            ExamTrack.objects.filter(organization=None).count(),
            Course.objects.filter(organization=None).count(),
            CourseSection.objects.filter(course__organization=None).count(),
            Lesson.objects.filter(section__course__organization=None).count(),
        )

        self.run_seed()
        counts_after = (
            Category.objects.filter(organization=None).count(),
            Question.objects.filter(organization=None, is_deleted=False).count(),
            Exam.objects.filter(organization=None).count(),
            ExamTrack.objects.filter(organization=None).count(),
            Course.objects.filter(organization=None).count(),
            CourseSection.objects.filter(course__organization=None).count(),
            Lesson.objects.filter(section__course__organization=None).count(),
        )
        self.assertEqual(counts_before, counts_after)
