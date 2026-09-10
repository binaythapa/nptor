from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from courses.models import Course
from organizations.models.membership import OrganizationMember
from organizations.models.organization import Organization
from organizations.models.role import OrganizationRole
from quiz.models import Exam, Question


User = get_user_model()


class StaffContentCreationTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Creation School",
            slug="creation-school",
            org_type=Organization.TYPE_SCHOOL,
            is_active=True,
        )
        self.staff = User.objects.create_user(
            username="creation-staff",
            email="creation-staff@example.com",
            password="password",
        )
        OrganizationMember.objects.create(
            user=self.staff,
            organization=self.organization,
            role=OrganizationRole.STAFF,
        )
        self.client.force_login(self.staff)

    def test_staff_can_create_exam_with_creator_recorded(self):
        response = self.client.post(
            reverse(
                "organizations_admin:exam_create",
                kwargs={"slug": self.organization.slug},
            ),
            {
                "title": "Staff Created Exam",
                "question_count": 10,
                "duration_seconds": 600,
                "level": 1,
                "passing_score": 50,
                "max_mock_attempts": 3,
                "allow_review": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        exam = Exam.objects.get(title="Staff Created Exam")
        self.assertEqual(exam.organization, self.organization)
        self.assertEqual(exam.created_by, self.staff)
        self.assertFalse(exam.is_published)

    def test_staff_can_create_course_with_creator_recorded(self):
        response = self.client.post(
            reverse(
                "organizations_admin:org_course_create",
                kwargs={"slug": self.organization.slug},
            ),
            {
                "title": "Staff Created Course",
                "description": "A course created by a teacher.",
                "level": "beginner",
                "is_public": "",
                "is_published": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        course = Course.objects.get(title="Staff Created Course")
        self.assertEqual(course.organization, self.organization)
        self.assertEqual(course.created_by, self.staff)
        self.assertFalse(course.is_published)

    def test_staff_can_create_question_with_creator_recorded(self):
        response = self.client.post(
            reverse(
                "organizations_admin:question_add",
                kwargs={"slug": self.organization.slug},
            ),
            {
                "difficulty": Question.EASY,
                "question_type": Question.SINGLE,
                "text": "What is 2 + 2?",
                "explanation": "Basic arithmetic.",
                "choices-TOTAL_FORMS": "4",
                "choices-INITIAL_FORMS": "0",
                "choices-MIN_NUM_FORMS": "0",
                "choices-MAX_NUM_FORMS": "1000",
            },
        )
        self.assertEqual(response.status_code, 302)
        question = Question.objects.get(text="What is 2 + 2?")
        self.assertEqual(question.organization, self.organization)
        self.assertEqual(question.created_by, self.staff)
