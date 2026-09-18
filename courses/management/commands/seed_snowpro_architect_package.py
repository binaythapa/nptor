from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from courses.models import Course, CourseSection, Lesson
from quiz.models import Category, Choice, Domain, Exam, ExamCategoryAllocation, ExamTrack, Question, TrackExam
from subscriptions.models import SubscriptionPlan


COURSE_SLUG = "snowpro-advanced-architect"
TRACK_SLUG = "snowpro-advanced-architect"
COURSE_TITLE = "SnowPro Advanced — Architect"
TRACK_TITLE = "SnowPro Advanced — Architect Certification Track"
COURSE_PLAN_CODE = "snowpro-advanced-architect-course-monthly"
TRACK_PLAN_CODE = "snowpro-advanced-architect-track-monthly"
EXAM_TITLE = "Snowflake | SnowPro Advanced Architect Practice Exam"
PREFIX = "SnowPro Architect | "


CONTENT = [
    ("Architecture and Design", [
        ("Architectural Design Principles", Lesson.TYPE_ARTICLE, "<h2>Architectural Design Principles</h2><p>Architectural decisions should balance scalability, reliability, security, operability, and cost. Snowflake separates storage from compute, allowing workloads to scale independently.</p><ul><li>Choose workload-specific warehouses.</li><li>Separate environments and responsibilities.</li><li>Design for least privilege and operational visibility.</li><li>Document trade-offs and service boundaries.</li></ul>"),
        ("Architecture Design Video", Lesson.TYPE_VIDEO, "https://www.youtube.com/results?search_query=Snowflake+advanced+architecture+design"),
        ("Architecture Design Lab", Lesson.TYPE_PRACTICE, "architecture"),
    ]),
    ("Performance and Workload Management", [
        ("Workload Isolation and Concurrency", Lesson.TYPE_ARTICLE, "<h2>Workload Isolation</h2><p>Use separate virtual warehouses for workloads with different performance, governance, and cost requirements. Multi-cluster warehouses can help manage concurrency, while resizing provides more resources to a cluster.</p><p>Monitor queuing, spilling, warehouse utilization, and query profiles before changing the architecture.</p>"),
        ("Performance Architecture Video", Lesson.TYPE_VIDEO, "https://www.youtube.com/results?search_query=Snowflake+performance+architecture+multi+cluster+warehouses"),
        ("Performance Architecture Lab", Lesson.TYPE_PRACTICE, "compute"),
    ]),
    ("Security and Governance Architecture", [
        ("Enterprise Security Architecture", Lesson.TYPE_ARTICLE, "<h2>Security and Governance Architecture</h2><p>Build security around role hierarchy, least privilege, network controls, authentication, encryption, masking policies, row access policies, tags, and auditing.</p><p>Separate administrative duties from data access duties and use controlled ownership roles for managed objects.</p>"),
        ("Security Architecture Video", Lesson.TYPE_VIDEO, "https://www.youtube.com/results?search_query=Snowflake+enterprise+security+governance+architecture"),
        ("Security Architecture Lab", Lesson.TYPE_PRACTICE, "security"),
    ]),
    ("Data Sharing and Resilience", [
        ("Data Sharing and Business Continuity", Lesson.TYPE_ARTICLE, "<h2>Sharing and Resilience</h2><p>Secure Data Sharing supports governed data distribution without requiring providers to copy shared data into consumer accounts.</p><p>Architect for recovery objectives using replication, failover planning, controlled data sharing, and documented recovery procedures. Validate dependencies and permissions during disaster-recovery exercises.</p>"),
        ("Sharing and Resilience Video", Lesson.TYPE_VIDEO, "https://www.youtube.com/results?search_query=Snowflake+data+sharing+replication+failover+architecture"),
        ("Resilience Architecture Lab", Lesson.TYPE_PRACTICE, "sharing"),
        ("Architect Practice Assessment", Lesson.TYPE_QUIZ, None),
    ]),
]

