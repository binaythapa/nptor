from django.test import RequestFactory, TestCase

from courses.models import Course
from organizations.models.organization import Organization
from organizations.views.admin.courses import org_courses
from quiz.models import Exam, ExamTrack


class OrganizationResourceIsolationTests(TestCase):
    def test_resource_dashboard_shows_only_current_organization_resources(self):
        org_a = Organization.objects.create(
            name="Organization A",
            slug="organization-a",
            org_type=Organization.TYPE_SCHOOL,
            is_active=True,
        )
        org_b = Organization.objects.create(
            name="Organization B",
            slug="organization-b",
            org_type=Organization.TYPE_SCHOOL,
            is_active=True,
        )

        Course.objects.create(title="Org A Course", organization=org_a)
        Course.objects.create(title="Org B Course", organization=org_b)
        ExamTrack.objects.create(
            title="Org A Track",
            slug="org-a-track",
            organization=org_a,
        )
        ExamTrack.objects.create(
            title="Org B Track",
            slug="org-b-track",
            organization=org_b,
        )
        Exam.objects.create(
            title="Org A Exam",
            organization=org_a,
            duration_seconds=600,
        )
        Exam.objects.create(
            title="Org B Exam",
            organization=org_b,
            duration_seconds=600,
        )

        request = RequestFactory().get(
            f"/org/{org_b.slug}/admin/courses/"
        )
        request.organization = org_b
        request.user = object()

        response = org_courses.__wrapped__(request, org_b.slug)
        content = response.content.decode("utf-8")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Org B Course", content)
        self.assertIn("Org B Track", content)
        self.assertIn("Org B Exam", content)
        self.assertNotIn("Org A Course", content)
        self.assertNotIn("Org A Track", content)
        self.assertNotIn("Org A Exam", content)
