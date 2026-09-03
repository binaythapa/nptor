from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from quiz.models import Category, Choice, Domain, Exam, ExamCategoryAllocation, ExamTrack, Question


SEED_PREFIX = "[SEED]"


class Command(BaseCommand):
    help = "Create deterministic demo data for local/testing environments."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Remove previously generated seed records before recreating them.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["reset"]:
            self._reset()

        domains = self._domains()
        categories = self._categories(domains)
        questions = self._questions(categories)
        tracks = self._tracks()
        exams = self._exams(tracks, categories)

        self.stdout.write(self.style.SUCCESS("Seed data created successfully."))
        self.stdout.write(f"Domains: {len(domains)}")
        self.stdout.write(f"Categories: {len(categories)}")
        self.stdout.write(f"Questions: {len(questions)}")
        self.stdout.write(f"Choices: {Choice.objects.filter(question__in=questions).count()}")
        self.stdout.write(f"Tracks: {len(tracks)}")
        self.stdout.write(f"Exams: {len(exams)}")
        self.stdout.write(
            f"Allocations: {ExamCategoryAllocation.objects.filter(exam__in=exams).count()}"
        )

    def _reset(self):
        ExamCategoryAllocation.objects.filter(exam__title__startswith=SEED_PREFIX).delete()
        Exam.objects.filter(title__startswith=SEED_PREFIX).delete()
        ExamTrack.objects.filter(title__startswith=SEED_PREFIX).delete()
        Question.objects.filter(text__startswith=SEED_PREFIX).delete()
        Category.objects.filter(name__startswith=SEED_PREFIX).delete()
        Domain.objects.filter(name__startswith=SEED_PREFIX).delete()

    def _domains(self):
        data = [
            ("AWS Cloud", "aws-cloud"),
            ("Snowflake", "snowflake"),
            ("Azure", "azure"),
        ]
        return [
            Domain.objects.update_or_create(
                slug=slug,
                defaults={"name": f"{SEED_PREFIX} {name}", "is_active": True},
            )[0]
            for name, slug in data
        ]

    def _categories(self, domains):
        specs = [
            (domains[0], "Compute", "compute"),
            (domains[0], "Storage", "storage"),
            (domains[0], "IAM", "iam"),
            (domains[1], "Virtual Warehouses", "virtual-warehouses"),
            (domains[1], "Data Loading", "data-loading"),
            (domains[1], "Time Travel", "time-travel"),
            (domains[2], "Data Factory", "data-factory"),
            (domains[2], "Storage", "azure-storage"),
        ]
        result = []
        for domain, name, slug in specs:
            category, _ = Category.objects.update_or_create(
                slug=slug,
                organization=None,
                defaults={
                    "name": f"{SEED_PREFIX} {name}",
                    "domain": domain,
                    "is_active": True,
                    "parent": None,
                },
            )
            result.append(category)
        return result

    def _questions(self, categories):
        bank = [
            (categories[0], "Which AWS service provides resizable compute capacity?", ["EC2", "S3", "IAM", "Route 53"], 0, Question.EASY),
            (categories[0], "Which EC2 pricing option is best suited to a predictable long-term workload?", ["On-Demand", "Reserved Instances", "Spot Instances", "Dedicated Hosts"], 1, Question.MEDIUM),
            (categories[1], "Which AWS service is object storage?", ["S3", "EBS", "EFS", "RDS"], 0, Question.EASY),
            (categories[2], "Which AWS service manages identities and permissions?", ["IAM", "CloudFront", "Lambda", "SQS"], 0, Question.EASY),
            (categories[3], "What does a Snowflake virtual warehouse primarily provide?", ["Compute resources", "Object storage", "DNS", "User authentication"], 0, Question.EASY),
            (categories[3], "What happens when a Snowflake warehouse is suspended?", ["Compute stops and resumes on demand", "Data is deleted", "The database is dropped", "All users are logged out"], 0, Question.MEDIUM),
            (categories[4], "Which Snowflake command loads staged files into a table?", ["COPY INTO", "PUT", "GET", "MERGE"], 0, Question.EASY),
            (categories[5], "What does Snowflake Time Travel allow?", ["Accessing historical table data", "Increasing warehouse size", "Changing account passwords", "Creating network rules"], 0, Question.EASY),
            (categories[6], "Which Azure service is commonly used to orchestrate data movement pipelines?", ["Azure Data Factory", "Azure DNS", "Azure Front Door", "Azure Monitor"], 0, Question.EASY),
            (categories[7], "Which Azure service provides managed object/blob storage?", ["Azure Blob Storage", "Azure SQL Database", "Azure Functions", "Azure Key Vault"], 0, Question.EASY),
        ]
        result = []
        for category, text, choices, correct, difficulty in bank:
            question, _ = Question.objects.update_or_create(
                text=f"{SEED_PREFIX} {text}",
                defaults={
                    "primary_category": category,
                    "question_type": Question.SINGLE,
                    "difficulty": difficulty,
                    "is_active": True,
                    "is_deleted": False,
                    "explanation": "Seed question for application testing.",
                },
            )
            question.categories.set([category])
            Choice.objects.filter(question=question).delete()
            Choice.objects.bulk_create([
                Choice(question=question, text=choice, is_correct=(i == correct), order=i)
                for i, choice in enumerate(choices)
            ])
            result.append(question)
        return result

    def _tracks(self):
        specs = [
            ("AWS SAA-C03", "aws-saa-c03"),
            ("SnowPro Core", "snowpro-core"),
            ("Azure Fundamentals", "azure-fundamentals"),
        ]
        return [
            ExamTrack.objects.update_or_create(
                slug=slug,
                organization=None,
                defaults={
                    "title": f"{SEED_PREFIX} {title}",
                    "description": "Seed track for application testing.",
                    "subscription_scope": ExamTrack.TRACK,
                    "pricing_type": ExamTrack.PRICING_FREE,
                    "currency": "INR",
                    "is_active": True,
                },
            )[0]
            for title, slug in specs
        ]

    def _exams(self, tracks, categories):
        specs = [
            (tracks[0], categories[0], "AWS SAA Practice Exam", 4),
            (tracks[1], categories[3], "SnowPro Core Practice Exam", 4),
            (tracks[2], categories[6], "Azure Fundamentals Practice Exam", 2),
        ]
        result = []
        for track, category, title, count in specs:
            exam, _ = Exam.objects.update_or_create(
                title=f"{SEED_PREFIX} {title}",
                defaults={
                    "track": track,
                    "primary_category": category,
                    "question_count": count,
                    "duration_seconds": 1800,
                    "level": 1,
                    "passing_score": 50,
                    "is_free": True,
                    "price": None,
                    "currency": "INR",
                    "is_published": True,
                    "max_mock_attempts": 3,
                    "allow_review": True,
                },
            )
            exam.categories.set([category])
            ExamCategoryAllocation.objects.update_or_create(
                exam=exam,
                category=category,
                defaults={
                    "fixed_count": count,
                    "percentage": None,
                    "include_descendants": True,
                },
            )
            result.append(exam)
        return result
