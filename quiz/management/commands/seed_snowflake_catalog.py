from django.core.management.base import BaseCommand
from django.db import transaction

from quiz.models import (
    Category,
    Choice,
    Domain,
    Exam,
    ExamCategoryAllocation,
    ExamTrack,
    Question,
    TrackExam,
)

PREFIX = "Snowflake | "

CATEGORIES = [
    ("architecture", "Architecture & Platform"),
    ("storage", "Storage & Data Organization"),
    ("compute", "Compute & Performance"),
    ("security", "Security & Governance"),
    ("ingestion", "Data Loading & Pipelines"),
    ("sql", "SQL & Data Transformation"),
    ("sharing", "Sharing & Collaboration"),
]

QUESTIONS = [
    ("architecture", "Which Snowflake layer handles query parsing, optimization, and metadata services?", ["Cloud Services", "Virtual Warehouse", "Database Storage", "External Stage"], 0, Question.EASY),
    ("architecture", "What architectural property lets Snowflake scale compute independently of storage?", ["Separate compute and storage layers", "One server per table", "Local database files", "Warehouse-owned storage"], 0, Question.MEDIUM),
    ("architecture", "Which object supplies compute resources for executing Snowflake SQL?", ["Virtual warehouse", "Database", "Schema", "Stage"], 0, Question.EASY),
    ("storage", "What is a Snowflake micro-partition?", ["A contiguous unit of table data managed by Snowflake", "A warehouse cluster", "A user role", "A network rule"], 0, Question.EASY),
    ("storage", "Which feature provides access to historical table data within its retention period?", ["Time Travel", "Resource Monitor", "Network Policy", "Snowpipe"], 0, Question.EASY),
    ("storage", "What is the main benefit of zero-copy cloning?", ["A logical copy can initially share underlying storage", "It doubles warehouse capacity", "It disables retention", "It exports CSV files"], 0, Question.MEDIUM),
    ("compute", "Which warehouse setting can automatically stop idle compute after a configured period?", ["Auto-suspend", "Time Travel", "Clustering", "Masking policy"], 0, Question.EASY),
    ("compute", "When are multi-cluster warehouses particularly useful?", ["When concurrent workloads cause queuing", "When users need passwords", "When tables need schemas", "When stages need URLs"], 0, Question.MEDIUM),
    ("compute", "What is a common reason to resize a virtual warehouse?", ["To provide more compute resources per cluster", "To increase table retention", "To create roles", "To change file formats"], 0, Question.EASY),
    ("security", "Which access-control model is central to Snowflake privilege management?", ["Role-based access control", "DNS-based access control", "Filesystem ACLs only", "Warehouse-only access"], 0, Question.EASY),
    ("security", "What does a row access policy determine?", ["Which rows a consumer can access", "Which warehouse starts", "Which files upload", "Which database is cloned"], 0, Question.MEDIUM),
    ("security", "What does a masking policy primarily control?", ["How sensitive column values are displayed", "Warehouse size", "Stage location", "Query scheduling"], 0, Question.MEDIUM),
    ("ingestion", "Which command loads files from a stage into a Snowflake table?", ["COPY INTO", "PUT", "GET", "GRANT"], 0, Question.EASY),
    ("ingestion", "What is Snowpipe designed to provide?", ["Continuous or near-real-time file ingestion", "Warehouse resizing", "Role creation", "Dashboard rendering"], 0, Question.EASY),
    ("ingestion", "Which Snowflake object can execute SQL or procedures on a schedule or condition?", ["Task", "Role", "Stage", "File format"], 0, Question.EASY),
    ("sql", "Which SQL statement can update matching rows and insert nonmatching rows?", ["MERGE", "COPY", "PUT", "GRANT"], 0, Question.EASY),
    ("sql", "Which Snowflake data type is commonly used for semi-structured JSON data?", ["VARIANT", "BOOLEAN", "NUMBER", "DATE"], 0, Question.EASY),
    ("sql", "Which SQL feature is appropriate for calculating a running total while retaining row-level detail?", ["Window function", "DDL statement", "Network policy", "Stage definition"], 0, Question.MEDIUM),
    ("sharing", "What is a key benefit of Snowflake Secure Data Sharing?", ["Governed sharing without copying shared data into the consumer account", "Mandatory CSV exports", "Disabling RBAC", "Moving data to local disks"], 0, Question.EASY),
    ("architecture", "Which Snowflake object logically organizes schemas?", ["Database", "Warehouse", "Role", "Task"], 0, Question.EASY),
]


