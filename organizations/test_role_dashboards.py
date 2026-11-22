from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from courses.models import Course
from organizations.models import (
    AcademicYear,
    ClassSection,
    ClassTeacher,
    ClassResourceAssignment,
    Organization,
    OrganizationClass,
    OrganizationMember,
    OrganizationRole,
    OrganizationStudent,
    OrganizationAuditLog,
    ResourceAssignment,
    StudentEnrollment,
)
from quiz.models import Category, Domain, Exam, ExamTrack, Question, UserExam

User = get_user_model()


class RoleBasedDashboardTests(TestCase):
    def setUp(self):
        # Create Primary Organization
        self.org = Organization.objects.create(
            name="Apex Academy",
            slug="apex-academy",
            org_type=Organization.TYPE_SCHOOL,
            is_active=True,
        )

        # Create Secondary Organization (for cross-org isolation tests)
        self.other_org = Organization.objects.create(
            name="Zenith College",
            slug="zenith-college",
            org_type=Organization.TYPE_COLLEGE,
            is_active=True,
        )

        # Users
        self.owner = User.objects.create_user(username="apex_owner", password="password123", first_name="Alice", last_name="Owner")
        self.admin = User.objects.create_user(username="apex_admin", password="password123", first_name="Bob", last_name="Admin")
        self.teacher1 = User.objects.create_user(username="apex_teacher1", password="password123", first_name="Charlie", last_name="Teacher")
        self.teacher2 = User.objects.create_user(username="apex_teacher2", password="password123", first_name="Diana", last_name="Teacher")
        self.student1_user = User.objects.create_user(username="apex_student1", password="password123", first_name="Evan", last_name="Student")
        self.student2_user = User.objects.create_user(username="apex_student2", password="password123", first_name="Fiona", last_name="Student")
        self.inactive_user = User.objects.create_user(username="apex_inactive", password="password123", first_name="Ian", last_name="Inactive")
        self.non_member = User.objects.create_user(username="apex_outsider", password="password123", first_name="Oscar", last_name="Outsider")

        # Memberships in Apex Academy
        self.owner_member = OrganizationMember.objects.create(
            user=self.owner, organization=self.org, role=OrganizationRole.ORG_OWNER, is_active=True
        )
        self.admin_member = OrganizationMember.objects.create(
            user=self.admin, organization=self.org, role=OrganizationRole.ORG_ADMIN, is_active=True
        )
        self.teacher1_member = OrganizationMember.objects.create(
            user=self.teacher1, organization=self.org, role=OrganizationRole.STAFF, is_active=True
        )
        self.teacher2_member = OrganizationMember.objects.create(
            user=self.teacher2, organization=self.org, role=OrganizationRole.STAFF, is_active=True
        )
        self.student1_member = OrganizationMember.objects.create(
            user=self.student1_user, organization=self.org, role=OrganizationRole.STUDENT, is_active=True
        )
        self.student2_member = OrganizationMember.objects.create(
            user=self.student2_user, organization=self.org, role=OrganizationRole.STUDENT, is_active=True
        )
        self.inactive_member = OrganizationMember.objects.create(
            user=self.inactive_user, organization=self.org, role=OrganizationRole.STUDENT, is_active=False
        )

        # OrganizationStudent records
        self.student1 = OrganizationStudent.objects.create(
            organization=self.org, user=self.student1_user, student_id="STU-001", admission_no="ADM-101"
        )
        self.student2 = OrganizationStudent.objects.create(
            organization=self.org, user=self.student2_user, student_id="STU-002", admission_no="ADM-102"
        )

        # Academic Structure
        self.year = AcademicYear.objects.create(
            organization=self.org, name="2026/2027", start_date="2026-04-01", end_date="2027-03-31", is_current=True
        )
        self.grade10 = OrganizationClass.objects.create(
            organization=self.org, name="Grade 10", code="G10", is_active=True
        )
        self.section_a = ClassSection.objects.create(
            organization=self.org, academic_year=self.year, class_group=self.grade10, name="A", capacity=30, is_active=True
        )
        self.section_b = ClassSection.objects.create(
            organization=self.org, academic_year=self.year, class_group=self.grade10, name="B", capacity=30, is_active=True
        )

        # Teacher 1 assigned to Section A; Teacher 2 assigned to Section B
        self.class_teacher1 = ClassTeacher.objects.create(
            organization=self.org, teacher=self.teacher1, class_section=self.section_a, academic_year=self.year,
            subject="Mathematics", is_primary=True, is_active=True
        )
        self.class_teacher2 = ClassTeacher.objects.create(
            organization=self.org, teacher=self.teacher2, class_section=self.section_b, academic_year=self.year,
            subject="Physics", is_primary=True, is_active=True
        )

        # Student 1 enrolled in Section A; Student 2 enrolled in Section B
        self.enrollment1 = StudentEnrollment.objects.create(
            student=self.student1, academic_year=self.year, class_section=self.section_a,
            roll_number="1", status=StudentEnrollment.STATUS_ACTIVE
        )
        self.enrollment2 = StudentEnrollment.objects.create(
            student=self.student2, academic_year=self.year, class_section=self.section_b,
            roll_number="2", status=StudentEnrollment.STATUS_ACTIVE
        )

        # Courses & Exams
        self.course_a = Course.objects.create(
            title="Advanced Algebra", slug="adv-algebra", organization=self.org, created_by=self.teacher1, is_published=True
        )
        self.course_b = Course.objects.create(
            title="Newtonian Mechanics", slug="newton-mechanics", organization=self.org, created_by=self.teacher2, is_published=True
        )
        self.exam_a = Exam.objects.create(
            title="Algebra Midterm", organization=self.org, created_by=self.teacher1, is_published=True, duration_seconds=3600
        )
        self.exam_b = Exam.objects.create(
            title="Physics Final", organization=self.org, created_by=self.teacher2, is_published=True, duration_seconds=3600
        )

        # Resource Assignments:
        # Student 1 gets Course A and Exam A directly from Teacher 1
        self.assignment_s1_course = ResourceAssignment.objects.create(
            organization=self.org, student=self.student1_user, assigned_by=self.teacher1,
            resource_type=ResourceAssignment.RESOURCE_COURSE, course=self.course_a,
            status=ResourceAssignment.STATUS_ASSIGNED, is_active=True,
            due_at=timezone.now() + timedelta(days=7)
        )
        self.assignment_s1_exam = ResourceAssignment.objects.create(
            organization=self.org, student=self.student1_user, assigned_by=self.teacher1,
            resource_type=ResourceAssignment.RESOURCE_EXAM, exam=self.exam_a,
            status=ResourceAssignment.STATUS_ASSIGNED, is_active=True,
            due_at=timezone.now() + timedelta(days=3)
        )

        # Student 2 gets Course B directly from Teacher 2
        self.assignment_s2_course = ResourceAssignment.objects.create(
            organization=self.org, student=self.student2_user, assigned_by=self.teacher2,
            resource_type=ResourceAssignment.RESOURCE_COURSE, course=self.course_b,
            status=ResourceAssignment.STATUS_ASSIGNED, is_active=True,
            due_at=timezone.now() + timedelta(days=5)
        )

        # Section-level assignment: Exam B assigned to Section B
        self.section_b_exam = ClassResourceAssignment.objects.create(
            organization=self.org, class_section=self.section_b, assigned_by=self.teacher2,
            resource_type=ClassResourceAssignment.RESOURCE_EXAM, exam=self.exam_b, is_active=True
        )

        # UserExam attempt for Student 1
        self.attempt_s1 = UserExam.objects.create(
            user=self.student1_user, exam=self.exam_a, status=UserExam.STATUS_SUBMITTED,
            score=88.5, passed=True, submitted_at=timezone.now()
        )

        # Audit Log Entry
        self.audit_log = OrganizationAuditLog.objects.create(
            organization=self.org, actor=self.owner, action="organization.created", target_type="Organization", target_id=str(self.org.id)
        )

    # 1. Owner accesses Admin Dashboard
    def test_org_owner_accesses_admin_dashboard(self):
        self.client.force_login(self.owner)
        url = reverse("organizations_admin:dashboard", kwargs={"slug": self.org.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Apex Academy")
        self.assertContains(response, "Organization Administration")
        self.assertContains(response, "Students")
        self.assertContains(response, "Academic Structure")
        self.assertContains(response, "Recent Student Assignments")
        self.assertContains(response, "Recent Activity Log")

    # 2. Admin accesses Admin Dashboard
    def test_org_admin_accesses_admin_dashboard(self):
        self.client.force_login(self.admin)
        url = reverse("organizations_admin:dashboard", kwargs={"slug": self.org.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Apex Academy")
        self.assertContains(response, "Teachers / Staff")

    # 3. Teacher accesses Teacher Dashboard
    def test_teacher_accesses_teacher_dashboard(self):
        self.client.force_login(self.teacher1)
        url = reverse("organizations_admin:teacher_dashboard", kwargs={"slug": self.org.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Teacher Portal")
        self.assertContains(response, "Welcome, Charlie Teacher")
        self.assertContains(response, "My Assigned Sections")
        self.assertContains(response, "Students in My Sections")
        self.assertContains(response, "Teaching Tools &amp; Actions")

    # 4. Teacher denied direct access to Admin Dashboard
    def test_teacher_denied_admin_dashboard(self):
        self.client.force_login(self.teacher1)
        url = reverse("organizations_admin:dashboard", kwargs={"slug": self.org.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    # 5. Teacher sees only assigned sections and students (strict scoping)
    def test_teacher_sees_only_assigned_sections_and_students(self):
        self.client.force_login(self.teacher1)
        url = reverse("organizations_admin:teacher_dashboard", kwargs={"slug": self.org.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Context inspection
        teacher_data = response.context["teacher_data"]
        # Teacher 1 only has Section A assigned (1 section)
        self.assertEqual(teacher_data["assigned_sections_count"], 1)
        # Teacher 1 only has 1 student in Section A (Evan Student), NOT 2 students
        self.assertEqual(teacher_data["total_section_students"], 1)

        # Evan Student should appear in response HTML; Fiona Student should NOT appear
        self.assertContains(response, "Evan Student")
        self.assertNotContains(response, "Fiona Student")

        # Section A should appear; Section B should NOT appear in assigned sections
        self.assertContains(response, "Section A")

    # 6. Student accesses Student Dashboard
    def test_student_accesses_student_dashboard(self):
        self.client.force_login(self.student1_user)
        url = reverse("organizations_public:learning", kwargs={"slug": self.org.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Apex Academy · Student Dashboard")
        self.assertContains(response, "Evan Student")
        self.assertContains(response, "My Assigned Courses")
        self.assertContains(response, "Upcoming &amp; Assigned Exams")
        self.assertContains(response, "Recent Exam Attempts &amp; Performance")
        # Check alias route
        alias_url = reverse("organizations_public:student_dashboard", kwargs={"slug": self.org.slug})
        alias_response = self.client.get(alias_url)
        self.assertEqual(alias_response.status_code, 200)

    # 7. Student denied access to Admin and Teacher dashboards
    def test_student_denied_admin_and_teacher_dashboards(self):
        self.client.force_login(self.student1_user)
        admin_url = reverse("organizations_admin:dashboard", kwargs={"slug": self.org.slug})
        response_admin = self.client.get(admin_url)
        self.assertEqual(response_admin.status_code, 403)

        teacher_url = reverse("organizations_admin:teacher_dashboard", kwargs={"slug": self.org.slug})
        response_teacher = self.client.get(teacher_url)
        self.assertEqual(response_teacher.status_code, 403)

    # 8. Student sees only their own data
    def test_student_sees_only_own_data(self):
        self.client.force_login(self.student1_user)
        url = reverse("organizations_public:learning", kwargs={"slug": self.org.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Student 1 has Course A assigned, NOT Course B
        self.assertContains(response, "Advanced Algebra")
        self.assertNotContains(response, "Newtonian Mechanics")

        # Student 1 has Exam A attempt (88.5%), Student 2's data must not be here
        self.assertContains(response, "Algebra Midterm")
        self.assertContains(response, "88.5%")

    # 9. Central Role Dispatcher routes to appropriate dashboard based on role
    def test_role_dashboard_dispatch(self):
        dispatch_url = reverse("organizations_public:dashboard", kwargs={"slug": self.org.slug})

        # Owner -> Admin Dashboard
        self.client.force_login(self.owner)
        resp_owner = self.client.get(dispatch_url)
        self.assertRedirects(resp_owner, reverse("organizations_admin:dashboard", kwargs={"slug": self.org.slug}))

        # Admin -> Admin Dashboard
        self.client.force_login(self.admin)
        resp_admin = self.client.get(dispatch_url)
        self.assertRedirects(resp_admin, reverse("organizations_admin:dashboard", kwargs={"slug": self.org.slug}))

        # Teacher -> Teacher Dashboard
        self.client.force_login(self.teacher1)
        resp_teacher = self.client.get(dispatch_url)
        self.assertRedirects(resp_teacher, reverse("organizations_admin:teacher_dashboard", kwargs={"slug": self.org.slug}))

        # Student -> Student Dashboard (learning)
        self.client.force_login(self.student1_user)
        resp_student = self.client.get(dispatch_url)
        self.assertRedirects(resp_student, reverse("organizations_public:learning", kwargs={"slug": self.org.slug}))

    # 10. Inactive membership denied access
    def test_inactive_membership_denied(self):
        self.client.force_login(self.inactive_user)
        dispatch_url = reverse("organizations_public:dashboard", kwargs={"slug": self.org.slug})
        response = self.client.get(dispatch_url)
        self.assertEqual(response.status_code, 403)

        learning_url = reverse("organizations_public:learning", kwargs={"slug": self.org.slug})
        response_learning = self.client.get(learning_url)
        self.assertEqual(response_learning.status_code, 403)

    # 11. Non-member denied access to organization
    def test_non_member_denied(self):
        self.client.force_login(self.non_member)
        dispatch_url = reverse("organizations_public:dashboard", kwargs={"slug": self.org.slug})
        response = self.client.get(dispatch_url)
        self.assertEqual(response.status_code, 403)

        admin_url = reverse("organizations_admin:dashboard", kwargs={"slug": self.org.slug})
        response_admin = self.client.get(admin_url)
        self.assertEqual(response_admin.status_code, 403)

        teacher_url = reverse("organizations_admin:teacher_dashboard", kwargs={"slug": self.org.slug})
        response_teacher = self.client.get(teacher_url)
        self.assertEqual(response_teacher.status_code, 403)

        learning_url = reverse("organizations_public:learning", kwargs={"slug": self.org.slug})
        response_learning = self.client.get(learning_url)
        self.assertEqual(response_learning.status_code, 403)

    # 12. Cross-organization isolation
    def test_cross_organization_isolation(self):
        # Admin of Apex Academy attempts to access Zenith College
        self.client.force_login(self.admin)
        other_admin_url = reverse("organizations_admin:dashboard", kwargs={"slug": self.other_org.slug})
        response = self.client.get(other_admin_url)
        self.assertEqual(response.status_code, 403)

        other_dispatch_url = reverse("organizations_public:dashboard", kwargs={"slug": self.other_org.slug})
        response_dispatch = self.client.get(other_dispatch_url)
        self.assertEqual(response_dispatch.status_code, 403)

    # 13. Academic Management Dashboard role-based visibility
    def test_academic_management_role_visibility(self):
        academic_url = reverse("organizations_admin:academic", kwargs={"slug": self.org.slug})

        # Admin view: sees full management buttons and all sections
        self.client.force_login(self.admin)
        resp_admin = self.client.get(academic_url)
        self.assertEqual(resp_admin.status_code, 200)
        self.assertContains(resp_admin, "Add Academic Year")
        self.assertContains(resp_admin, "Add Class")
        self.assertContains(resp_admin, "Add Section")
        self.assertContains(resp_admin, "Section A")
        self.assertContains(resp_admin, "Section B")

        # Teacher 1 view: restricted to Section A only, no Add buttons
        self.client.force_login(self.teacher1)
        resp_teacher = self.client.get(academic_url)
        self.assertEqual(resp_teacher.status_code, 200)
        self.assertContains(resp_teacher, "Teacher View:")
        self.assertNotContains(resp_teacher, "Add Academic Year")
        self.assertNotContains(resp_teacher, "Add Class")
        self.assertNotContains(resp_teacher, "Add Section")
        # Section A is taught by Teacher 1, Section B is not
        self.assertContains(resp_teacher, "Section A")
        self.assertNotContains(resp_teacher, "Section B")
