from django.test import TestCase

from courses.models import Course, CourseExam
from organizations.forms.content import OrganizationCourseForm
from organizations.models.organization import Organization
from quiz.models import Exam


class OrganizationCourseFormTests(TestCase):
    def test_existing_course_exam_selection_loads_on_edit(self):
        organization = Organization.objects.create(
            name="Test School",
            slug="test-school-course-form",
            org_type=Organization.TYPE_SCHOOL,
            is_active=True,
        )
        course = Course.objects.create(
            title="Test Course",
            description="Course description",
            level="beginner",
            organization=organization,
            owner_type=Course.OWNER_ORGANIZATION,
        )
        exam = Exam.objects.create(
            title="Test Exam",
            organization=organization,
            question_count=10,
            duration_seconds=600,
        )
        CourseExam.objects.create(course=course, exam=exam, order=1)

        form = OrganizationCourseForm(instance=course, organization=organization)

        self.assertEqual(
            list(form.fields["exams"].initial),
            [exam.pk],
        )