QUESTION_BANK = [
    ("Which design best supports workload isolation in Snowflake?", ["Use separate warehouses for materially different workloads", "Run every workload on one warehouse", "Store every workload in a separate account", "Disable monitoring"], 0, "architecture"),
    ("What is the primary purpose of a multi-cluster warehouse?", ["Improve concurrency handling", "Increase Time Travel retention", "Replace role hierarchy", "Create external stages"], 0, "compute"),
    ("Which control determines which rows a user can see?", ["Row access policy", "Warehouse size", "File format", "Resource monitor"], 0, "security"),
    ("What is a key benefit of Secure Data Sharing?", ["Governed sharing without copying shared data into the consumer account", "Automatic removal of RBAC", "Mandatory CSV exports", "Disabling encryption"], 0, "sharing"),
    ("Which approach supports least privilege?", ["Grant only the permissions required for a defined responsibility", "Grant ACCOUNTADMIN to all analysts", "Use shared passwords", "Avoid role hierarchies"], 0, "security"),
    ("What should guide a warehouse resizing decision?", ["Observed workload behavior and query performance evidence", "The number of database names", "The number of roles", "The number of file formats"], 0, "compute"),
    ("Which activity validates a disaster-recovery design?", ["A documented and exercised recovery test", "Changing a table comment", "Creating an unused schema", "Renaming a warehouse"], 0, "sharing"),
    ("Why should architecture decisions document trade-offs?", ["To make reliability, cost, security, and operational consequences explicit", "To avoid all monitoring", "To remove the need for testing", "To guarantee zero cost"], 0, "architecture"),
]


