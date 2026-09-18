from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Seed the Nepal Lok Sewa Nayab Subba government exam."

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.WARNING(
                "Seed implementation requires confirmation of the project's question and category schemas."
            )
        )
