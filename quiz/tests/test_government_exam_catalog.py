from django.db import IntegrityError
from django.test import TestCase

from quiz.models import (
    ContentVertical,
    Country,
    Exam,
    GovernmentBody,
    GovernmentExamProgram,
    GovernmentExamStage,
    GovernmentExamVersion,
    GovernmentJob,
)


class GovernmentExamCatalogTests(TestCase):
    def setUp(self):
        self.country = Country.objects.create(name="Nepal", code="NPL", slug="nepal")
        self.body = GovernmentBody.objects.create(
            country=self.country,
            name="Public Service Commission",
            code="psc",
            slug="public-service-commission",
        )
        self.vertical = ContentVertical.objects.create(
            name="Government / Competitive Exam",
            code="government-exam",
            vertical_type=ContentVertical.GOVERNMENT_EXAM,
        )

    def test_catalog_hierarchy_reuses_existing_exam_engine(self):
        job = GovernmentJob.objects.create(
            country=self.country,
            government_body=self.body,
            name="Nayab Subba",
            code="nayab-subba",
            slug="nayab-subba",
        )
        program = GovernmentExamProgram.objects.create(
            country=self.country,
            government_body=self.body,
            content_vertical=self.vertical,
            name="Nayab Subba Recruitment",
            code="nayab-subba-recruitment",
            slug="nayab-subba-recruitment",
        )
        program.jobs.add(job)
        version = GovernmentExamVersion.objects.create(
            program=program,
            version="2026",
            slug="2026",
            status=GovernmentExamVersion.ACTIVE,
        )
        assessment = Exam.objects.create(
            title="Nayab Subba First Paper",
            question_count=10,
            duration_seconds=1800,
            passing_score=70,
            is_published=True,
        )
        stage = GovernmentExamStage.objects.create(
            version=version,
            exam=assessment,
            name="First Paper",
            code="first-paper",
            order=1,
        )

        self.assertEqual(program.jobs.get(), job)
        self.assertEqual(version.stages.get(), stage)
        self.assertEqual(stage.exam, assessment)

    def test_multiple_versions_preserve_history(self):
        program = GovernmentExamProgram.objects.create(
            country=self.country,
            government_body=self.body,
            content_vertical=self.vertical,
            name="Civil Service",
            code="civil-service",
            slug="civil-service",
        )
        first = GovernmentExamVersion.objects.create(program=program, version="2026", slug="2026")
        second = GovernmentExamVersion.objects.create(program=program, version="2027", slug="2027")
        assessment = Exam.objects.create(title="Civil Service Paper", question_count=10, duration_seconds=1800)
        GovernmentExamStage.objects.create(version=first, exam=assessment, name="Paper I", code="paper-i", order=1)
        GovernmentExamStage.objects.create(version=second, exam=assessment, name="Paper I", code="paper-i", order=1)

        self.assertEqual(program.versions.count(), 2)
        self.assertEqual(first.stages.count(), 1)
        self.assertEqual(second.stages.count(), 1)

    def test_body_code_is_unique_only_within_country(self):
        other = Country.objects.create(name="India", code="IND", slug="india")
        GovernmentBody.objects.create(country=other, name="Public Service Commission", code="psc", slug="public-service-commission")

        with self.assertRaises(IntegrityError):
            GovernmentBody.objects.create(
                country=self.country,
                name="Duplicate Body Code",
                code="psc",
                slug="duplicate-body-code",
            )
