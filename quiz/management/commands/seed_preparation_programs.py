from django.core.management.base import BaseCommand
from django.db import transaction

from quiz.models import ContentVertical, Country, PreparationProgram


PROGRAMS = (
    {
        "name": "MBBS Entrance Preparation",
        "code": "mbbs-entrance",
        "slug": "mbbs-entrance",
        "description": "Original NPTOR preparation catalog for MBBS entrance candidates. Attach subject courses and mock exams through admin.",
    },
    {
        "name": "IOE Entrance Preparation",
        "code": "ioe-entrance",
        "slug": "ioe-entrance",
        "description": "Original NPTOR preparation catalog for IOE entrance candidates. Attach subject courses and mock exams through admin.",
    },
    {
        "name": "Class 11 Entrance Preparation",
        "code": "class-11-entrance",
        "slug": "class-11-entrance",
        "description": "Original NPTOR preparation catalog for Class 11 entrance candidates. Attach school/stream-specific courses and mock exams through admin.",
    },
)


class Command(BaseCommand):
    help = "Seed reusable local academic and entrance preparation programs."

    @transaction.atomic
    def handle(self, *args, **options):
        vertical, _ = ContentVertical.objects.update_or_create(
            vertical_type=ContentVertical.ACADEMIC_EXAM,
            defaults={
                "name": "Academic Exam",
                "code": "academic-exam",
                "is_active": True,
            },
        )
        country, _ = Country.objects.update_or_create(
            code="NPL",
            defaults={
                "name": "Nepal",
                "slug": "nepal",
                "is_active": True,
            },
        )

        for item in PROGRAMS:
            PreparationProgram.objects.update_or_create(
                content_vertical=vertical,
                code=item["code"],
                defaults={
                    "country": country,
                    "name": item["name"],
                    "slug": item["slug"],
                    "description": item["description"],
                    "is_active": True,
                },
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Seeded 3 Nepal academic/entrance preparation programs."
            )
        )
