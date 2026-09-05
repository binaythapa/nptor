from django.core.management.base import BaseCommand
from django.db import transaction

from courses.models import Course, CourseSection, Lesson
from quiz.models import Category, Choice, Difficulty, Domain, Exam, ExamTrack, Question, TrackExam
from subscriptions.models import SubscriptionPlan

VIDEO_URL = "https://www.youtube.com/@Snowflake"
DOCS_URL = "https://docs.snowflake.com/"
PREFIX = "Snowflake | "

CERTS = [
    ("associate-platform", "SnowPro Associate: Platform", "beginner", "architecture"),
    ("core", "SnowPro Core", "intermediate", "architecture"),
    ("advanced-architect", "SnowPro Advanced: Architect", "advanced", "architecture"),
    ("advanced-data-engineer", "SnowPro Advanced: Data Engineer", "advanced", "ingestion"),
    ("advanced-data-scientist", "SnowPro Advanced: Data Scientist", "advanced", "ai-snowpark"),
    ("advanced-administrator", "SnowPro Advanced: Administrator", "advanced", "security"),
    ("advanced-data-analyst", "SnowPro Advanced: Data Analyst", "advanced", "sql"),
]

CATEGORIES = [
    ("architecture", "Architecture & Platform"),
    ("storage", "Storage & Data Organization"),
    ("compute", "Compute & Performance"),
    ("security", "Security & Governance"),
    ("ingestion", "Data Loading & Pipelines"),
    ("sql", "SQL & Data Transformation"),
    ("sharing", "Sharing & Collaboration"),
    ("ai-snowpark", "AI, Apps & Snowpark"),
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
    ("sharing", "What is a key benefit of Snowflake Secure Data Sharing?", ["Governed sharing without copying the shared data into the consumer account", "Mandatory CSV exports", "Disabling RBAC", "Moving data to local disks"], 0, Question.EASY),
    ("ai-snowpark", "What is Snowpark primarily used for?", ["Building data applications and transformations with supported programming languages", "Managing DNS", "Replacing Snowflake storage", "Creating firewall rules"], 0, Question.EASY),
]

