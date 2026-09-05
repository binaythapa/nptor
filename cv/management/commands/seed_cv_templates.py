from django.core.management.base import BaseCommand

from cv.models_template import CVTemplate


TEMPLATES = [
    ("ats-classic", "ATS Classic", "Clean, ATS-friendly single-column layout."),
    ("modern-professional", "Modern Professional", "Contemporary professional layout with restrained visual hierarchy."),
    ("executive", "Executive", "Leadership-focused layout for senior professionals."),
    ("technical", "Technical", "Skills and project-focused layout for technical roles."),
    ("fresher", "Fresher", "Entry-level layout emphasizing education, skills, and projects."),
    ("academic", "Academic", "Academic-oriented layout for education and research profiles."),
    ("government", "Government", "Formal layout suited to government and public-sector applications."),
    ("minimal", "Minimal", "Simple typography-first layout with minimal decoration."),
]


class Command(BaseCommand):
    help = "Create or update the default NPTOR CV templates."

    def handle(self, *args, **options):
        for slug, name, description in TEMPLATES:
            CVTemplate.objects.update_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "description": description,
                    "config": {"template_version": 1},
                    "is_active": True,
                },
            )

        self.stdout.write(
            self.style.SUCCESS(f"Seeded {len(TEMPLATES)} CV templates.")
        )
