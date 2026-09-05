from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from courses.models import Course, CourseSection, Lesson
from quiz.models import (
    Category,
    ContentVertical,
    Country,
    Domain,
    Exam,
    ExamCategoryAllocation,
    ExamTrack,
    GovernmentBody,
    GovernmentExamProgram,
    GovernmentExamStage,
    GovernmentExamVersion,
    GovernmentJob,
    TrackExam,
)


COUNTRIES = [
    {"name": "Nepal", "code": "NPL", "slug": "nepal"},
    {"name": "India", "code": "IND", "slug": "india"},
    {"name": "United States", "code": "USA", "slug": "united-states"},
]

BODIES = [
    {"country": "NPL", "name": "Public Service Commission", "code": "psc", "website": "https://psc.gov.np/"},
    {"country": "IND", "name": "Union Public Service Commission", "code": "upsc", "website": "https://www.upsc.gov.in/"},
    {"country": "IND", "name": "Staff Selection Commission", "code": "ssc", "website": "https://ssc.gov.in/"},
    {"country": "USA", "name": "U.S. Office of Personnel Management", "code": "opm", "website": "https://www.opm.gov/"},
]

JOBS = [
    ("NPL", "psc", "Kharidar", "kharidar"),
    ("NPL", "psc", "Nayab Subba", "nayab-subba"),
    ("NPL", "psc", "Section Officer", "section-officer"),
    ("IND", "upsc", "Civil Services", "civil-services"),
    ("IND", "upsc", "Engineering Services", "engineering-services"),
    ("IND", "ssc", "Combined Graduate Level", "ssc-cgl"),
    ("IND", "ssc", "Combined Higher Secondary Level", "ssc-chsl"),
    ("USA", "opm", "Federal Competitive Service Applicant", "federal-competitive-service"),
]

PROGRAMS = [
    {
        "country": "NPL", "body": "psc", "code": "kharidar", "name": "Lok Sewa Kharidar Preparation",
        "jobs": ["kharidar"], "description": "Original NPTOR preparation resources for candidates targeting the Kharidar recruitment pathway.",
        "website": "https://psc.gov.np/",
    },
    {
        "country": "NPL", "body": "psc", "code": "nayab-subba", "name": "Lok Sewa Nayab Subba Preparation",
        "jobs": ["nayab-subba"], "description": "Original NPTOR preparation resources for candidates targeting the Nayab Subba recruitment pathway.",
        "website": "https://psc.gov.np/",
    },
    {
        "country": "NPL", "body": "psc", "code": "section-officer", "name": "Lok Sewa Section Officer Preparation",
        "jobs": ["section-officer"], "description": "Original NPTOR preparation resources for candidates targeting Section Officer recruitment.",
        "website": "https://psc.gov.np/",
    },
    {
        "country": "IND", "body": "upsc", "code": "civil-services", "name": "UPSC Civil Services Preparation",
        "jobs": ["civil-services"], "description": "Original NPTOR preparation resources aligned to the UPSC Civil Services recruitment pathway. Always verify the current official notification and syllabus.",
        "website": "https://www.upsc.gov.in/",
    },
    {
        "country": "IND", "body": "upsc", "code": "engineering-services", "name": "UPSC Engineering Services Preparation",
        "jobs": ["engineering-services"], "description": "Original NPTOR preparation resources for Engineering Services candidates. Verify the active UPSC notification before relying on exam-specific details.",
        "website": "https://www.upsc.gov.in/",
    },
    {
        "country": "IND", "body": "ssc", "code": "ssc-cgl", "name": "SSC CGL Preparation",
        "jobs": ["ssc-cgl"], "description": "Original NPTOR preparation resources for SSC CGL candidates. Current official scheme and notification should be checked before each attempt.",
        "website": "https://ssc.gov.in/",
    },
    {
        "country": "IND", "body": "ssc", "code": "ssc-chsl", "name": "SSC CHSL Preparation",
        "jobs": ["ssc-chsl"], "description": "Original NPTOR preparation resources for SSC CHSL candidates. Current official scheme and notification should be checked before each attempt.",
        "website": "https://ssc.gov.in/",
    },
    {
        "country": "USA", "body": "opm", "code": "federal-competitive-service", "name": "U.S. Federal Competitive Hiring Preparation",
        "jobs": ["federal-competitive-service"], "description": "NPTOR preparation for general federal competitive hiring assessments. Specific assessment methods vary by vacancy and agency; verify the job announcement.",
        "website": "https://www.usajobs.gov/",
    },
]

SUBJECTS = [
    ("General Awareness", "general-awareness"),
    ("Current Affairs", "current-affairs"),
    ("Quantitative Aptitude", "quantitative-aptitude"),
    ("Reasoning", "reasoning"),
    ("English Language", "english-language"),
    ("Government & Constitution", "government-constitution"),
]