class Command(BaseCommand):
    help = "Seed the SnowPro Advanced Architect course, track, exam, and subscription plans."

    def add_arguments(self, parser):
        parser.add_argument("--username", help="Course owner username; defaults to first superuser or active user.")
        parser.add_argument("--reset", action="store_true", help="Delete this package's records before recreating them.")

    @transaction.atomic
    def handle(self, *args, **options):
        if options["reset"]:
            self._reset()

        owner = self._owner(options.get("username"))
        domain = self._domain()
        categories = self._categories(domain)
        exam = self._exam(categories, owner)
        track = self._track(exam)
        course = self._course(owner, domain)
        self._lessons(course, categories, domain, exam)
        course_plan, track_plan = self._plans()
        course.subscription_plans.set([course_plan])
        track.subscription_plans.set([track_plan])

        self.stdout.write(self.style.SUCCESS("SnowPro Advanced Architect package seeded successfully."))
        self.stdout.write(f"Course: {course.title}")
        self.stdout.write(f"Track: {track.title}")
        self.stdout.write(f"Exam: {exam.title}")
        self.stdout.write(f"Plans: {course_plan.code}, {track_plan.code}")

    def _owner(self, username):
        User = get_user_model()
        if username:
            try:
                return User.objects.get(username=username)
            except User.DoesNotExist as exc:
                raise CommandError(f"User '{username}' does not exist.") from exc
        owner = User.objects.filter(is_superuser=True).order_by("id").first()
        owner = owner or User.objects.filter(is_active=True).order_by("id").first()
        if not owner:
            raise CommandError("No active user exists. Pass --username.")
        return owner

    def _domain(self):
        domain, _ = Domain.objects.update_or_create(organization=None, slug="snowflake", defaults={"name": "Snowflake", "is_active": True})
        return domain

    def _categories(self, domain):
        names = {
            "architecture": "Architecture & Platform",
            "compute": "Compute & Performance",
            "security": "Security & Governance",
            "sharing": "Sharing & Collaboration",
        }
        result = {}
        for slug, name in names.items():
            category, _ = Category.objects.update_or_create(
                organization=None,
                slug=f"snowflake-{slug}",
                defaults={"name": name, "domain": domain, "parent": None, "is_active": True},
            )
            result[slug] = category
        return result

    def _exam(self, categories, owner):
        exam, _ = Exam.objects.update_or_create(
            title=EXAM_TITLE,
            defaults={
                "question_count": len(QUESTION_BANK),
                "duration_seconds": 1800,
                "level": 3,
                "passing_score": 70,
                "is_published": True,
                "max_mock_attempts": 3,
                "allow_review": True,
                "created_by": owner,
            },
        )
        exam.categories.set(categories.values())
        ExamCategoryAllocation.objects.filter(exam=exam).delete()
        questions_by_category = {slug: 0 for slug in categories}
        for text, choices, correct, category_slug in QUESTION_BANK:
            question, _ = Question.objects.update_or_create(
                text=f"{PREFIX}{text}",
                defaults={
                    "primary_category": categories[category_slug],
                    "question_type": Question.SINGLE,
                    "difficulty": Question.HARD,
                    "is_active": True,
                    "is_deleted": False,
                    "explanation": "Original NPTOR educational content; not an official Snowflake certification question.",
                },
            )
            question.categories.set([categories[category_slug]])
            Choice.objects.filter(question=question).delete()
            Choice.objects.bulk_create([
                Choice(question=question, text=value, is_correct=index == correct, order=index)
                for index, value in enumerate(choices)
            ])
            questions_by_category[category_slug] += 1
        for slug, count in questions_by_category.items():
            ExamCategoryAllocation.objects.create(exam=exam, category=categories[slug], fixed_count=count, include_descendants=True)
        return exam

    def _track(self, exam):
        track, _ = ExamTrack.objects.update_or_create(
            organization=None,
            slug=TRACK_SLUG,
            defaults={
                "title": TRACK_TITLE,
                "description": "A paid preparation track for SnowPro Advanced Architect study and assessment.",
                "subscription_scope": ExamTrack.TRACK,
                "pricing_type": ExamTrack.PRICING_MONTHLY,
                "monthly_price": 2499,
                "currency": "INR",
                "is_active": True,
            },
        )
        TrackExam.objects.update_or_create(track=track, exam=exam, defaults={"order": 1, "is_required": True})
        return track

    def _course(self, owner, domain):
        course, _ = Course.objects.update_or_create(
            slug=COURSE_SLUG,
            defaults={
                "title": COURSE_TITLE,
                "description": "Advanced Snowflake architecture preparation covering design, performance, security, sharing, resilience, practical labs, video resources, and assessment.",
                "category": domain,
                "level": "advanced",
                "owner_type": Course.OWNER_PLATFORM,
                "organization": None,
                "is_public": True,
                "is_published": True,
                "approval_status": Course.APPROVAL_APPROVED,
                "created_by": owner,
            },
        )
        return course

    def _lessons(self, course, categories, domain, exam):
        for section_order, (section_title, lessons) in enumerate(CONTENT, start=1):
            section, _ = CourseSection.objects.update_or_create(
                course=course,
                order=section_order,
                defaults={"title": section_title, "is_visible": True},
            )
            for lesson_order, (title, lesson_type, value) in enumerate(lessons, start=1):
                defaults = {
                    "title": title,
                    "lesson_type": lesson_type,
                    "video_url": None,
                    "article_content": "",
                    "practice_domain": None,
                    "practice_category": None,
                    "practice_difficulty": None,
                    "practice_threshold": 10,
                    "practice_lock_filters": True,
                    "practice_require_correct": False,
                    "practice_min_accuracy": None,
                    "exam": None,
                    "quiz_completion_mode": "attempt",
                    "quiz_min_score": 0,
                    "quiz_allow_mock": False,
                    "quiz_max_attempts": 0,
                }
                if lesson_type == Lesson.TYPE_ARTICLE:
                    defaults["article_content"] = value
                elif lesson_type == Lesson.TYPE_VIDEO:
                    defaults["video_url"] = value
                elif lesson_type == Lesson.TYPE_PRACTICE:
                    defaults.update({
                        "practice_domain": domain,
                        "practice_category": categories[value],
                        "practice_difficulty": "hard",
                        "practice_threshold": 10,
                    })
                elif lesson_type == Lesson.TYPE_QUIZ:
                    defaults.update({"exam": exam, "quiz_completion_mode": "pass", "quiz_min_score": 70, "quiz_max_attempts": 3})
                Lesson.objects.update_or_create(section=section, order=lesson_order, defaults=defaults)

    def _plans(self):
        common = {
            "scope": SubscriptionPlan.SCOPE_RESOURCE,
            "access_mode": SubscriptionPlan.ACCESS_SINGLE_RESOURCE,
            "interval_unit": SubscriptionPlan.INTERVAL_MONTH,
            "interval_count": 1,
            "price": 2499,
            "currency": "INR",
            "is_active": True,
        }
        course_plan, _ = SubscriptionPlan.objects.update_or_create(
            code=COURSE_PLAN_CODE,
            defaults={**common, "name": "SnowPro Advanced Architect Course — Monthly", "product_type": SubscriptionPlan.PRODUCT_COURSE, "description": "Monthly access to the SnowPro Advanced Architect course."},
        )
        track_plan, _ = SubscriptionPlan.objects.update_or_create(
            code=TRACK_PLAN_CODE,
            defaults={**common, "name": "SnowPro Advanced Architect Track — Monthly", "product_type": SubscriptionPlan.PRODUCT_TRACK, "description": "Monthly access to the SnowPro Advanced Architect certification track."},
        )
        return course_plan, track_plan

    def _reset(self):
        Course.objects.filter(slug=COURSE_SLUG).delete()
        ExamTrack.objects.filter(slug=TRACK_SLUG, organization=None).delete()
        Exam.objects.filter(title=EXAM_TITLE).delete()
        Question.objects.filter(text__startswith=PREFIX).delete()
        SubscriptionPlan.objects.filter(code__in=[COURSE_PLAN_CODE, TRACK_PLAN_CODE]).delete()
