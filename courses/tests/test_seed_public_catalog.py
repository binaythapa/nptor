from django.core.management import call_command
from django.test import TestCase

from quiz.models import ContentVertical, Domain, Exam, ExamTrack, TrackExam


class SeedPublicCatalogTests(TestCase):
    def test_public_tracks_include_published_public_exams(self):
        call_command("seed_public_catalog")

        tracks = ExamTrack.objects.filter(
            slug__in=[
                "public-python-assessment-track",
                "public-data-analytics-assessment-track",
                "public-sql-assessment-track",
            ],
            organization__isnull=True,
        )

        self.assertEqual(tracks.count(), 3)
        self.assertEqual(TrackExam.objects.filter(track__in=tracks).count(), 6)
        self.assertEqual(
            Exam.objects.filter(
                title__startswith="[PUBLIC DEMO]",
                organization__isnull=True,
                is_published=True,
            ).count(),
            6,
        )

        for track in tracks:
            memberships = TrackExam.objects.filter(track=track).select_related("exam")
            self.assertEqual(memberships.count(), 2)
            for membership in memberships:
                self.assertTrue(membership.exam.is_published)
                self.assertIsNone(membership.exam.organization_id)

    def test_public_catalog_domains_are_classified_for_certifications(self):
        call_command("seed_public_catalog")

        vertical = ContentVertical.objects.get(
            vertical_type=ContentVertical.PROFESSIONAL_CERTIFICATION
        )
        domains = Domain.objects.filter(
            name__startswith="[PUBLIC DEMO] ",
            organization__isnull=True,
        )

        self.assertEqual(domains.count(), 3)
        self.assertTrue(all(domain.content_vertical_id == vertical.id for domain in domains))
