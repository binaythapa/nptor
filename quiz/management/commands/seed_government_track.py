from django.core.management.base import CommandError, BaseCommand
from django.db import transaction

from quiz.models import Exam, ExamTrack, TrackExam


class Command(BaseCommand):
    help = "Seed the Nepal Lok Sewa Nayab Subba government-exam track and attach the sample exam."

    @transaction.atomic
    def handle(self, *args, **options):
        exam = Exam.objects.filter(
            organization=None,
            title="लोक सेवा आयोग – नायब सुब्बा नमुना परीक्षा",
        ).first()
        if exam is None:
            raise CommandError(
                "The Nayab Subba sample exam was not found. "
                "Run seed_government_exam first."
            )

        track, _ = ExamTrack.objects.get_or_create(
            organization=None,
            slug="nayab-subba-preparation-track",
            defaults={
                "title": "नायब सुब्बा परीक्षा तयारी ट्र्याक",
                "description": (
                    "लोक सेवा आयोगको नायब सुब्बा परीक्षाका लागि क्रमिक तयारी "
                    "र नमुना मूल्याङ्कन ट्र्याक।"
                ),
                "subscription_scope": ExamTrack.TRACK,
                "pricing_type": ExamTrack.PRICING_FREE,
                "currency": "NPR",
                "is_active": True,
            },
        )
        track.title = "नायब सुब्बा परीक्षा तयारी ट्र्याक"
        track.description = (
            "लोक सेवा आयोगको नायब सुब्बा परीक्षाका लागि क्रमिक तयारी "
            "र नमुना मूल्याङ्कन ट्र्याक।"
        )
        track.subscription_scope = ExamTrack.TRACK
        track.pricing_type = ExamTrack.PRICING_FREE
        track.currency = "NPR"
        track.is_active = True
        track.save()

        track_exam, _ = TrackExam.objects.get_or_create(
            track=track,
            exam=exam,
            defaults={
                "order": 1,
                "is_required": True,
            },
        )
        track_exam.order = 1
        track_exam.is_required = True
        track_exam.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded government track: track_id={track.id}; "
                f"track_exam_id={track_exam.id}; exam_id={exam.id}"
            )
        )
