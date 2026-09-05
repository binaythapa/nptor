from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Seed the complete NPTOR development catalog and end-to-end learning data."

    def handle(self, *args, **options):
        self.stdout.write("Seeding professional certification catalog...")
        call_command("seed_snowflake_catalog")
        self.stdout.write("Seeding government exam catalog...")
        call_command("seed_government_catalog")
        self.stdout.write("Seeding academic and entrance preparation catalog...")
        call_command("seed_preparation_programs")
        self.stdout.write("Seeding reusable domains, questions, exams, tracks and courses...")
        call_command("seed_complete_catalog")
        self.stdout.write("Seeding complete-flow question pools and government course lessons...")
        call_command("seed_flow_content")
        self.stdout.write(self.style.SUCCESS("NPTOR complete development catalog seeded successfully."))
