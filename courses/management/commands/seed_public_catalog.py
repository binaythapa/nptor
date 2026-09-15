from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from courses.models import Course
from quiz.models import Category, Domain, Exam, ExamTrack, TrackExam


PREFIX = "[PUBLIC DEMO]"

COURSES = [
    {
        "slug": "public-python-programming-fundamentals",
        "title": "Python Programming Fundamentals",
        "description": "Learn Python syntax, data types, control flow, functions, and practical problem-solving from the ground up.",
        "level": "beginner",
        "domain": "Programming",
        "category": "Python Programming",
    },
    {
        "slug": "public-data-analysis-with-python",
        "title": "Data Analysis with Python",
        "description": "Build a practical foundation in Python data analysis, including pandas, data cleaning, exploration, and reporting.",
        "level": "intermediate",
        "domain": "Data & Analytics",
        "category": "Data Analysis",
    },
    {
        "slug": "public-sql-database-fundamentals",
        "title": "SQL & Database Fundamentals",
        "description": "Understand relational databases and master practical SQL queries for filtering, joining, aggregating, and analyzing data.",
        "level": "beginner",
        "domain": "Data & Analytics",
        "category": "SQL & Databases",
    },
    {
        "slug": "public-cloud-computing-fundamentals",
        "title": "Cloud Computing Fundamentals",
        "description": "Explore core cloud concepts, service models, deployment models, security basics, scalability, and modern cloud architecture.",
        "level": "beginner",
        "domain": "Cloud Computing",
        "category": "Cloud Fundamentals",
    },
]

TRACKS = [
    {
        "slug": "public-python-assessment-track",
        "title": "Python Assessment Track",
        "description": "A reusable public assessment track for Python programming fundamentals.",
    },
    {
        "slug": "public-data-analytics-assessment-track",
        "title": "Data Analytics Assessment Track",
        "description": "A reusable public assessment track covering practical data analytics concepts.",
    },
    {
        "slug": "public-sql-assessment-track",
        "title": "SQL Assessment Track",
        "description": "A reusable public assessment track for SQL and relational database skills.",
    },
]

ASSESSMENTS = [
    {
        "slug": "public-python-assessment-track",
        "track_slug": "public-python-assessment-track",
        "category": "Python Programming",
        "titles": [
            "Python Fundamentals Assessment",
            "Python Problem Solving Assessment",
        ],
    },
    {
        "slug": "public-data-analytics-assessment-track",
        "track_slug": "public-data-analytics-assessment-track",
        "category": "Data Analysis",
        "titles": [
            "Data Analysis Fundamentals Assessment",
            "Python Data Analysis Assessment",
        ],
    },
    {
        "slug": "public-sql-assessment-track",
        "track_slug": "public-sql-assessment-track",
        "category": "SQL & Databases",
        "titles": [
            "SQL Fundamentals Assessment",
            "SQL Querying Assessment",
        ],
    },
]