class Command(BaseCommand):
    help = "Seed an idempotent SnowPro Core reusable question bank and practice exam."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Remove this command's Snowflake seed records first.")

    @transaction.atomic
    def handle(self, *args, **options):
        if options["reset"]:
            self.reset()

        domain, _ = Domain.objects.update_or_create(
            organization=None,
            slug="snowflake",
            defaults={"name": "Snowflake", "is_active": True},
        )
        categories = self.seed_categories(domain)
        questions = self.seed_questions(categories)
        exam = self.seed_exam(categories)
        track = self.seed_track(exam)

        self.stdout.write(self.style.SUCCESS("SnowPro Core seed completed."))
        self.stdout.write(f"Domain: {domain.name}")
        self.stdout.write(f"Categories: {len(categories)} | Questions: {len(questions)}")
        self.stdout.write(f"Exam: {exam.title} | Track: {track.title}")

    def reset(self):
        TrackExam.objects.filter(track__slug="snowflake-snowpro-core").delete()
        ExamTrack.objects.filter(slug="snowflake-snowpro-core").delete()
        ExamCategoryAllocation.objects.filter(exam__title=f"{PREFIX}SnowPro Core Practice Exam").delete()
        Exam.objects.filter(title=f"{PREFIX}SnowPro Core Practice Exam").delete()
        Question.objects.filter(text__startswith=PREFIX).delete()
        Category.objects.filter(slug__startswith="snowflake-").delete()
        Domain.objects.filter(slug="snowflake", organization=None).delete()

    def seed_categories(self, domain):
        return {
            slug: Category.objects.update_or_create(
                organization=None,
                slug=f"snowflake-{slug}",
                defaults={"name": name, "domain": domain, "parent": None, "is_active": True},
            )[0]
            for slug, name in CATEGORIES
        }

    def seed_questions(self, categories):
        questions = []
        for category_slug, text, options, correct_index, difficulty in QUESTIONS:
            question, _ = Question.objects.update_or_create(
                text=f"{PREFIX}{text}",
                defaults={
                    "primary_category": categories[category_slug],
                    "question_type": Question.SINGLE,
                    "difficulty": difficulty,
                    "is_active": True,
                    "is_deleted": False,
                    "explanation": "Original NPTOR educational content; not an official Snowflake certification question.",
                },
            )
            question.categories.set([categories[category_slug]])
            Choice.objects.filter(question=question).delete()
            Choice.objects.bulk_create([
                Choice(question=question, text=choice, is_correct=index == correct_index, order=index)
                for index, choice in enumerate(options)
            ])
            questions.append(question)
        return questions

    def seed_exam(self, categories):
        exam, _ = Exam.objects.update_or_create(
            title=f"{PREFIX}SnowPro Core Practice Exam",
            defaults={
                "question_count": len(QUESTIONS),
                "duration_seconds": 3600,
                "level": 1,
                "passing_score": 70,
                "is_published": True,
                "max_mock_attempts": 3,
                "allow_review": True,
            },
        )
        exam.categories.set(categories.values())
        ExamCategoryAllocation.objects.filter(exam=exam).delete()
        for slug, _ in CATEGORIES:
            ExamCategoryAllocation.objects.create(
                exam=exam,
                category=categories[slug],
                fixed_count=sum(1 for question in QUESTIONS if question[0] == slug),
                include_descendants=True,
            )
        return exam

    def seed_track(self, exam):
        track, _ = ExamTrack.objects.update_or_create(
            organization=None,
            slug="snowflake-snowpro-core",
            defaults={
                "title": f"{PREFIX}SnowPro Core Preparation Track",
                "description": "Reusable preparation track for SnowPro Core practice and future learning content.",
                "subscription_scope": ExamTrack.TRACK,
                "pricing_type": ExamTrack.PRICING_FREE,
                "currency": "INR",
                "is_active": True,
            },
        )
        TrackExam.objects.update_or_create(
            track=track,
            exam=exam,
            defaults={"order": 1, "is_required": True},
        )
        return track
