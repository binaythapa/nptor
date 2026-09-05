from django.core.management.base import BaseCommand
from django.db import transaction

from courses.models import Course, CourseSection, Lesson
from quiz.models import Category, Choice, Difficulty, Domain, Exam, ExamTrack, Question, TrackExam
from subscriptions.models import SubscriptionPlan

PREFIX = "Snowflake"
VIDEO_URL = "https://www.youtube.com/@Snowflake"
DOCS_URL = "https://docs.snowflake.com/"

CERTS = [
    ("associate-platform", "SnowPro Associate: Platform", "beginner"),
    ("core", "SnowPro Core", "intermediate"),
    ("advanced-architect", "SnowPro Advanced: Architect", "advanced"),
    ("advanced-data-engineer", "SnowPro Advanced: Data Engineer", "advanced"),
    ("advanced-data-scientist", "SnowPro Advanced: Data Scientist", "advanced"),
    ("advanced-administrator", "SnowPro Advanced: Administrator", "advanced"),
    ("advanced-data-analyst", "SnowPro Advanced: Data Analyst", "advanced"),
]

CATS = [
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
    ("architecture", "Which Snowflake layer provides SQL parsing, metadata management, and query optimization?", ["Cloud Services", "Virtual Warehouse", "Database Storage", "External Stage"], 0, Question.EASY),
    ("architecture", "Why can Snowflake scale compute independently from storage?", ["Compute and storage are separate layers", "Every table has its own server", "Stages replace warehouses", "Queries never use storage"], 0, Question.MEDIUM),
    ("architecture", "Which object is used to provide compute resources for executing queries?", ["Virtual warehouse", "Database", "Schema", "Stage"], 0, Question.EASY),
    ("architecture", "What is the primary purpose of a Snowflake database and schema hierarchy?", ["Logical organization of database objects", "Warehouse autoscaling", "Network encryption", "User authentication"], 0, Question.EASY),
    ("architecture", "Which characteristic is central to Snowflake's architecture?", ["Independent compute and storage", "Single fixed server", "Local-only storage", "Shared OS filesystem"], 0, Question.MEDIUM),
    ("storage", "What is a micro-partition in Snowflake?", ["A contiguous unit of table data managed by Snowflake", "A virtual warehouse node", "A database user", "A network policy"], 0, Question.EASY),
    ("storage", "What feature lets Snowflake create a copy of a database without initially duplicating all underlying data?", ["Zero-copy cloning", "Replication-only loading", "Warehouse cloning", "Result caching"], 0, Question.EASY),
    ("storage", "Which mechanism helps Snowflake skip micro-partitions that cannot contain qualifying rows?", ["Micro-partition metadata", "Role hierarchy", "Network policies", "Resource monitors"], 0, Question.MEDIUM),
    ("storage", "What does Time Travel primarily provide?", ["Access to historical data within the retention period", "Automatic warehouse resizing", "Cross-region login", "Automatic schema design"], 0, Question.EASY),
    ("storage", "What is Fail-safe intended to provide?", ["A limited recovery mechanism administered by Snowflake after Time Travel", "User query caching", "Warehouse scaling", "Routine data sharing"], 0, Question.MEDIUM),
    ("compute", "What happens when a warehouse is suspended?", ["Its running compute resources stop", "All table data is deleted", "The database becomes read-only", "All roles are disabled"], 0, Question.EASY),
    ("compute", "Which warehouse setting can reduce compute cost for intermittent workloads?", ["Auto-suspend", "Larger database", "More schemas", "Longer retention"], 0, Question.EASY),
    ("compute", "When would multi-cluster warehouses be most useful?", ["When concurrency causes query queuing", "When tables need backups", "When users need new roles", "When files need encryption"], 0, Question.MEDIUM),
    ("compute", "Which feature can improve repeated query response without rerunning the full computation?", ["Result cache", "Time Travel", "External stage", "Masking policy"], 0, Question.MEDIUM),
    ("compute", "What is a common reason to resize a warehouse?", ["To provide more compute resources per cluster", "To increase database retention", "To create more roles", "To change table ownership"], 0, Question.EASY),
    ("security", "Which Snowflake access-control approach is used to grant privileges to users through roles?", ["Role-based access control", "File-based access control", "Warehouse-only control", "DNS-based control"], 0, Question.EASY),
    ("security", "What does a masking policy control?", ["How sensitive column values are presented to eligible consumers", "Warehouse size", "Micro-partition count", "Stage file format"], 0, Question.MEDIUM),
    ("security", "What does a row access policy control?", ["Which rows a query can return", "Which warehouse can start", "Which files can upload", "Which schemas can be cloned"], 0, Question.MEDIUM),
    ("security", "Which principle should guide least-privilege Snowflake role design?", ["Grant only the privileges required for the job", "Grant ACCOUNTADMIN to every analyst", "Grant all database privileges by default", "Avoid role hierarchies"], 0, Question.EASY),
    ("security", "What is a network policy primarily used to restrict?", ["Network locations from which users can access Snowflake", "Table row counts", "Warehouse sizes", "Query result formats"], 0, Question.MEDIUM),
    ("ingestion", "Which command loads data from a Snowflake stage into a table?", ["COPY INTO", "PUT", "GET", "CREATE WAREHOUSE"], 0, Question.EASY),
    ("ingestion", "What is Snowpipe designed for?", ["Continuous or near-real-time file ingestion", "Interactive dashboard rendering", "Role creation", "Warehouse resizing"], 0, Question.EASY),
    ("ingestion", "What does a Snowflake stage provide?", ["A location from which files can be loaded or unloaded", "A compute cluster", "A role hierarchy", "A query cache"], 0, Question.EASY),
    ("ingestion", "Which capability is designed for continuously ingesting streaming data into Snowflake?", ["Snowpipe Streaming", "Time Travel", "Zero-copy cloning", "Resource Monitor"], 0, Question.MEDIUM),
    ("ingestion", "Which Snowflake object can automate work on a schedule or in response to conditions?", ["Task", "Role", "File format", "Network policy"], 0, Question.EASY),
    ("sql", "Which command combines inserts and updates based on a matching condition?", ["MERGE", "COPY", "PUT", "GRANT"], 0, Question.EASY),
    ("sql", "Which Snowflake feature is designed to simplify querying semi-structured data such as JSON?", ["VARIANT", "BOOLEAN", "GEOGRAPHY", "SEQUENCE"], 0, Question.EASY),
    ("sql", "Which SQL construct is commonly used to calculate a running total while retaining individual rows?", ["Window function", "DDL statement", "Network policy", "Stage definition"], 0, Question.MEDIUM),
    ("sql", "What is the purpose of a dynamic table?", ["Maintain query-defined results that refresh automatically toward a target lag", "Replace all warehouses", "Store user passwords", "Manage network allowlists"], 0, Question.MEDIUM),
    ("sql", "Which operation is most directly associated with transforming relational data before loading a target table?", ["SELECT with expressions and joins", "CREATE ROLE", "ALTER NETWORK POLICY", "CREATE RESOURCE MONITOR"], 0, Question.EASY),
    ("sharing", "What is a key benefit of Secure Data Sharing?", ["Share governed data without copying it into the consumer account", "Require CSV exports for every consumer", "Disable role-based access", "Move all data to object storage"], 0, Question.EASY),
    ("sharing", "What does a Snowflake Marketplace listing enable?", ["Discovery and governed access to data or data products", "Warehouse autoscaling", "Password rotation", "Micro-partition rebuilding"], 0, Question.EASY),
    ("sharing", "What is a data clean room intended to help organizations do?", ["Collaborate on sensitive data with controlled access and analysis", "Resize warehouses", "Replace SQL", "Create user passwords"], 0, Question.MEDIUM),
    ("sharing", "Which object is commonly used to package data for secure sharing?", ["Share", "Warehouse", "Network policy", "Resource monitor"], 0, Question.EASY),
    ("sharing", "What is an important governance goal when sharing data externally?", ["Expose only the data and operations the consumer is authorized to use", "Grant unrestricted database ownership", "Disable auditing", "Publish raw credentials"], 0, Question.MEDIUM),
    ("ai-snowpark", "What is Snowpark primarily used for?", ["Building data applications and transformations with supported programming languages", "Managing DNS records", "Replacing all storage", "Creating network firewalls"], 0, Question.EASY),
    ("ai-snowpark", "Which language is supported by Snowpark for DataFrame programming?", ["Python", "HTML", "CSS", "Bash only"], 0, Question.EASY),
    ("ai-snowpark", "What is Snowflake Cortex intended to provide?", ["AI/ML capabilities integrated with Snowflake data workflows", "Only DNS management", "Only warehouse billing", "Only file compression"], 0, Question.MEDIUM),
    ("ai-snowpark", "Which Snowflake capability is used to build data applications with a web application framework?", ["Streamlit in Snowflake", "Time Travel", "Fail-safe", "Resource Monitor"], 0, Question.EASY),
    ("ai-snowpark", "What is a practical benefit of running application logic close to governed Snowflake data?", ["Reduced data movement and centralized governance", "Eliminating all compute cost", "Disabling authentication", "Removing SQL support"], 0, Question.MEDIUM),
]