class Command(BaseCommand):
    help = "Seed a small, repeatable set of public platform courses and assessment tracks."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete the seeded public catalog records before recreating them.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["reset"]:
            self._reset()

        self._seed_courses()
        created_exams = self._seed_exams()
        created_tracks = self._seed_tracks()
        self._attach_exams_to_tracks()

        self.stdout.write(
            self.style.SUCCESS(
                f"Public catalog seeded: {len(COURSES)} courses, {len(created_exams)} exams, {len(created_tracks)} tracks."
            )
        )
        self.stdout.write("All seeded resources are platform-owned and publicly available.")
        self.stdout.write("No organization ownership, subscriptions, payments, or entitlements are created.")
        self.stdout.write("Re-run: python manage.py seed_public_catalog")
        self.stdout.write("Reset/recreate: python manage.py seed_public_catalog --reset")

    def _reset(self):
        Course.objects.filter(slug__in=[item["slug"] for item in COURSES]).delete()
        ExamTrack.objects.filter(
            slug__in=[item["slug"] for item in TRACKS],
            organization=None,
        ).delete()
        Exam.objects.filter(
            title__in=[
                f"{PREFIX} {title}"
                for item in ASSESSMENTS
                for title in item["titles"]
            ],
            organization=None,
        ).delete()

        seeded_domains = [
            f"{PREFIX} {item['domain']}" for item in COURSES
        ]
        seeded_categories = [
            f"{PREFIX} {item['category']}" for item in COURSES
        ]
        Category.objects.filter(name__in=seeded_categories, organization=None).delete()
        Domain.objects.filter(name__in=seeded_domains, organization=None).delete()

    def _seed_courses(self):
        courses = []
        for item in COURSES:
            domain = self._domain(item["domain"])
            category = self._category(item["category"], domain)

            course, _ = Course.objects.update_or_create(
                slug=item["slug"],
                defaults={
                    "title": item["title"],
                    "description": item["description"],
                    "category": category,
                    "level": item["level"],
                    "owner_type": Course.OWNER_PLATFORM,
                    "organization": None,
                    "is_public": True,
                    "is_published": True,
                    "approval_status": Course.APPROVAL_APPROVED,
                    "submitted_at": None,
                    "reviewed_at": None,
                    "reviewed_by": None,
                    "review_notes": "Seeded public platform catalog resource.",
                    "created_by": None,
                },
            )
            courses.append(course)
        return courses

    def _seed_exams(self):
        exams = []
        categories = {
            item["category"]: self._category_for_name(item["category"])
            for item in COURSES
        }
        for assessment in ASSESSMENTS:
            category = categories[assessment["category"]]
            for title in assessment["titles"]:
                exam, _ = Exam.objects.update_or_create(
                    title=f"{PREFIX} {title}",
                    organization=None,
                    defaults={
                        "question_count": 10,
                        "duration_seconds": 1800,
                        "level": 1,
                        "passing_score": 50.0,
                        "is_published": True,
                        "max_mock_attempts": 3,
                        "allow_review": True,
                        "created_by": None,
                    },
                )
                exam.categories.set([category])
                exams.append(exam)
        return exams

    def _seed_tracks(self):
        tracks = []
        for item in TRACKS:
            track, _ = ExamTrack.objects.update_or_create(
                slug=item["slug"],
                organization=None,
                defaults={
                    "title": item["title"],
                    "description": item["description"],
                    "subscription_scope": ExamTrack.TRACK,
                    "pricing_type": ExamTrack.PRICING_FREE,
                    "monthly_price": None,
                    "lifetime_price": None,
                    "trial_days": 0,
                    "currency": "INR",
                    "is_active": True,
                },
            )
            tracks.append(track)
        return tracks

    def _attach_exams_to_tracks(self):
        exams_by_track = {}
        for assessment in ASSESSMENTS:
            exams_by_track[assessment["track_slug"]] = list(
                Exam.objects.filter(
                    organization=None,
                    title__in=[f"{PREFIX} {title}" for title in assessment["titles"]],
                    is_published=True,
                ).order_by("id")
            )

        for track in ExamTrack.objects.filter(
            slug__in=exams_by_track,
            organization=None,
        ):
            for order, exam in enumerate(exams_by_track[track.slug], start=1):
                TrackExam.objects.update_or_create(
                    track=track,
                    exam=exam,
                    defaults={"order": order, "is_required": True},
                )

    def _domain(self, name):
        domain, _ = Domain.objects.update_or_create(
            slug=slugify(f"public-{name}"),
            organization=None,
            defaults={
                "name": f"{PREFIX} {name}",
                "is_active": True,
            },
        )
        return domain

    def _category(self, name, domain):
        category, _ = Category.objects.update_or_create(
            slug=slugify(f"public-{name}"),
            organization=None,
            defaults={
                "name": f"{PREFIX} {name}",
                "domain": domain,
                "parent": None,
                "is_active": True,
            },
        )
        return category

    def _category_for_name(self, name):
        item = next(course for course in COURSES if course["category"] == name)
        domain = Domain.objects.get(
            slug=slugify(f"public-{item['domain']}"),
            organization=None,
        )
        return Category.objects.get(
            slug=slugify(f"public-{name}"),
            organization=None,
            domain=domain,
        )
