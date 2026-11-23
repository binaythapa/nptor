# organizations/test_org_analytics.py

from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
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
    ResourceAssignment,
    StudentEnrollment,
)
from organizations.services.analytics import (
    parse_date_range,
    get_admin_analytics,
    get_teacher_analytics,
    get_student_analytics,
)
from quiz.models import Category, Domain, Exam, ExamTrack, Question, UserExam

User = get_user_model()


class OrganizationAnalyticsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # 1. Organization A (Primary Tenant)
        cls.org_a = Organization.objects.create(name="Apex Academy", slug="apex-academy", is_active=True)

        # 2. Organization B (Isolated Tenant)
        cls.org_b = Organization.objects.create(name="Beta College", slug="beta-college", is_active=True)

        # 3. Users for Org A
        cls.admin_a = User.objects.create_user(username="admin_a", email="admin_a@example.com", password="password123")
        OrganizationMember.objects.create(organization=cls.org_a, user=cls.admin_a, role=OrganizationRole.ORG_ADMIN, is_active=True)

        cls.teacher_a1 = User.objects.create_user(username="teacher_a1", email="teacher_a1@example.com", password="password123")
        OrganizationMember.objects.create(organization=cls.org_a, user=cls.teacher_a1, role=OrganizationRole.STAFF, is_active=True)

        cls.teacher_a2 = User.objects.create_user(username="teacher_a2", email="teacher_a2@example.com", password="password123")
        OrganizationMember.objects.create(organization=cls.org_a, user=cls.teacher_a2, role=OrganizationRole.STAFF, is_active=True)

        cls.student_a1 = User.objects.create_user(username="student_a1", email="student_a1@example.com", password="password123")
        OrganizationMember.objects.create(organization=cls.org_a, user=cls.student_a1, role=OrganizationRole.STUDENT, is_active=True)
        cls.org_student_a1 = OrganizationStudent.objects.create(organization=cls.org_a, user=cls.student_a1, student_id="STU-A1")

        cls.student_a2 = User.objects.create_user(username="student_a2", email="student_a2@example.com", password="password123")
        OrganizationMember.objects.create(organization=cls.org_a, user=cls.student_a2, role=OrganizationRole.STUDENT, is_active=True)
        cls.org_student_a2 = OrganizationStudent.objects.create(organization=cls.org_a, user=cls.student_a2, student_id="STU-A2")

        # 4. Users for Org B
        cls.admin_b = User.objects.create_user(username="admin_b", email="admin_b@example.com", password="password123")
        OrganizationMember.objects.create(organization=cls.org_b, user=cls.admin_b, role=OrganizationRole.ORG_ADMIN, is_active=True)

        cls.student_b = User.objects.create_user(username="student_b", email="student_b@example.com", password="password123")
        OrganizationMember.objects.create(organization=cls.org_b, user=cls.student_b, role=OrganizationRole.STUDENT, is_active=True)
        cls.org_student_b = OrganizationStudent.objects.create(organization=cls.org_b, user=cls.student_b, student_id="STU-B")

        # 5. Academic Structure Org A
        today = timezone.now().date()
        cls.year_a = AcademicYear.objects.create(
            organization=cls.org_a,
            name="2026/2027",
            start_date=today - timedelta(days=60),
            end_date=today + timedelta(days=300),
            is_current=True,
        )
        cls.class_a1 = OrganizationClass.objects.create(organization=cls.org_a, name="Class 10")
        cls.sec_a1 = ClassSection.objects.create(organization=cls.org_a, academic_year=cls.year_a, class_group=cls.class_a1, name="Section A")
        cls.sec_a2 = ClassSection.objects.create(organization=cls.org_a, academic_year=cls.year_a, class_group=cls.class_a1, name="Section B")

        # Assign teacher_a1 to sec_a1 only; teacher_a2 to sec_a2 only
        ClassTeacher.objects.create(organization=cls.org_a, academic_year=cls.year_a, class_section=cls.sec_a1, teacher=cls.teacher_a1, is_primary=True)
        ClassTeacher.objects.create(organization=cls.org_a, academic_year=cls.year_a, class_section=cls.sec_a2, teacher=cls.teacher_a2, is_primary=True)

        # Enroll student_a1 in sec_a1; student_a2 in sec_a2
        cls.enroll_a1 = StudentEnrollment.objects.create(student=cls.org_student_a1, academic_year=cls.year_a, class_section=cls.sec_a1, roll_number="101")
        cls.enroll_a2 = StudentEnrollment.objects.create(student=cls.org_student_a2, academic_year=cls.year_a, class_section=cls.sec_a2, roll_number="102")

        # Academic Structure Org B
        cls.year_b = AcademicYear.objects.create(
            organization=cls.org_b,
            name="2026/2027",
            start_date=today - timedelta(days=60),
            end_date=today + timedelta(days=300),
            is_current=True,
        )
        cls.class_b = OrganizationClass.objects.create(organization=cls.org_b, name="Grade 12")
        cls.sec_b = ClassSection.objects.create(organization=cls.org_b, academic_year=cls.year_b, class_group=cls.class_b, name="Section Alpha")
        StudentEnrollment.objects.create(student=cls.org_student_b, academic_year=cls.year_b, class_section=cls.sec_b, roll_number="201")

        # 6. Courses & Exams
        cls.course_a = Course.objects.create(title="Advanced Physics", slug="advanced-physics", organization=cls.org_a, is_published=True)
        cls.course_b = Course.objects.create(title="Beta Biology", slug="beta-biology", organization=cls.org_b, is_published=True)

        cls.domain_a = Domain.objects.create(name="Science", slug="science", organization=cls.org_a)
        cls.category_a = Category.objects.create(domain=cls.domain_a, name="Physics", slug="physics", organization=cls.org_a)
        cls.exam_a = Exam.objects.create(title="Physics Midterm", organization=cls.org_a, duration_seconds=45 * 60, is_published=True)
        cls.exam_a.categories.add(cls.category_a)
        cls.exam_b = Exam.objects.create(title="Biology Quiz", organization=cls.org_b, duration_seconds=30 * 60, is_published=True)

        # 7. Assignments in Org A
        # Direct assignment to student_a1 created by teacher_a1 (COMPLETED)
        cls.assign_a1 = ResourceAssignment.objects.create(
            organization=cls.org_a,
            student=cls.student_a1,
            assigned_by=cls.teacher_a1,
            resource_type=ResourceAssignment.RESOURCE_COURSE,
            course=cls.course_a,
            status=ResourceAssignment.STATUS_COMPLETED,
            due_at=timezone.now() + timedelta(days=5),
        )

        # Direct assignment to student_a2 created by teacher_a2 (STARTED)
        cls.assign_a2 = ResourceAssignment.objects.create(
            organization=cls.org_a,
            student=cls.student_a2,
            assigned_by=cls.teacher_a2,
            resource_type=ResourceAssignment.RESOURCE_EXAM,
            exam=cls.exam_a,
            status=ResourceAssignment.STATUS_STARTED,
            due_at=timezone.now() + timedelta(days=3),
        )

        # Overdue assignment to student_a1
        cls.assign_a_overdue = ResourceAssignment.objects.create(
            organization=cls.org_a,
            student=cls.student_a1,
            assigned_by=cls.teacher_a1,
            resource_type=ResourceAssignment.RESOURCE_EXAM,
            exam=cls.exam_a,
            status=ResourceAssignment.STATUS_ASSIGNED,
            due_at=timezone.now() - timedelta(days=2),
        )

        # Section Resource for sec_a1
        ClassResourceAssignment.objects.create(
            organization=cls.org_a,
            class_section=cls.sec_a1,
            assigned_by=cls.teacher_a1,
            resource_type=ClassResourceAssignment.RESOURCE_COURSE,
            course=cls.course_a,
        )

        # 8. Exam Attempts in Org A
        # student_a1 took exam_a (passed, score 85)
        cls.attempt_a1 = UserExam.objects.create(
            user=cls.student_a1,
            exam=cls.exam_a,
            status=UserExam.STATUS_SUBMITTED,
            score=85.0,
            passed=True,
            started_at=timezone.now() - timedelta(days=3),
            submitted_at=timezone.now() - timedelta(days=3),
        )

        # student_a2 took exam_a (failed, score 45)
        cls.attempt_a2 = UserExam.objects.create(
            user=cls.student_a2,
            exam=cls.exam_a,
            status=UserExam.STATUS_SUBMITTED,
            score=45.0,
            passed=False,
            started_at=timezone.now() - timedelta(days=1),
            submitted_at=timezone.now() - timedelta(days=1),
        )

        # Exam attempt in Org B (should never leak to Org A)
        cls.attempt_b = UserExam.objects.create(
            user=cls.student_b,
            exam=cls.exam_b,
            status=UserExam.STATUS_SUBMITTED,
            score=95.0,
            passed=True,
            started_at=timezone.now() - timedelta(days=2),
            submitted_at=timezone.now() - timedelta(days=2),
        )

    # ========================================================
    # 1. Date Range Filter Tests
    # ========================================================
    def test_parse_date_range_defaults_and_options(self):
        start_7d, end, range_7d, label_7d = parse_date_range("7d")
        self.assertEqual(range_7d, "7d")
        self.assertIsNotNone(start_7d)
        self.assertAlmostEqual((end - start_7d).total_seconds(), 7 * 86400, delta=10)

        start_all, end, range_all, label_all = parse_date_range("all")
        self.assertEqual(range_all, "all")
        self.assertIsNone(start_all)

        # Invalid string defaults safely to "30d"
        start_inv, end, range_inv, label_inv = parse_date_range("invalid_range_123")
        self.assertEqual(range_inv, "30d")
        self.assertIsNotNone(start_inv)

    # ========================================================
    # 2. Admin Analytics Tests (Accuracy & Multi-Tenant Isolation)
    # ========================================================
    def test_admin_analytics_kpi_and_tenant_isolation(self):
        analytics = get_admin_analytics(self.org_a, date_range="30d")

        # Org A people
        self.assertEqual(analytics["total_students"], 2)
        self.assertEqual(analytics["total_teachers"], 2)
        self.assertEqual(analytics["total_admins"], 1)

        # Academic structure
        self.assertEqual(analytics["academic_years_count"], 1)
        self.assertEqual(analytics["classes_count"], 1)
        self.assertEqual(analytics["sections_count"], 2)

        # Assignments (total 3 in org A)
        self.assertEqual(analytics["total_assignments"], 3)
        self.assertEqual(analytics["completed_assignments"], 1)
        self.assertEqual(analytics["started_assignments"], 1)
        self.assertEqual(analytics["assigned_assignments"], 1)
        self.assertEqual(analytics["overdue_assignments"], 1)
        self.assertAlmostEqual(analytics["completion_rate"], 33.3, places=1)

        # Exam submissions (2 submitted in Org A: 85% and 45% -> avg 65%, 1 passed out of 2 -> 50%)
        self.assertEqual(analytics["submitted_exam_attempts"], 2)
        self.assertEqual(analytics["avg_exam_score"], 65.0)
        self.assertEqual(analytics["passed_exam_attempts"], 1)
        self.assertEqual(analytics["pass_rate"], 50.0)

        # Verify Org B data is strictly excluded (Org B has 1 student and 1 exam score 95%)
        self.assertNotEqual(analytics["total_students"], 3)
        self.assertNotEqual(analytics["avg_exam_score"], 75.0)

        # Check chart payloads
        self.assertTrue(analytics["charts"]["assignment_status"]["has_data"])
        self.assertTrue(analytics["charts"]["section_distribution"]["has_data"])
        self.assertEqual(len(analytics["charts"]["section_distribution"]["labels"]), 2)

    # ========================================================
    # 3. Teacher Analytics Tests (Strict Scoping & Isolation)
    # ========================================================
    def test_teacher_analytics_strictly_scoped_to_assigned_sections(self):
        # Teacher A1 is assigned to Section A (student_a1) only
        analytics_t1 = get_teacher_analytics(self.org_a, self.teacher_a1, date_range="30d")

        self.assertEqual(analytics_t1["assigned_sections_count"], 1)
        self.assertEqual(analytics_t1["total_section_students"], 1)
        self.assertEqual(analytics_t1["section_resources_count"], 1)

        # Teacher A1 created 2 assignments (1 completed, 1 overdue)
        self.assertEqual(analytics_t1["total_teacher_assignments"], 2)
        self.assertEqual(analytics_t1["completed_assignments"], 1)
        self.assertEqual(analytics_t1["overdue_assignments"], 1)
        self.assertEqual(analytics_t1["completion_rate"], 50.0)

        # Exam performance in Teacher A1's section: only student_a1's score (85%), passed 100%
        self.assertEqual(analytics_t1["student_exams_attempted"], 1)
        self.assertEqual(analytics_t1["avg_student_exam_score"], 85.0)
        self.assertEqual(analytics_t1["student_pass_rate"], 100.0)

        # Teacher A2 is assigned to Section B (student_a2) only
        analytics_t2 = get_teacher_analytics(self.org_a, self.teacher_a2, date_range="30d")

        self.assertEqual(analytics_t2["assigned_sections_count"], 1)
        self.assertEqual(analytics_t2["total_section_students"], 1)
        self.assertEqual(analytics_t2["total_teacher_assignments"], 1)
        self.assertEqual(analytics_t2["completed_assignments"], 0)

        # Exam performance in Teacher A2's section: only student_a2's score (45%), passed 0%
        self.assertEqual(analytics_t2["student_exams_attempted"], 1)
        self.assertEqual(analytics_t2["avg_student_exam_score"], 45.0)
        self.assertEqual(analytics_t2["student_pass_rate"], 0.0)

        # Verify Teacher A1 never sees Student A2's failure or Section B's roster
        student_names_t1 = [r.student.user.username for r in analytics_t1["student_roster"]]
        self.assertIn("student_a1", student_names_t1)
        self.assertNotIn("student_a2", student_names_t1)

    # ========================================================
    # 4. Student Analytics Tests (Strict Individual Privacy)
    # ========================================================
    def test_student_analytics_strictly_individual_and_private(self):
        # Student A1 analytics
        analytics_s1 = get_student_analytics(self.org_a, self.student_a1)

        self.assertEqual(analytics_s1["total_assignments"], 2)
        self.assertEqual(analytics_s1["completed_assignments"], 1)
        self.assertEqual(analytics_s1["overdue_count"], 1)
        self.assertEqual(analytics_s1["completion_rate"], 50.0)

        # Student A1's exam score: only 85%
        self.assertEqual(analytics_s1["submitted_attempts"], 1)
        self.assertEqual(analytics_s1["avg_score"], 85.0)
        self.assertEqual(analytics_s1["passed_count"], 1)

        # Score progression chart
        self.assertTrue(analytics_s1["charts"]["score_progression"]["has_data"])
        self.assertEqual(analytics_s1["charts"]["score_progression"]["scores"], [85.0])

        # Student A2 analytics
        analytics_s2 = get_student_analytics(self.org_a, self.student_a2)
        self.assertEqual(analytics_s2["submitted_attempts"], 1)
        self.assertEqual(analytics_s2["avg_score"], 45.0)
        self.assertEqual(analytics_s2["passed_count"], 0)
        self.assertEqual(analytics_s2["charts"]["score_progression"]["scores"], [45.0])

        # Verify Student A1 cannot see Student A2's scores
        self.assertNotIn(45.0, analytics_s1["charts"]["score_progression"]["scores"])

    # ========================================================
    # 5. Zero-State Handling (Empty Organization)
    # ========================================================
    def test_empty_organization_zero_state_resilience(self):
        empty_org = Organization.objects.create(name="Empty Academy", slug="empty-academy", is_active=True)
        empty_admin = User.objects.create_user(username="empty_admin", password="password123")
        OrganizationMember.objects.create(organization=empty_org, user=empty_admin, role=OrganizationRole.ORG_ADMIN, is_active=True)

        analytics = get_admin_analytics(empty_org, date_range="30d")

        self.assertEqual(analytics["total_students"], 0)
        self.assertEqual(analytics["total_assignments"], 0)
        self.assertEqual(analytics["completion_rate"], 0.0)
        self.assertEqual(analytics["submitted_exam_attempts"], 0)
        self.assertEqual(analytics["avg_exam_score"], None)
        self.assertEqual(analytics["pass_rate"], 0.0)
        self.assertFalse(analytics["charts"]["enrollment_trends"]["has_data"])
        self.assertFalse(analytics["charts"]["assignment_status"]["has_data"])

        # Empty teacher
        empty_teacher = User.objects.create_user(username="empty_teacher", password="password123")
        OrganizationMember.objects.create(organization=empty_org, user=empty_teacher, role=OrganizationRole.STAFF, is_active=True)
        t_analytics = get_teacher_analytics(empty_org, empty_teacher, date_range="30d")
        self.assertEqual(t_analytics["assigned_sections_count"], 0)
        self.assertEqual(t_analytics["total_section_students"], 0)
        self.assertEqual(t_analytics["completion_rate"], 0.0)

        # Empty student
        empty_student = User.objects.create_user(username="empty_student", password="password123")
        OrganizationMember.objects.create(organization=empty_org, user=empty_student, role=OrganizationRole.STUDENT, is_active=True)
        s_analytics = get_student_analytics(empty_org, empty_student)
        self.assertEqual(s_analytics["total_assignments"], 0)
        self.assertEqual(s_analytics["completion_rate"], 0.0)
        self.assertEqual(s_analytics["submitted_attempts"], 0)
        self.assertFalse(s_analytics["charts"]["score_progression"]["has_data"])

    # ========================================================
    # 6. HTTP View & Permission Integration Tests
    # ========================================================
    def test_dashboard_views_render_analytics_with_role_authorization(self):
        client = Client()

        # Admin accessing Admin Dashboard -> 200 OK with analytics
        client.force_login(self.admin_a)
        url_admin = reverse("organizations_admin:dashboard", kwargs={"slug": self.org_a.slug})
        res = client.get(f"{url_admin}?range=90d")
        self.assertEqual(res.status_code, 200)
        self.assertIn("analytics", res.context)
        self.assertEqual(res.context["active_range"], "90d")
        self.assertContains(res, "Institutional Analytics &amp; Visual Intelligence")
        self.assertContains(res, "admin-analytics-data")

        # Teacher accessing Teacher Dashboard -> 200 OK with analytics
        client.force_login(self.teacher_a1)
        url_teacher = reverse("organizations_admin:teacher_dashboard", kwargs={"slug": self.org_a.slug})
        res_t = client.get(f"{url_teacher}?range=30d")
        self.assertEqual(res_t.status_code, 200)
        self.assertIn("analytics", res_t.context)
        self.assertContains(res_t, "Section Analytics &amp; Student Performance")
        self.assertContains(res_t, "teacher-analytics-data")

        # Student accessing Student Learning Dashboard -> 200 OK with analytics
        client.force_login(self.student_a1)
        url_student = reverse("organizations_public:learning", kwargs={"slug": self.org_a.slug})
        res_s = client.get(url_student)
        self.assertEqual(res_s.status_code, 200)
        self.assertIn("analytics", res_s.context)
        self.assertContains(res_s, "My Learning Progression &amp; Analytics")
        self.assertContains(res_s, "student-analytics-data")

        # Student attempting to access Admin Dashboard -> 403 Forbidden
        res_forbidden = client.get(url_admin)
        self.assertEqual(res_forbidden.status_code, 403)

        # Student attempting to access Teacher Dashboard -> 403 Forbidden
        res_teacher_forbidden = client.get(url_teacher)
        self.assertEqual(res_teacher_forbidden.status_code, 403)
