from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.contrib.auth import get_user_model

from courses.models import Course, CourseSection, Lesson
from organizations.models import Organization, OrganizationMember
from quiz.models import Category, Choice, Exam, ExamTrack, Question, TrackExam
from subscriptions.models import SubscriptionPlan


class SeedDummyDataTests(TestCase):
    def test_seed_creates_coherent_demo_learning_data(self):
        output = StringIO()
        call_command("seed_dummy_data", stdout=output)

        User = get_user_model()
        self.assertTrue(User.objects.filter(username="demo_admin").exists())
        self.assertTrue(User.objects.filter(username="demo_student").exists())
        self.assertTrue(Organization.objects.filter(slug="demo-academy").exists())
        self.assertGreaterEqual(Category.objects.filter(name__startswith="Demo ").count(), 2)
        self.assertGreaterEqual(Exam.objects.filter(title__startswith="Demo ").count(), 3)
        self.assertGreaterEqual(Question.objects.filter(text__startswith="Demo ").count(), 6)
        self.assertGreaterEqual(Choice.objects.filter(text__startswith="Demo ").count(), 24)
        self.assertGreaterEqual(Course.objects.filter(title__startswith="Demo ").count(), 2)
        self.assertGreaterEqual(CourseSection.objects.filter(title__startswith="Demo ").count(), 2)
        self.assertGreaterEqual(Lesson.objects.filter(title__startswith="Demo ").count(), 2)
        self.assertGreaterEqual(ExamTrack.objects.filter(title__startswith="Demo ").count(), 2)
        self.assertGreaterEqual(TrackExam.objects.filter(track__title__startswith="Demo ").count(), 3)
        self.assertGreaterEqual(SubscriptionPlan.objects.filter(code__startswith="demo-").count(), 3)
        self.assertGreaterEqual(OrganizationMember.objects.filter(organization__slug="demo-academy").count(), 3)

        track = ExamTrack.objects.get(slug="demo-data-analytics-track")
        items = list(track.track_exams.select_related("exam").order_by("order"))
        self.assertEqual([item.order for item in items], [1, 2, 3])
        self.assertEqual(items[1].prerequisite_exams.count(), 1)
        self.assertEqual(items[1].prerequisite_exams.first(), items[0].exam)

    def test_seed_is_idempotent(self):
        call_command("seed_dummy_data", stdout=StringIO())
        User = get_user_model()
        counts_before = {
            "users": User.objects.filter(username__startswith="demo_").count(),
            "organizations": Organization.objects.filter(slug__startswith="demo-").count(),
            "exams": Exam.objects.filter(title__startswith="Demo ").count(),
            "courses": Course.objects.filter(title__startswith="Demo ").count(),
            "tracks": ExamTrack.objects.filter(title__startswith="Demo ").count(),
            "questions": Question.objects.filter(text__startswith="Demo ").count(),
            "choices": Choice.objects.filter(text__startswith="Demo ").count(),
        }

        call_command("seed_dummy_data", stdout=StringIO())

        counts_after = {
            "users": User.objects.filter(username__startswith="demo_").count(),
            "organizations": Organization.objects.filter(slug__startswith="demo-").count(),
            "exams": Exam.objects.filter(title__startswith="Demo ").count(),
            "courses": Course.objects.filter(title__startswith="Demo ").count(),
            "tracks": ExamTrack.objects.filter(title__startswith="Demo ").count(),
            "questions": Question.objects.filter(text__startswith="Demo ").count(),
            "choices": Choice.objects.filter(text__startswith="Demo ").count(),
        }
        self.assertEqual(counts_before, counts_after)
