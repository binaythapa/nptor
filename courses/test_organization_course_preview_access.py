from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from courses.models import Course, CourseEnrollment
from organizations.models import Organization, ResourceAccess, ResourceAssignment


User = get_user_model()


class OrganizationCoursePreviewAccessTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="org-course-student",
            password="test-password",
        )
        self.client.force_login(self.user)
        self.organization = Organization.objects.create(
            name="Organization A",
            slug="organization-a",
            org_type=Organization.TYPE_SCHOOL,
        )
        self.course = Course.objects.create(
            title="Organization Course",
            description="Assigned organization course",
            level="beginner",
            is_published=True,
            is_public=True,
            owner_type=Course.OWNER_ORGANIZATION,
            organization=self.organization,
        )

    def _assign_course(self):
        assignment = ResourceAssignment.objects.create(
            student=self.user,
            organization=self.organization,
            resource_type=ResourceAssignment.RESOURCE_COURSE,
            course=self.course,
            status=ResourceAssignment.STATUS_ASSIGNED,
            is_active=True,
        )
        ResourceAccess.objects.create(
            user=self.user,
            resource_type=ResourceAccess.RESOURCE_COURSE,
            course=self.course,
            source=ResourceAccess.SOURCE_ORGANIZATION,
            organization=self.organization,
            assignment=assignment,
            is_active=True,
        )

    def test_assigned_organization_course_preview_routes_to_course_detail(self):
        self._assign_course()

        response = self.client.get(
            reverse("courses:course_preview", kwargs={"slug": self.course.slug})
        )

        self.assertRedirects(
            response,
            reverse("courses:course_detail", kwargs={"slug": self.course.slug}),
        )

    def test_assigned_organization_course_can_use_enroll_endpoint(self):
        self._assign_course()

        response = self.client.post(
            reverse("courses:enroll_free_course", kwargs={"slug": self.course.slug})
        )

        self.assertRedirects(
            response,
            reverse("courses:course_learn", kwargs={"slug": self.course.slug}),
        )
        self.assertTrue(
            CourseEnrollment.objects.filter(
                user=self.user,
                course=self.course,
                is_active=True,
            ).exists()
        )

    def test_unassigned_organization_course_is_not_exposed_by_preview(self):
        response = self.client.get(
            reverse("courses:course_preview", kwargs={"slug": self.course.slug})
        )

        self.assertEqual(response.status_code, 404)
