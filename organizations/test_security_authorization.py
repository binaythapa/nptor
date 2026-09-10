from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from courses.models import Course
from organizations.models.access import ResourceAccess
from organizations.models.assignment import ResourceAssignment
from organizations.models.membership import OrganizationMember
from organizations.models.organization import Organization
from organizations.models.role import OrganizationRole
from organizations.services.assignments import assign_resource, StudentNotInOrganizationError
from organizations.services.content_permissions import user_can_manage_owned_content
from quiz.models import Exam, ExamTrack, Question
from subscriptions.models import Subscription, SubscriptionEntitlement, SubscriptionPlan
from subscriptions.services import AccessService
from organizations.views.admin.courses import _platform_or_organization_resource

User = get_user_model()


class OrganizationSecurityBoundaryTests(TestCase):
    def setUp(self):
        self.org_a = Organization.objects.create(name="School A", slug="security-a", org_type=Organization.TYPE_SCHOOL)
        self.org_b = Organization.objects.create(name="School B", slug="security-b", org_type=Organization.TYPE_SCHOOL)
        self.admin_a = User.objects.create_user(username="security-admin-a", email="security-a@example.com", password="password")
        self.student_a = User.objects.create_user(username="security-student-a", email="security-student-a@example.com", password="password")
        OrganizationMember.objects.create(user=self.admin_a, organization=self.org_a, role=OrganizationRole.ORG_ADMIN)
        OrganizationMember.objects.create(user=self.student_a, organization=self.org_a, role=OrganizationRole.STUDENT)

    def test_organization_resource_cannot_be_attached_across_org_boundary(self):
        course = Course.objects.create(title="Private B", organization=self.org_b, owner_type=Course.OWNER_ORGANIZATION)
        track = ExamTrack.objects.create(title="Private Track B", slug="private-track-b", organization=self.org_b)
        exam = Exam.objects.create(title="Private Exam B", organization=self.org_b, duration_seconds=60)
        self.assertFalse(_platform_or_organization_resource(course, self.org_a))
        self.assertFalse(_platform_or_organization_resource(track, self.org_a))
        self.assertFalse(_platform_or_organization_resource(exam, self.org_a))

    def test_platform_resources_remain_attachable(self):
        course = Course.objects.create(title="Platform Course", owner_type=Course.OWNER_PLATFORM)
        track = ExamTrack.objects.create(title="Platform Track", slug="platform-track")
        exam = Exam.objects.create(title="Platform Exam", duration_seconds=60)
        self.assertTrue(_platform_or_organization_resource(course, self.org_a))
        self.assertTrue(_platform_or_organization_resource(track, self.org_a))
        self.assertTrue(_platform_or_organization_resource(exam, self.org_a))

    def test_assignment_service_rejects_student_from_other_org(self):
        other_student = User.objects.create_user(username="security-student-b", email="security-student-b@example.com", password="password")
        OrganizationMember.objects.create(user=other_student, organization=self.org_b, role=OrganizationRole.STUDENT)
        course = Course.objects.create(title="Assigned Course")
        with self.assertRaises(StudentNotInOrganizationError):
            assign_resource(
                actor=self.admin_a,
                organization=self.org_a,
                student=other_student,
                resource_type=ResourceAssignment.RESOURCE_COURSE,
                resource_id=course.id,
            )

    def test_expired_organization_subscription_does_not_grant_access(self):
        course = Course.objects.create(title="Expired Course")
        plan = SubscriptionPlan.objects.create(name="Security Plan", code="security-plan")
        subscription = Subscription.objects.create(
            organization=self.org_a,
            plan=plan,
            status=Subscription.STATUS_ACTIVE,
            starts_at=timezone.now() - timedelta(days=10),
            expires_at=timezone.now() - timedelta(days=1),
        )
        SubscriptionEntitlement.objects.create(
            subscription=subscription,
            resource_type=SubscriptionEntitlement.RESOURCE_COURSE,
            course=course,
            is_active=True,
        )
        self.assertFalse(AccessService.organization_has_resource(self.org_a, AccessService.RESOURCE_COURSE, course))

    def test_organization_access_requires_matching_assignment(self):
        course = Course.objects.create(title="Assigned Course")
        access = ResourceAccess.objects.create(
            user=self.student_a,
            resource_type=ResourceAccess.RESOURCE_COURSE,
            source=ResourceAccess.SOURCE_ORGANIZATION,
            organization=self.org_a,
            course=course,
            is_active=True,
        )
        self.assertFalse(AccessService.has_access(
            student=self.student_a,
            resource_type=AccessService.RESOURCE_COURSE,
            resource=course,
        ))
        self.assertIsNotNone(access)


class StaffTeacherOrganizationPermissionTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="Teaching School",
            slug="teaching-school",
            org_type=Organization.TYPE_SCHOOL,
            is_active=True,
        )
        self.org_other = Organization.objects.create(
            name="Other School",
            slug="other-school-content",
            org_type=Organization.TYPE_SCHOOL,
            is_active=True,
        )
        self.owner = User.objects.create_user(username="teacher-owner", email="teacher-owner@example.com", password="password")
        self.admin = User.objects.create_user(username="teacher-admin", email="teacher-admin@example.com", password="password")
        self.staff = User.objects.create_user(username="teacher-staff", email="teacher-staff@example.com", password="password")
        self.other_staff = User.objects.create_user(username="teacher-other-staff", email="teacher-other-staff@example.com", password="password")
        self.student = User.objects.create_user(username="teacher-student", email="teacher-student@example.com", password="password")
        OrganizationMember.objects.create(user=self.owner, organization=self.org, role=OrganizationRole.ORG_OWNER)
        OrganizationMember.objects.create(user=self.admin, organization=self.org, role=OrganizationRole.ORG_ADMIN)
        OrganizationMember.objects.create(user=self.staff, organization=self.org, role=OrganizationRole.STAFF)
        OrganizationMember.objects.create(user=self.other_staff, organization=self.org, role=OrganizationRole.STAFF)
        OrganizationMember.objects.create(user=self.student, organization=self.org, role=OrganizationRole.STUDENT)

    def test_staff_can_manage_only_content_they_created(self):
        staff_course = Course.objects.create(
            title="Staff Course",
            organization=self.org,
            owner_type=Course.OWNER_ORGANIZATION,
            created_by=self.staff,
        )
        other_course = Course.objects.create(
            title="Other Course",
            organization=self.org,
            owner_type=Course.OWNER_ORGANIZATION,
            created_by=self.other_staff,
        )
        staff_exam = Exam.objects.create(title="Staff Exam", organization=self.org, duration_seconds=60, created_by=self.staff)
        other_exam = Exam.objects.create(title="Other Exam", organization=self.org, duration_seconds=60, created_by=self.other_staff)

        self.assertTrue(user_can_manage_owned_content(self.staff, self.org, staff_course))
        self.assertFalse(user_can_manage_owned_content(self.staff, self.org, other_course))
        self.assertTrue(user_can_manage_owned_content(self.staff, self.org, staff_exam))
        self.assertFalse(user_can_manage_owned_content(self.staff, self.org, other_exam))
        self.assertTrue(user_can_manage_owned_content(self.owner, self.org, other_course))
        self.assertTrue(user_can_manage_owned_content(self.admin, self.org, other_exam))
        self.assertFalse(user_can_manage_owned_content(self.student, self.org, staff_course))

    def test_staff_content_ownership_cannot_cross_organization_boundary(self):
        course = Course.objects.create(
            title="Other Organization Course",
            organization=self.org_other,
            owner_type=Course.OWNER_ORGANIZATION,
            created_by=self.staff,
        )
        self.assertFalse(user_can_manage_owned_content(self.staff, self.org, course))

    def test_staff_can_open_operational_create_and_management_pages(self):
        self.client.force_login(self.staff)
        for name in (
            "organizations_admin:questions",
            "organizations_admin:question_add",
            "organizations_admin:exams",
            "organizations_admin:exam_create",
            "organizations_admin:org_course_list",
            "organizations_admin:org_course_create",
            "organizations_admin:students",
            "organizations_admin:assignments",
            "organizations_admin:assignment_create",
        ):
            with self.subTest(name=name):
                response = self.client.get(self._url(name))
                self.assertEqual(response.status_code, 200)

    def test_student_cannot_open_staff_operational_pages(self):
        self.client.force_login(self.student)
        for name in (
            "organizations_admin:questions",
            "organizations_admin:question_add",
            "organizations_admin:exams",
            "organizations_admin:exam_create",
            "organizations_admin:org_course_list",
            "organizations_admin:org_course_create",
            "organizations_admin:students",
            "organizations_admin:assignments",
            "organizations_admin:assignment_create",
        ):
            with self.subTest(name=name):
                response = self.client.get(self._url(name))
                self.assertEqual(response.status_code, 403)

    def test_staff_can_edit_only_their_own_content(self):
        question = Question.objects.create(
            organization=self.org,
            created_by=self.staff,
            text="Staff question",
            difficulty=Question.EASY,
            question_type=Question.SINGLE,
        )
        other_question = Question.objects.create(
            organization=self.org,
            created_by=self.other_staff,
            text="Other question",
            difficulty=Question.EASY,
            question_type=Question.SINGLE,
        )
        exam = Exam.objects.create(
            title="Staff exam",
            organization=self.org,
            duration_seconds=60,
            created_by=self.staff,
        )
        other_exam = Exam.objects.create(
            title="Other exam",
            organization=self.org,
            duration_seconds=60,
            created_by=self.other_staff,
        )
        course = Course.objects.create(
            title="Staff course",
            description="Course",
            level="beginner",
            organization=self.org,
            owner_type=Course.OWNER_ORGANIZATION,
            created_by=self.staff,
        )
        other_course = Course.objects.create(
            title="Other course",
            description="Course",
            level="beginner",
            organization=self.org,
            owner_type=Course.OWNER_ORGANIZATION,
            created_by=self.other_staff,
        )

        self.client.force_login(self.staff)
        own_urls = (
            self._url("organizations_admin:question_edit", pk=question.pk),
            self._url("organizations_admin:exam_update", pk=exam.pk),
            self._url("organizations_admin:org_course_edit", pk=course.pk),
        )
        other_urls = (
            self._url("organizations_admin:question_edit", pk=other_question.pk),
            self._url("organizations_admin:exam_update", pk=other_exam.pk),
            self._url("organizations_admin:org_course_edit", pk=other_course.pk),
        )
        for url in own_urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
        for url in other_urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)

    def test_staff_can_add_and_remove_students_but_not_admin_roles(self):
        self.client.force_login(self.staff)
        new_student = User.objects.create_user(username="new-student", email="new-student@example.com", password="password")
        add_response = self.client.post(
            self._url("organizations_admin:student_add"),
            {"email": new_student.email, "role": OrganizationRole.STUDENT},
        )
        self.assertEqual(add_response.status_code, 302)
        member = OrganizationMember.objects.get(user=new_student, organization=self.org)
        self.assertEqual(member.role, OrganizationRole.STUDENT)

        remove_response = self.client.post(
            self._url("organizations_admin:student_remove", member_id=member.id),
        )
        self.assertEqual(remove_response.status_code, 302)
        self.assertFalse(OrganizationMember.objects.filter(id=member.id).exists())

        admin_user = User.objects.create_user(username="new-admin", email="new-admin@example.com", password="password")
        admin_attempt = self.client.post(
            self._url("organizations_admin:student_add"),
            {"email": admin_user.email, "role": OrganizationRole.ORG_ADMIN},
        )
        self.assertEqual(admin_attempt.status_code, 302)
        self.assertFalse(OrganizationMember.objects.filter(user=admin_user, organization=self.org).exists())

    def test_staff_cannot_manage_organization_settings(self):
        self.client.force_login(self.staff)
        response = self.client.get(self._url("organizations_admin:settings"))
        self.assertEqual(response.status_code, 403)

    def _url(self, name, **extra):
        from django.urls import reverse
        kwargs = {"slug": self.org.slug}
        kwargs.update(extra)
        return reverse(name, kwargs=kwargs)