class Command(BaseCommand):
    help = "Seed the reusable NPTOR government exam catalog, courses, tracks and practice exams."

    @transaction.atomic
    def handle(self, *args, **options):
        vertical, _ = ContentVertical.objects.update_or_create(
            code="government-exam",
            defaults={
                "name": "Government / Competitive Exam",
                "vertical_type": ContentVertical.GOVERNMENT_EXAM,
                "is_active": True,
            },
        )

        countries = {}
        for item in COUNTRIES:
            country, _ = Country.objects.update_or_create(
                code=item["code"],
                defaults={"name": item["name"], "slug": item["slug"], "is_active": True},
            )
            countries[item["code"]] = country

        bodies = {}
        for item in BODIES:
            country = countries[item["country"]]
            body, _ = GovernmentBody.objects.update_or_create(
                country=country,
                code=item["code"],
                defaults={
                    "name": item["name"],
                    "slug": item["code"],
                    "official_website": item["website"],
                    "is_active": True,
                },
            )
            bodies[item["code"]] = body

        jobs = {}
        for country_code, body_code, name, code in JOBS:
            country = countries[country_code]
            body = bodies[body_code]
            job, _ = GovernmentJob.objects.update_or_create(
                government_body=body,
                code=code,
                defaults={
                    "country": country,
                    "name": name,
                    "slug": code,
                    "description": f"Government recruitment target: {name}.",
                    "is_active": True,
                },
            )
            jobs[code] = job

        domain, _ = Domain.objects.update_or_create(
            organization=None,
            slug="government-exams",
            defaults={"name": "Government Exams", "is_active": True},
        )
        categories = {}
        for name, slug in SUBJECTS:
            category, _ = Category.objects.update_or_create(
                organization=None,
                slug=slug,
                defaults={"domain": domain, "name": name, "parent": None, "is_active": True},
            )
            categories[slug] = category

        for item in PROGRAMS:
            country = countries[item["country"]]
            body = bodies[item["body"]]
            program, _ = GovernmentExamProgram.objects.update_or_create(
                government_body=body,
                code=item["code"],
                defaults={
                    "country": country,
                    "content_vertical": vertical,
                    "name": item["name"],
                    "slug": item["code"],
                    "description": item["description"],
                    "official_website": item["website"],
                    "is_active": True,
                },
            )
            program.jobs.set([jobs[code] for code in item["jobs"]])

            primary_category = categories["general-awareness"]
            exam, _ = Exam.objects.update_or_create(
                title=f"{item['name']} — Practice & Mock Exam",
                defaults={
                    "organization": None,
                    "primary_category": primary_category,
                    "question_count": 20,
                    "duration_seconds": 1800,
                    "level": 2,
                    "passing_score": 60,
                    "is_published": True,
                    "max_mock_attempts": 3,
                    "allow_review": True,
                },
            )
            exam.categories.set(categories.values())
            ExamCategoryAllocation.objects.update_or_create(
                exam=exam,
                category=primary_category,
                defaults={"percentage": 100, "fixed_count": None, "include_descendants": True},
            )

            version, _ = GovernmentExamVersion.objects.update_or_create(
                program=program,
                version="catalog-v1",
                defaults={
                    "slug": f"{item['code']}-catalog-v1",
                    "status": GovernmentExamVersion.ACTIVE,
                    "official_syllabus_url": item["website"],
                    "official_notification_url": item["website"],
                    "notes": "Catalog metadata only. Verify the current official notification before using exam-specific requirements, syllabus or dates.",
                },
            )
            GovernmentExamStage.objects.update_or_create(
                version=version,
                code="practice-mock",
                defaults={
                    "exam": exam,
                    "name": "NPTOR Practice & Mock",
                    "order": 1,
                    "is_required": True,
                    "description": "NPTOR preparation assessment. This is not a claim about the official government recruitment stage structure.",
                    "is_active": True,
                },
            )

            track, _ = ExamTrack.objects.update_or_create(
                organization=None,
                slug=f"{item['code']}-track",
                defaults={
                    "title": f"{item['name']} Learning Track",
                    "description": item["description"],
                    "subscription_scope": ExamTrack.TRACK,
                    "pricing_type": ExamTrack.PRICING_FREE,
                    "trial_days": 7,
                    "currency": "INR",
                    "is_active": True,
                },
            )
            TrackExam.objects.update_or_create(
                track=track,
                exam=exam,
                defaults={"order": 1, "is_required": True},
            )

            course, _ = Course.objects.update_or_create(
                slug=f"{item['code']}-complete-preparation",
                defaults={
                    "title": f"{item['name']} — Complete Preparation",
                    "description": item["description"],
                    "category": primary_category,
                    "level": "intermediate",
                    "owner_type": Course.OWNER_PLATFORM,
                    "organization": None,
                    "is_public": True,
                    "is_published": True,
                    "approval_status": Course.APPROVAL_APPROVED,
                    "created_by": None,
                },
            )
            program.courses.add(course)

            section, _ = CourseSection.objects.update_or_create(
                course=course,
                order=1,
                defaults={"title": "Core Preparation", "is_visible": True},
            )
            Lesson.objects.update_or_create(
                section=section,
                order=1,
                defaults={
                    "title": "How to use this preparation path",
                    "lesson_type": Lesson.TYPE_ARTICLE,
                    "article_content": (
                        "<h2>Start here</h2>"
                        "<p>Study the relevant subjects, use NPTOR practice resources, and confirm all current official requirements from the recruiting authority before applying.</p>"
                    ),
                },
            )
            Lesson.objects.update_or_create(
                section=section,
                order=2,
                defaults={
                    "title": "Practice & Mock Exam",
                    "lesson_type": Lesson.TYPE_QUIZ,
                    "exam": exam,
                    "quiz_completion_mode": "attempt",
                    "quiz_allow_mock": True,
                    "quiz_max_attempts": 3,
                },
            )

        self.stdout.write(self.style.SUCCESS("Government catalog seeded successfully."))
        self.stdout.write("Countries: 3 | Bodies: 4 | Jobs: 8 | Programs: 8")
        self.stdout.write("Each program: 1 course + 1 track + 1 reusable practice/mock exam")
