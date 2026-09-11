from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from courses.models import Course
from organizations.models import Organization, OrganizationMember, OrganizationStudent
from quiz.models import Category, Domain, Exam, ExamTrack, Question


User = get_user_model()


class SeedDemoDataCommandTests(TestCase):
    def test_seed_demo_data_creates_complete_dataset_and_is_idempotent(self):
        call_command("seed_demo_data", password="TestDemo123!")

        self.assertTrue(Organization.objects.filter(slug="demo-academy").exists())
        organization = Organization.objects.get(slug="demo-academy")

        self.assertEqual(
            OrganizationMember.objects.filter(organization=organization).count(),
            6,
        )
        self.assertEqual(
            OrganizationStudent.objects.filter(organization=organization).count(),
            3,
        )
        self.assertEqual(Course.objects.filter(organization=organization).count(), 3)
        self.assertEqual(ExamTrack.objects.filter(organization=organization).count(), 2)
        self.assertEqual(Exam.objects.filter(organization=organization).count(), 2)
        self.assertEqual(Question.objects.filter(organization=organization).count(), 5)
        self.assertEqual(Domain.objects.filter(organization=organization).count(), 1)
        self.assertEqual(Category.objects.filter(organization=organization).count(), 4)

        self.assertTrue(
            User.objects.get(username="demo_teacher").check_password("TestDemo123!")
        )

        call_command("seed_demo_data", password="TestDemo123!")

        self.assertEqual(
            Organization.objects.filter(slug="demo-academy").count(),
            1,
        )
        self.assertEqual(
            Course.objects.filter(organization=organization).count(),
            3,
        )
        self.assertEqual(
            Question.objects.filter(organization=organization).count(),
            5,
        )