SECTION_TOPICS = [
    ("Platform architecture", "architecture"),
    ("Storage and micro-partitions", "storage"),
    ("Compute and performance", "compute"),
    ("Security and governance", "security"),
]

class Command(BaseCommand):
    help = "Seed a complete Snowflake certification learning catalog with free and paid content."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Remove records created by this command first.")

    @transaction.atomic
    def handle(self, *args, **options):
        if options["reset"]:
            self.reset()
        plans = self.seed_plans()
        domain = self.seed_domain()
        categories = self.seed_categories(domain)
        self.seed_difficulties()
        questions = self.seed_questions(categories)
        exams = self.seed_exams(categories, plans)
        tracks = self.seed_tracks(exams, plans)
        courses = self.seed_courses(categories, exams, plans)
        self.stdout.write(self.style.SUCCESS("Snowflake catalog seeded successfully."))
        self.stdout.write(f"Domain: 1 | Categories: {len(categories)} | Questions: {len(questions)}")
        self.stdout.write(f"Courses: {len(courses)} | Tracks: {len(tracks)} | Exams: {len(exams)}")
        self.stdout.write("Plans: free, monthly premium, lifetime premium")

    def reset(self):
        Course.objects.filter(slug__startswith="snowflake-").delete()
        ExamTrack.objects.filter(slug__startswith="snowflake-").delete()
        Exam.objects.filter(title__startswith="Snowflake | ").delete()
        Question.objects.filter(text__startswith="Snowflake | ").delete()
        Category.objects.filter(slug__startswith="snowflake-").delete()
        Domain.objects.filter(slug="snowflake").delete()
        SubscriptionPlan.objects.filter(code__startswith="snowflake-").delete()
        Difficulty.objects.filter(slug__in=["easy", "medium", "hard"]).delete()

    def seed_plans(self):
        specs = [
            ("snowflake-free", "Snowflake Free", "Free Snowflake introductory access", None, 0),
            ("snowflake-premium-monthly", "Snowflake Premium Monthly", "Full Snowflake certification preparation", 30, 999),
            ("snowflake-premium-lifetime", "Snowflake Premium Lifetime", "Lifetime access to the Snowflake certification catalog", None, 4999),
        ]
        result = {}
        for code, name, desc, days, price in specs:
            result[code] = SubscriptionPlan.objects.update_or_create(
                code=code,
                defaults={"name": name, "description": desc, "duration_days": days, "price": price, "currency": "INR", "is_active": True},
            )[0]
        return result

    def seed_domain(self):
        return Domain.objects.update_or_create(
            slug="snowflake", organization=None,
            defaults={"name": "Snowflake", "is_active": True},
        )[0]

    def seed_categories(self, domain):
        result = {}
        for slug, name in CATS:
            result[slug] = Category.objects.update_or_create(
                slug=f"snowflake-{slug}", organization=None,
                defaults={"name": name, "domain": domain, "parent": None, "is_active": True},
            )[0]
        return result

    def seed_difficulties(self):
        for slug, name in (("easy", "Easy"), ("medium", "Medium"), ("hard", "Hard")):
            Difficulty.objects.update_or_create(slug=slug, defaults={"name": name, "is_active": True})

    def seed_questions(self, categories):
        result = []
        for cat_slug, text, choices, correct, difficulty in QUESTIONS:
            question, _ = Question.objects.update_or_create(
                text=f"Snowflake | {text}",
                defaults={
                    "primary_category": categories[cat_slug],
                    "question_type": Question.SINGLE,
                    "difficulty": difficulty,
                    "is_active": True,
                    "is_deleted": False,
                    "explanation": "NPTOR Snowflake practice question. This is original educational content and is not an official Snowflake certification question.",
                },
            )
            question.categories.set([categories[cat_slug]])
            Choice.objects.filter(question=question).delete()
            Choice.objects.bulk_create([
                Choice(question=question, text=value, is_correct=(index == correct), order=index)
                for index, value in enumerate(choices)
            ])
            result.append(question)
        return result

    def make_exam(self, name, category, count, level, plans, paid=False):
        exam, _ = Exam.objects.update_or_create(
            title=f"Snowflake | {name}",
            defaults={
                "primary_category": category,
                "question_count": count,
                "duration_seconds": 3600 if count >= 20 else 1800,
                "level": level,
                "passing_score": 70,
                "is_published": True,
                "max_mock_attempts": 3,
                "allow_review": True,
            },
        )
        exam.categories.set(list(self.category_map.values()))
        exam.subscription_plans.set([plans["snowflake-premium-monthly"], plans["snowflake-premium-lifetime"]] if paid else [plans["snowflake-free"]])
        return exam

    def seed_exams(self, categories, plans):
        self.category_map = categories
        exams = {}
        exams["associate_sample"] = self.make_exam("SnowPro Associate Platform | Free Sample Exam", categories["architecture"], 10, 1, plans, False)
        exams["associate_mock"] = self.make_exam("SnowPro Associate Platform | Full Mock Exam", categories["architecture"], 20, 1, plans, True)
        exams["core_sample"] = self.make_exam("SnowPro Core | Free Sample Exam", categories["architecture"], 10, 1, plans, False)
        exams["core_mock"] = self.make_exam("SnowPro Core | Full Mock Exam", categories["architecture"], 20, 1, plans, True)
        for key, role, primary in [
            ("architect", "Architect", "architecture"),
            ("data_engineer", "Data Engineer", "ingestion"),
            ("data_scientist", "Data Scientist", "ai-snowpark"),
            ("administrator", "Administrator", "security"),
            ("data_analyst", "Data Analyst", "sql"),
        ]:
            exams[f"{key}_sample"] = self.make_exam(f"SnowPro Advanced {role} | Free Sample Exam", categories[primary], 10, 2, plans, False)
            exams[f"{key}_mock"] = self.make_exam(f"SnowPro Advanced {role} | Full Mock Exam", categories[primary], 20, 2, plans, True)
        return exams

    def seed_tracks(self, exams, plans):
        specs = [
            ("associate-platform", "SnowPro Associate: Platform", "associate_sample", "associate_mock", False),
            ("core", "SnowPro Core", "core_sample", "core_mock", False),
            ("advanced-architect", "SnowPro Advanced: Architect", "architect_sample", "architect_mock", True),
            ("advanced-data-engineer", "SnowPro Advanced: Data Engineer", "data_engineer_sample", "data_engineer_mock", True),
            ("advanced-data-scientist", "SnowPro Advanced: Data Scientist", "data_scientist_sample", "data_scientist_mock", True),
            ("advanced-administrator", "SnowPro Advanced: Administrator", "administrator_sample", "administrator_mock", True),
            ("advanced-data-analyst", "SnowPro Advanced: Data Analyst", "data_analyst_sample", "data_analyst_mock", True),
        ]
        result = []
        for slug, title, sample_key, mock_key, advanced in specs:
            track, _ = ExamTrack.objects.update_or_create(
                slug=f"snowflake-{slug}", organization=None,
                defaults={
                    "title": f"Snowflake | {title} Certification Track",
                    "description": f"Structured NPTOR preparation path for {title}. Free sample assessment plus premium full mock preparation.",
                    "subscription_scope": ExamTrack.TRACK,
                    "pricing_type": ExamTrack.PRICING_FREE,
                    "currency": "INR",
                    "is_active": True,
                },
            )
            track.subscription_plans.set([plans["snowflake-free"], plans["snowflake-premium-monthly"], plans["snowflake-premium-lifetime"]])
            TrackExam.objects.filter(track=track).delete()
            sample = TrackExam.objects.create(track=track, exam=exams[sample_key], order=1, is_required=True)
            mock = TrackExam.objects.create(track=track, exam=exams[mock_key], order=2, is_required=True)
            if advanced:
                mock.prerequisite_exams.set([exams["core_mock"]])
            result.append(track)
        return result

    def seed_courses(self, categories, exams, plans):
        result = []
        for slug, title, level in CERTS:
            sample = exams["associate_sample" if slug == "associate-platform" else "core_sample" if slug == "core" else slug.replace("advanced-", "") + "_sample"]
            mock = exams["associate_mock" if slug == "associate-platform" else "core_mock" if slug == "core" else slug.replace("advanced-", "") + "_mock"]
            for paid, plan_key in ((False, "snowflake-free"), (True, "snowflake-premium-monthly")):
                course_slug = f"snowflake-{slug}-{'premium' if paid else 'free'}"
                course_title = f"Snowflake | {title} {'Full Certification Preparation' if paid else 'Free Foundations'}"
                course, _ = Course.objects.update_or_create(
                    slug=course_slug,
                    defaults={
                        "title": course_title,
                        "description": self.course_description(title, paid),
                        "category": categories["architecture"],
                        "level": level,
                        "owner_type": Course.OWNER_PLATFORM,
                        "organization": None,
                        "is_public": True,
                        "is_published": True,
                        "approval_status": Course.APPROVAL_APPROVED,
                        "created_by": None,
                    },
                )
                course.subscription_plans.set([self.plans[plan_key]]) if hasattr(self, "plans") else course.subscription_plans.set([self.current_plans[plan_key]])
                CourseSection.objects.filter(course=course).delete()
                if paid:
                    for order, (topic, cat) in enumerate(SECTION_TOPICS, 1):
                        section = CourseSection.objects.create(course=course, title=topic, order=order, is_visible=True)
                        Lesson.objects.create(section=section, title=f"{topic}: Core Concepts", lesson_type=Lesson.TYPE_ARTICLE, order=1, article_content=self.article(title, topic))
                        Lesson.objects.create(section=section, title=f"{topic}: Snowflake Video", lesson_type=Lesson.TYPE_VIDEO, order=2, video_url=VIDEO_URL, article_content=f"Official Snowflake video library reference. See {VIDEO_URL}.")
                        Lesson.objects.create(section=section, title=f"{topic}: Guided Practice", lesson_type=Lesson.TYPE_PRACTICE, order=3, practice_domain=self.domain, practice_category=categories[cat], practice_difficulty="medium", practice_threshold=5)
                        Lesson.objects.create(section=section, title=f"{topic}: Knowledge Check", lesson_type=Lesson.TYPE_QUIZ, order=4, exam=mock, quiz_completion_mode="pass", quiz_min_score=70, quiz_allow_mock=False, quiz_max_attempts=3)
                else:
                    section = CourseSection.objects.create(course=course, title="Start Here: Snowflake Foundations", order=1, is_visible=True)
                    Lesson.objects.create(section=section, title="What is Snowflake?", lesson_type=Lesson.TYPE_ARTICLE, order=1, article_content=self.article(title, "Snowflake foundations"))
                    Lesson.objects.create(section=section, title="Snowflake Platform Overview", lesson_type=Lesson.TYPE_VIDEO, order=2, video_url=VIDEO_URL, article_content=f"Official Snowflake video library reference. See {VIDEO_URL}.")
                    Lesson.objects.create(section=section, title="Practice: Snowflake Fundamentals", lesson_type=Lesson.TYPE_PRACTICE, order=3, practice_domain=self.domain, practice_category=categories["architecture"], practice_difficulty="easy", practice_threshold=5)
                    Lesson.objects.create(section=section, title="Free Sample Quiz", lesson_type=Lesson.TYPE_QUIZ, order=4, exam=sample, quiz_completion_mode="attempt", quiz_min_score=0, quiz_allow_mock=False, quiz_max_attempts=0)
                result.append(course)
        return result

    def course_description(self, title, paid):
        if paid:
            return f"Complete NPTOR Snowflake preparation for {title}, combining text lessons, video references, guided practice, quizzes, hands-on concepts, and certification-style mock assessment. Content is original educational material and is not an official Snowflake course."
        return f"Free Snowflake foundations for learners preparing for {title}. Includes text, video references, guided practice, and a sample quiz."

    def article(self, title, topic):
        return f"<h2>{topic}</h2><p>This NPTOR lesson builds practical Snowflake knowledge for the {title} learning path.</p><p>Focus on the platform mental model, the reason a feature exists, the operational trade-offs, and the SQL or administrative workflow you would use in a real Snowflake environment.</p><p>Use the official Snowflake documentation as the authoritative reference for current product behavior: <a href=\"{DOCS_URL}\">Snowflake Documentation</a>.</p><pre><code>-- Example learning workflow\nSELECT CURRENT_VERSION();\nSELECT CURRENT_ACCOUNT();</code></pre><p>After reading, complete the guided practice and knowledge check.</p>"
