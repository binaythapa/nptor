from decimal import Decimal
from uuid import uuid4

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import IntegrityError, models, transaction
from django.utils import timezone

from courses.models import Course, CourseSection, Lesson
from organizations.models import Organization, OrganizationMember
from quiz.models import (
    Category,
    Choice,
    ContentVertical,
    Difficulty,
    Domain,
    Exam,
    ExamTrack,
    Question,
    TrackExam,
)
from subscriptions.models import SubscriptionPlan


DEMO_PREFIX = "Demo "
DEMO_CODE_PREFIX = "demo-"
SKIP_MODELS = {
    "admin.LogEntry",
    "contenttypes.ContentType",
    "sessions.Session",
    "authtoken.Token",
}


class Command(BaseCommand):
    help = "Create a repeatable demo dataset for local development and UI testing."

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-generic",
            action="store_true",
            help="Seed the curated demo dataset only.",
        )

    def handle(self, *args, **options):
        self.created = 0
        self.reused = 0
        self.skipped = []

        with transaction.atomic():
            context = self._seed_core()
            if not options["skip_generic"]:
                self._seed_remaining_models(context)

        self.stdout.write(
            self.style.SUCCESS(
                f"Demo data ready: {self.created} created, "
                f"{self.reused} reused, {len(self.skipped)} model(s) skipped."
            )
        )
        if self.skipped:
            self.stdout.write("Skipped models: " + ", ".join(self.skipped))

    def _get_or_create(self, model, lookup, defaults=None):
        obj, created = model.objects.get_or_create(
            **lookup,
            defaults=defaults or {},
        )
        if created:
            self.created += 1
        else:
            self.reused += 1
        return obj

    def _seed_core(self):
        User = get_user_model()
        admin = self._get_or_create(
            User,
            {"username": "demo_admin"},
            {
                "email": "demo.admin@example.test",
                "first_name": "Demo",
                "last_name": "Admin",
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
            },
        )
        teacher = self._get_or_create(
            User,
            {"username": "demo_teacher"},
            {
                "email": "demo.teacher@example.test",
                "first_name": "Demo",
                "last_name": "Teacher",
                "is_active": True,
            },
        )
        student = self._get_or_create(
            User,
            {"username": "demo_student"},
            {
                "email": "demo.student@example.test",
                "first_name": "Demo",
                "last_name": "Student",
                "is_active": True,
            },
        )
        for user in (admin, teacher, student):
            if not user.has_usable_password():
                user.set_password("DemoPass123!")
                user.save(update_fields=["password"])

        org = self._get_or_create(
            Organization,
            {"slug": "demo-academy"},
            {
                "name": "Demo Academy",
                "org_type": Organization.TYPE_INSTITUTE,
                "is_active": True,
                "created_by": admin,
            },
        )
        for user, role in (
            (admin, OrganizationMember.ROLE_ORG_OWNER),
            (teacher, OrganizationMember.ROLE_STAFF),
            (student, OrganizationMember.ROLE_STUDENT),
        ):
            self._get_or_create(
                OrganizationMember,
                {"user": user, "organization": org},
                {"role": role, "is_active": True},
            )

        vertical = self._get_or_create(
            ContentVertical,
            {"code": "demo-data-skills"},
            {
                "name": "Demo Data Skills",
                "vertical_type": ContentVertical.SKILL_ASSESSMENT,
                "is_active": True,
            },
        )
        platform_domain = self._get_or_create(
            Domain,
            {"organization": None, "slug": "demo-data-analytics"},
            {
                "name": "Demo Data Analytics",
                "content_vertical": vertical,
                "is_active": True,
            },
        )
        org_domain = self._get_or_create(
            Domain,
            {"organization": org, "slug": "demo-business-analytics"},
            {
                "name": "Demo Business Analytics",
                "content_vertical": vertical,
                "is_active": True,
            },
        )

        categories = []
        for name, slug, domain, organization in (
            (
                "Demo SQL Fundamentals",
                "demo-sql-fundamentals",
                platform_domain,
                None,
            ),
            (
                "Demo Python Basics",
                "demo-python-basics",
                platform_domain,
                None,
            ),
            (
                "Demo Business Reporting",
                "demo-business-reporting",
                org_domain,
                org,
            ),
        ):
            categories.append(
                self._get_or_create(
                    Category,
                    {"organization": organization, "slug": slug},
                    {"name": name, "domain": domain, "is_active": True},
                )
            )

        difficulties = [
            self._get_or_create(
                Difficulty,
                {"slug": slug},
                {"name": name, "is_active": True},
            )
            for slug, name in (
                ("easy", "Easy"),
                ("medium", "Medium"),
                ("hard", "Hard"),
            )
        ]

        questions = []
        question_texts = [
            "Demo Question 1: Which SQL clause filters grouped results?",
            "Demo Question 2: Which Python type stores key-value pairs?",
            "Demo Question 3: What does SELECT COUNT(*) return?",
            "Demo Question 4: Which keyword defines a Python function?",
            "Demo Question 5: Which SQL command adds a new row?",
            "Demo Question 6: Which Python value represents no value?",
        ]
        for index, text in enumerate(question_texts):
            category = categories[index % 2]
            question = self._get_or_create(
                Question,
                {"text": text},
                {
                    "primary_category": category,
                    "question_type": Question.SINGLE,
                    "difficulty": difficulties[index % 3].slug,
                    "is_active": True,
                    "is_deleted": False,
                    "explanation": "Demo explanation for UI and grading tests.",
                    "created_by": teacher,
                },
            )
            question.categories.set([category])
            questions.append(question)
            for choice_index, choice_text in enumerate(
                (
                    "Demo Option A",
                    "Demo Option B",
                    "Demo Option C",
                    "Demo Option D",
                )
            ):
                self._get_or_create(
                    Choice,
                    {"question": question, "order": choice_index + 1},
                    {
                        "text": choice_text,
                        "is_correct": choice_index == (index % 4),
                    },
                )

        exams = []
        for title, organization, category in (
            ("Demo SQL Foundations Exam", None, categories[0]),
            ("Demo Python Fundamentals Exam", None, categories[1]),
            ("Demo Advanced Analytics Exam", None, categories[0]),
            ("Demo Academy Reporting Exam", org, categories[2]),
        ):
            exam = self._get_or_create(
                Exam,
                {"title": title},
                {
                    "organization": organization,
                    "primary_category": category,
                    "question_count": 6,
                    "duration_seconds": 900,
                    "level": 1 if "Foundations" in title or "Python" in title else 2,
                    "passing_score": 60,
                    "is_published": True,
                    "max_mock_attempts": 3,
                    "allow_review": True,
                    "created_by": teacher,
                },
            )
            exam.categories.set([category])
            exams.append(exam)

        plans = [
            self._get_or_create(
                SubscriptionPlan,
                {"code": "demo-course-plan"},
                {
                    "name": "Demo Course Plan",
                    "product_type": SubscriptionPlan.PRODUCT_COURSE,
                    "access_mode": SubscriptionPlan.ACCESS_SINGLE_RESOURCE,
                    "scope": SubscriptionPlan.SCOPE_RESOURCE,
                    "price": Decimal("499.00"),
                    "currency": "INR",
                    "duration_days": 30,
                    "description": "Demo plan for Course access.",
                    "is_active": True,
                },
            ),
            self._get_or_create(
                SubscriptionPlan,
                {"code": "demo-track-plan"},
                {
                    "name": "Demo Track Plan",
                    "product_type": SubscriptionPlan.PRODUCT_TRACK,
                    "access_mode": SubscriptionPlan.ACCESS_SINGLE_RESOURCE,
                    "scope": SubscriptionPlan.SCOPE_RESOURCE,
                    "price": Decimal("799.00"),
                    "currency": "INR",
                    "duration_days": 60,
                    "description": "Demo plan for Track access.",
                    "is_active": True,
                },
            ),
            self._get_or_create(
                SubscriptionPlan,
                {"code": "demo-account-plan"},
                {
                    "name": "Demo All Access",
                    "product_type": SubscriptionPlan.PRODUCT_ACCOUNT,
                    "access_mode": SubscriptionPlan.ACCESS_ALL,
                    "scope": SubscriptionPlan.SCOPE_ALL_ACCESS,
                    "price": Decimal("1499.00"),
                    "currency": "INR",
                    "description": "Demo account-wide access plan.",
                    "is_active": True,
                },
            ),
        ]

        tracks = []
        for title, slug, organization, track_exams in (
            (
                "Demo Data Analytics Track",
                "demo-data-analytics-track",
                None,
                [exams[0], exams[1], exams[2]],
            ),
            (
                "Demo Academy Track",
                "demo-academy-track",
                org,
                [exams[3], exams[1]],
            ),
        ):
            track = self._get_or_create(
                ExamTrack,
                {"organization": organization, "slug": slug},
                {
                    "title": title,
                    "description": "Demo learning track for progression testing.",
                    "is_active": True,
                    "pricing_type": ExamTrack.PRICING_FREE,
                    "currency": "INR",
                },
            )
            tracks.append(track)
            for order, exam in enumerate(track_exams, 1):
                membership = self._get_or_create(
                    TrackExam,
                    {"track": track, "exam": exam},
                    {"order": order, "is_required": True},
                )
                if membership.order != order or not membership.is_required:
                    membership.order = order
                    membership.is_required = True
                    membership.save(update_fields=["order", "is_required"])
            if len(track_exams) >= 3:
                second = TrackExam.objects.get(
                    track=track,
                    exam=track_exams[1],
                )
                second.prerequisite_exams.set([track_exams[0]])

        courses = []
        for title, slug, organization, category, course_exams, plan in (
            (
                "Demo Data Analytics Course",
                "demo-data-analytics-course",
                None,
                categories[0],
                [exams[0], exams[1]],
                plans[0],
            ),
            (
                "Demo Academy Reporting Course",
                "demo-academy-reporting-course",
                org,
                categories[2],
                [exams[3]],
                plans[0],
            ),
        ):
            course = self._get_or_create(
                Course,
                {"slug": slug},
                {
                    "title": title,
                    "description": "Demo course used to exercise catalog, enrollment, lesson and exam relationships.",
                    "category": category,
                    "level": "beginner",
                    "owner_type": Course.OWNER_ORGANIZATION if organization else Course.OWNER_PLATFORM,
                    "organization": organization,
                    "is_public": not bool(organization),
                    "is_published": True,
                    "approval_status": Course.APPROVAL_APPROVED,
                    "created_by": teacher,
                },
            )
            course.subscription_plans.add(plan)
            course.exams.set(course_exams)
            courses.append(course)
            section = self._get_or_create(
                CourseSection,
                {"course": course, "order": 1},
                {
                    "title": f"Demo {title.replace('Course', '').strip()} Introduction",
                    "is_visible": True,
                },
            )
            self._get_or_create(
                Lesson,
                {"section": section, "order": 1},
                {
                    "title": f"Demo {title.replace('Course', '').strip()} Overview",
                    "lesson_type": Lesson.TYPE_ARTICLE,
                    "article_content": "Demo lesson content for local development and UI testing.",
                },
            )
            self._get_or_create(
                Lesson,
                {"section": section, "order": 2},
                {
                    "title": f"Demo {title.replace('Course', '').strip()} Assessment",
                    "lesson_type": Lesson.TYPE_QUIZ,
                    "exam": course_exams[0],
                },
            )

        return {
            "users": (admin, teacher, student),
            "organization": org,
            "domains": (platform_domain, org_domain),
            "categories": categories,
            "questions": questions,
            "exams": exams,
            "tracks": tracks,
            "courses": courses,
            "plans": plans,
        }

    def _seed_remaining_models(self, context):
        seeded_models = {
            ContentVertical,
            Domain,
            Category,
            Difficulty,
            Question,
            Choice,
            Exam,
            ExamTrack,
            TrackExam,
            Course,
            CourseSection,
            Lesson,
            SubscriptionPlan,
            Organization,
            OrganizationMember,
            get_user_model(),
        }
        for model in apps.get_models():
            if (
                model in seeded_models
                or model._meta.abstract
                or model._meta.proxy
                or model._meta.auto_created
                or model._meta.label in SKIP_MODELS
            ):
                continue
            try:
                with transaction.atomic():
                    self._generic_instance(model, set())
            except Exception as exc:
                self.skipped.append(
                    f"{model._meta.label} ({exc.__class__.__name__})"
                )

    def _generic_instance(self, model, stack):
        if model in stack:
            return None
        stack = set(stack)
        stack.add(model)

        existing = model.objects.order_by("pk").first()
        if existing is not None:
            return existing

        kwargs = {}
        for field in model._meta.concrete_fields:
            if (
                field.primary_key
                or field.auto_created
                or getattr(field, "auto_now", False)
                or getattr(field, "auto_now_add", False)
                or field.has_default()
                or field.null
                or field.blank
            ):
                continue
            if isinstance(field, models.ForeignKey):
                related = self._generic_instance(field.remote_field.model, stack)
                if related is None:
                    raise ValueError(f"cannot satisfy {field.name}")
                kwargs[field.name] = related
                continue
            value = self._generic_value(model, field)
            if value is not None:
                kwargs[field.name] = value

        obj = model.objects.create(**kwargs)
        self.created += 1
        self._seed_generic_m2m(obj, model, stack)
        return obj

    def _generic_value(self, model, field):
        name = field.name.lower()
        if getattr(field, "choices", None):
            return field.choices[0][0]
        if isinstance(field, models.EmailField):
            return f"{DEMO_CODE_PREFIX}{model._meta.model_name}-{uuid4().hex[:8]}@example.test"
        if isinstance(field, models.URLField):
            return f"https://example.test/demo/{model._meta.model_name}"
        if isinstance(field, models.UUIDField):
            return uuid4()
        if isinstance(field, models.BooleanField):
            return "active" in name
        if isinstance(
            field,
            (
                models.IntegerField,
                models.PositiveIntegerField,
                models.PositiveSmallIntegerField,
                models.SmallIntegerField,
            ),
        ):
            return 1
        if isinstance(field, models.FloatField):
            return 1.0
        if isinstance(field, models.DecimalField):
            return Decimal("1.00")
        if isinstance(field, models.DateTimeField):
            return timezone.now()
        if isinstance(field, models.DateField):
            return timezone.localdate()
        if isinstance(field, models.TimeField):
            return timezone.localtime().time()
        if isinstance(field, models.JSONField):
            return {}
        if isinstance(field, models.BinaryField):
            return b"demo"
        if isinstance(field, models.SlugField):
            return f"{DEMO_CODE_PREFIX}{model._meta.model_name}-{uuid4().hex[:8]}"
        if isinstance(field, (models.CharField, models.TextField)):
            if name in {"name", "title", "label"}:
                return f"{DEMO_PREFIX}{model._meta.verbose_name.title()}"
            if "code" in name:
                return f"{DEMO_CODE_PREFIX}{model._meta.model_name}-{uuid4().hex[:8]}"
            return f"{DEMO_PREFIX}{model._meta.verbose_name.title()} sample"
        return None

    def _seed_generic_m2m(self, obj, model, stack):
        for field in model._meta.many_to_many:
            if field.auto_created:
                continue
            related = field.remote_field.model.objects.order_by("pk").first()
            if related is None:
                related = self._generic_instance(field.remote_field.model, stack)
            if related is not None:
                try:
                    getattr(obj, field.name).add(related)
                except (IntegrityError, TypeError, ValueError):
                    pass
