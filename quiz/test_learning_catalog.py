from django.contrib.auth import get_user_model
from django.test import TestCase

from courses.models import Course
from quiz.models import Category, Domain, Exam, ExamTrack
from quiz.services.learning_catalog import build_learning_catalog


User = get_user_model()


class LearningCatalogServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="learning-catalog-user", password="test-password")
        self.snowflake = Domain.objects.create(name="Snowflake", slug="snowflake", is_active=True)
        self.aws = Domain.objects.create(name="AWS", slug="aws", is_active=True)
        self.snowflake_category = Category.objects.create(name="Snowflake Core", slug="snowflake-core", domain=self.snowflake, is_active=True)
        self.aws_category = Category.objects.create(name="AWS Core", slug="aws-core", domain=self.aws, is_active=True)

    def test_builds_active_domains_and_derives_course_exam_and_track_domains(self):
        course = Course.objects.create(title="Snowflake Fundamentals", description="Learn Snowflake.", category=self.snowflake_category, level="beginner", is_public=True, is_published=True, approval_status=Course.APPROVAL_APPROVED)
        track = ExamTrack.objects.create(title="SnowPro Core Track", slug="snowpro-core", is_active=True)
        exam = Exam.objects.create(title="Snowflake Core Exam", track=track, primary_category=self.snowflake_category, question_count=10, duration_seconds=1800, is_published=True, is_free=True)
        Exam.objects.create(title="AWS Exam", primary_category=self.aws_category, question_count=10, duration_seconds=1800, is_published=True, is_free=True)

        catalog = build_learning_catalog(user=self.user)
        domains = {item["domain"].slug: item for item in catalog["domains"]}

        self.assertEqual(set(domains), {"aws", "snowflake"})
        self.assertEqual(domains["snowflake"]["course_count"], 1)
        self.assertEqual(domains["snowflake"]["exam_count"], 1)
        self.assertEqual(domains["snowflake"]["track_count"], 1)
        self.assertIn(course.id, domains["snowflake"]["course_ids"])
        self.assertIn(exam.id, domains["snowflake"]["exam_ids"])
        self.assertIn(track.id, domains["snowflake"]["track_ids"])

    def test_excludes_inactive_domains_and_non_public_resources(self):
        inactive = Domain.objects.create(name="Legacy", slug="legacy", is_active=False)
        inactive_category = Category.objects.create(name="Legacy Core", slug="legacy-core", domain=inactive)
        Course.objects.create(title="Visible AWS", description="Visible.", category=self.aws_category, level="beginner", is_public=True, is_published=True, approval_status=Course.APPROVAL_APPROVED)
        Course.objects.create(title="Draft Snowflake", description="Hidden.", category=self.snowflake_category, level="beginner", is_public=False, is_published=False, approval_status=Course.APPROVAL_DRAFT)
        Exam.objects.create(title="Legacy Exam", primary_category=inactive_category, question_count=10, duration_seconds=1800, is_published=True, is_free=True)

        catalog = build_learning_catalog(user=self.user)

        self.assertEqual([item["domain"].slug for item in catalog["domains"]], ["aws"])
        self.assertTrue(all(item["domain"].slug != "legacy" for item in catalog["domains"]))
        self.assertNotIn("Draft Snowflake", [item["resource"].title for item in catalog["resources"]])

    def test_search_and_pagination_are_server_side(self):
        for index in range(15):
            Exam.objects.create(title=f"Snowflake Practice {index}", primary_category=self.snowflake_category, question_count=10, duration_seconds=1800, is_published=True, is_free=True)

        catalog = build_learning_catalog(user=self.user, query="Snowflake Practice", resource_type="exams", per_page=5, page=2)

        self.assertEqual(catalog["page_obj"].paginator.count, 15)
        self.assertEqual(len(catalog["resources"]), 5)
        self.assertEqual(catalog["page_obj"].number, 2)
        self.assertTrue(all(item["type"] == "exam" for item in catalog["resources"]))

    def test_pricing_filter_separates_free_and_premium_resources(self):
        Exam.objects.create(title="Free AWS Practice", primary_category=self.aws_category, question_count=10, duration_seconds=1800, is_published=True, is_free=True)
        Exam.objects.create(title="Premium AWS Practice", primary_category=self.aws_category, question_count=20, duration_seconds=3600, is_published=True, is_free=False, price=499, currency="INR")

        free_catalog = build_learning_catalog(user=self.user, resource_type="exams", pricing="free")
        premium_catalog = build_learning_catalog(user=self.user, resource_type="exams", pricing="premium")

        self.assertEqual([item["resource"].title for item in free_catalog["resources"]], ["Free AWS Practice"])
        self.assertEqual([item["resource"].title for item in premium_catalog["resources"]], ["Premium AWS Practice"])
