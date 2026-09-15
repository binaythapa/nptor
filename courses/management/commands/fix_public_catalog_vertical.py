from django.core.management.base import BaseCommand
from django.db import transaction

from quiz.models import ContentVertical, Domain


PREFIX = "[PUBLIC DEMO]"


class Command(BaseCommand):
    help = "Classify the seeded public catalog as professional-certification content."

    @transaction.atomic
    def handle(self, *args, **options):
        vertical, _ = ContentVertical.objects.update_or_create(
            vertical_type=ContentVertical.PROFESSIONAL_CERTIFICATION,
            defaults={
                "name": "Professional Certification",
                "code": "professional-certification",
                "is_active": True,
            },
        )
        domains = Domain.objects.filter(
            name__startswith=f"{PREFIX} ",
            organization__isnull=True,
        )
        updated = domains.update(content_vertical=vertical)
        self.stdout.write(
            self.style.SUCCESS(
                f"Classified {updated} public demo domains as Professional Certification."
            )
        )
