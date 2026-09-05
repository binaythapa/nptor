from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Seed the complete professional-certification, government-exam, and academic/entrance catalog."

    def handle(self, *args, **options):
        self.stdout.write("Seeding professional certification catalog...")
        call_command("seed_snowflake_catalog")
        self.stdout.write("Seeding government exam catalog...")
        call_command("seed_government_catalog")
        self.stdout.write("Seeding academic and entrance preparation catalog...")
        call_command("seed_preparation_programs")
        self.stdout.write(self.style.SUCCESS("NPTOR catalog seeded successfully."))