class Command(BaseCommand):
    help = "Seed the NPTOR Snowflake certification catalog with free and premium learning content."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Remove this seed's records before recreating them.")

    @transaction.atomic
    def handle(self, *args, **options):
        if options["reset"]:
            self.reset()
        self.plans = self.seed_plans()
        self.domain = Domain.objects.update_or_create(
            slug="snowflake", organization=None,
            defaults={"name": "Snowflake", "is_active": True},
        )[0]
        self.categories = self.seed_categories()
        self.seed_difficulties()
        questions = self.seed_questions()
        exams = self.seed_exams()
        tracks = self.seed_tracks(exams)
        courses = self.seed_courses(exams)
        self.stdout.write(self.style.SUCCESS("Snowflake certification catalog seeded."))
        self.stdout.write(f"Domain: 1 | Categories: {len(self.categories)} | Questions: {len(questions)}")
        self.stdout.write(f"Exams: {len(exams)} | Tracks: {len(tracks)} | Courses: {len(courses)}")
        self.stdout.write("Plans: free, premium monthly INR 999, premium lifetime INR 4999")

    def reset(self):
        Course.objects.filter(slug__startswith="snowflake-").delete()
        ExamTrack.objects.filter(slug__startswith="snowflake-").delete()
        Exam.objects.filter(title__startswith=PREFIX).delete()
        Question.objects.filter(text__startswith=PREFIX).delete()
        Category.objects.filter(slug__startswith="snowflake-").delete()
        Domain.objects.filter(slug="snowflake", organization=None).delete()
        SubscriptionPlan.objects.filter(code__startswith="snowflake-").delete()

    def seed_plans(self):
        specs = [
            ("snowflake-free", "Snowflake Free", "Free introductory Snowflake learning", None, 0),
            ("snowflake-premium-monthly", "Snowflake Premium Monthly", "Full certification preparation", 30, 999),
            ("snowflake-premium-lifetime", "Snowflake Premium Lifetime", "Lifetime certification preparation access", None, 4999),
        ]
        return {
            code: SubscriptionPlan.objects.update_or_create(
                code=code,
                defaults={"name": name, "description": desc, "duration_days": days, "price": price, "currency": "INR", "is_active": True},
            )[0]
            for code, name, desc, days, price in specs
        }

    def seed_categories(self):
        return {
            slug: Category.objects.update_or_create(
                slug=f"snowflake-{slug}", organization=None,
                defaults={"name": name, "domain": self.domain, "parent": None, "is_active": True},
            )[0]
            for slug, name in CATEGORIES
        }

    def seed_difficulties(self):
        for slug, name in (("easy", "Easy"), ("medium", "Medium"), ("hard", "Hard")):
            Difficulty.objects.update_or_create(slug=slug, defaults={"name": name, "is_active": True})

    def seed_questions(self):
        result = []
        for cat_slug, text, options, correct, difficulty in QUESTIONS:
            q, _ = Question.objects.update_or_create(
                text=f"{PREFIX}{text}",
                defaults={
                    "primary_category": self.categories[cat_slug],
                    "question_type": Question.SINGLE,
                    "difficulty": difficulty,
                    "is_active": True,
                    "is_deleted": False,
                    "explanation": "Original NPTOR educational content. Not an official Snowflake certification question.",
                },
            )
            q.categories.set([self.categories[cat_slug]])
            Choice.objects.filter(question=q).delete()
            Choice.objects.bulk_create([
                Choice(question=q, text=value, is_correct=(i == correct), order=i)
                for i, value in enumerate(options)
            ])
            result.append(q)
        return result

    def seed_exams(self):
        result = {}
        for slug, title, level, primary in CERTS:
            result[f"{slug}_sample"] = self.make_exam(
                f"{title} | Free Sample Exam", self.categories[primary], 10, 1, [self.plans["snowflake-free"]]
            )
            result[f"{slug}_mock"] = self.make_exam(
                f"{title} | Full Mock Exam", self.categories[primary], 20, 2 if level == "advanced" else 1,
                [self.plans["snowflake-premium-monthly"], self.plans["snowflake-premium-lifetime"]],
            )
        return result

    def make_exam(self, name, primary, count, level, plans):
        exam, _ = Exam.objects.update_or_create(
            title=f"{PREFIX}{name}",
            defaults={
                "primary_category": primary,
                "question_count": count,
                "duration_seconds": 3600 if count > 10 else 1800,
                "level": level,
                "passing_score": 70,
                "is_published": True,
                "max_mock_attempts": 3,
                "allow_review": True,
            },
        )
        exam.categories.set(list(self.categories.values()))
        exam.subscription_plans.set(plans)
        return exam

    def seed_tracks(self, exams):
        result = []
        for slug, title, _, _ in CERTS:
            track, _ = ExamTrack.objects.update_or_create(
                slug=f"snowflake-{slug}", organization=None,
                defaults={
                    "title": f"{PREFIX}{title} Certification Track",
                    "description": f"NPTOR structured preparation path for {title}, with a free sample and premium full mock assessment.",
                    "subscription_scope": ExamTrack.TRACK,
                    "pricing_type": ExamTrack.PRICING_FREE,
                    "currency": "INR",
                    "is_active": True,
                },
            )
            track.subscription_plans.set([
                self.plans["snowflake-free"],
                self.plans["snowflake-premium-monthly"],
                self.plans["snowflake-premium-lifetime"],
            ])
            TrackExam.objects.filter(track=track).delete()
            sample = TrackExam.objects.create(track=track, exam=exams[f"{slug}_sample"], order=1, is_required=True)
            mock = TrackExam.objects.create(track=track, exam=exams[f"{slug}_mock"], order=2, is_required=True)
            if slug.startswith("advanced-"):
                mock.prerequisite_exams.set([exams["core_mock"]])
            result.append(track)
        return result

    def seed_courses(self, exams):
        result = []
        for slug, title, level, primary in CERTS:
            sample = exams[f"{slug}_sample"]
            mock = exams[f"{slug}_mock"]
            for paid, plan_code in ((False, "snowflake-free"), (True, "snowflake-premium-monthly")):
                course, _ = Course.objects.update_or_create(
                    slug=f"snowflake-{slug}-{'premium' if paid else 'free'}",
                    defaults={
                        "title": f"{PREFIX}{title} {'Full Certification Preparation' if paid else 'Free Foundations'}",
                        "description": self.description(title, paid),
                        "category": self.categories[primary],
                        "level": level,
                        "owner_type": Course.OWNER_PLATFORM,
                        "organization": None,
                        "is_public": True,
                        "is_published": True,
                        "approval_status": Course.APPROVAL_APPROVED,
                        "created_by": None,
                    },
                )
                course.subscription_plans.set([self.plans[plan_code]])
                CourseSection.objects.filter(course=course).delete()
                topics = [("Architecture & Platform", "architecture"), ("Security, Data & Workloads", primary)] if paid else [("Snowflake Foundations", "architecture")]
                for section_no, (topic, cat_slug) in enumerate(topics, 1):
                    section = CourseSection.objects.create(course=course, title=topic, order=section_no, is_visible=True)
                    Lesson.objects.create(section=section, title=f"{topic}: Text Lesson", lesson_type=Lesson.TYPE_ARTICLE, order=1, article_content=self.article(title, topic))
                    Lesson.objects.create(section=section, title=f"{topic}: Video Lesson", lesson_type=Lesson.TYPE_VIDEO, order=2, video_url=VIDEO_URL, article_content=f"Use the official Snowflake video library for demonstrations: {VIDEO_URL}")
                    Lesson.objects.create(section=section, title=f"{topic}: Guided Practice", lesson_type=Lesson.TYPE_PRACTICE, order=3, practice_domain=self.domain, practice_category=self.categories[cat_slug], practice_difficulty="medium", practice_threshold=5)
                    Lesson.objects.create(section=section, title=f"{topic}: Quiz", lesson_type=Lesson.TYPE_QUIZ, order=4, exam=mock if paid else sample, quiz_completion_mode="pass" if paid else "attempt", quiz_min_score=70 if paid else 0, quiz_allow_mock=False, quiz_max_attempts=3 if paid else 0)
                result.append(course)
        return result

    def description(self, title, paid):
        if paid:
            return f"Complete NPTOR preparation for {title} with text lessons, video references, guided practice, quizzes, hands-on concepts, and a certification-style mock exam. Original educational content; not an official Snowflake course."
        return f"Free NPTOR foundations for {title}, including text, video references, guided practice, and a free sample quiz."

    def article(self, title, topic):
        return (
            f"<h2>{topic}</h2>"
            f"<p>This lesson supports the {title} Snowflake learning path.</p>"
            "<p>Study the platform mental model, understand why the feature exists, and connect the concept to a practical Snowflake workflow. Pay attention to security, cost, performance, and operational trade-offs.</p>"
            f"<p>For current product behavior, use the official Snowflake documentation: <a href='{DOCS_URL}'>{DOCS_URL}</a>.</p>"
            "<pre><code>SELECT CURRENT_VERSION();\nSELECT CURRENT_ACCOUNT();</code></pre>"
            "<p>Complete the guided practice and quiz after reading.</p>"
        )
