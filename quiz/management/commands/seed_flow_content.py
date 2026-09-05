from django.core.management.base import BaseCommand
from django.db import transaction

from courses.models import Course, CourseSection, Lesson
from quiz.models import (
    Category,
    Choice,
    Domain,
    GovernmentExamProgram,
    Question,
)


class Command(BaseCommand):
    help = "Seed the question pool and course lesson data required for end-to-end NPTOR flow testing."

    @transaction.atomic
    def handle(self, *args, **options):
        domains = {d.name: d for d in Domain.objects.filter(organization=None)}
        created = self.seed_question_pool(domains)
        government_courses = self.enrich_government_courses(domains)
        self.stdout.write(self.style.SUCCESS("Complete-flow content seeded successfully."))
        self.stdout.write(f"Question pool rows created/updated: {created}" )
        self.stdout.write(f"Government courses enriched: {government_courses}")

    def seed_question_pool(self, domains):
        total = 0
        for domain in Domain.objects.filter(organization=None, is_active=True):
            categories = list(domain.categories.filter(organization=None, is_active=True))
            for category in categories:
                for number in range(1, 6):
                    text = f"{domain.name} — {category.name}: Which option best represents the primary focus of this topic in this NPTOR demo?"
                    question, _ = Question.objects.update_or_create(
                        organization=None,
                        primary_category=category,
                        text=f"{text} #{number}",
                        defaults={
                            "question_type": Question.SINGLE,
                            "difficulty": (Question.EASY, Question.MEDIUM, Question.HARD)[(number - 1) % 3],
                            "is_active": True,
                            "is_deleted": False,
                            "correct_text": None,
                            "numeric_answer": None,
                            "numeric_tolerance": 0,
                            "matching_pairs": None,
                            "ordering_items": None,
                            "explanation": "Original NPTOR demo question. The correct choice names the category being tested.",
                        },
                    )
                    question.categories.set([category])
                    question.choices.all().delete()
                    options = [
                        category.name,
                        f"{domain.name} administration",
                        "Unrelated system configuration",
                        "Database backup scheduling",
                    ]
                    Choice.objects.bulk_create([
                        Choice(question=question, text=value, is_correct=(i == 0), order=i)
                        for i, value in enumerate(options)
                    ])
                    total += 1
        return total

    def enrich_government_courses(self, domains):
        government_domain = domains.get("Government Exams")
        if not government_domain:
            return 0
        category = government_domain.categories.filter(organization=None, is_active=True).first()
        count = 0
        for program in GovernmentExamProgram.objects.filter(is_active=True).prefetch_related("courses"):
            stage = (
                program.versions.filter(status="active")
                .prefetch_related("stages")
                .first()
            )
            exam = None
            if stage:
                stage_obj = stage.stages.filter(is_active=True).select_related("exam").first()
                exam = stage_obj.exam if stage_obj else None
            for course in program.courses.all():
                self.add_course_content(course, program.name, government_domain, category, exam)
                count += 1
        return count

    def add_course_content(self, course, program_name, domain, category, exam):
        section1, _ = CourseSection.objects.update_or_create(
            course=course,
            order=1,
            defaults={"title": "Fundamentals & Strategy", "is_visible": True},
        )
        section2, _ = CourseSection.objects.update_or_create(
            course=course,
            order=2,
            defaults={"title": "Practice & Mock Assessment", "is_visible": True},
        )
        Lesson.objects.update_or_create(
            section=section1,
            order=1,
            defaults={
                "title": "Preparation Guide",
                "lesson_type": Lesson.TYPE_ARTICLE,
                "article_content": (
                    f"<h2>{program_name}</h2>"
                    "<p>This original NPTOR lesson introduces a structured preparation workflow. "
                    "Check the current official notification and syllabus before relying on recruitment-specific requirements.</p>"
                ),
            },
        )
        Lesson.objects.update_or_create(
            section=section1,
            order=2,
            defaults={
                "title": "Preparation Video",
                "lesson_type": Lesson.TYPE_VIDEO,
                "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            },
        )
        Lesson.objects.update_or_create(
            section=section2,
            order=1,
            defaults={
                "title": "Targeted Practice",
                "lesson_type": Lesson.TYPE_PRACTICE,
                "practice_domain": domain,
                "practice_category": category,
                "practice_difficulty": "medium",
                "practice_threshold": 5,
                "practice_lock_filters": True,
                "practice_require_correct": False,
                "practice_min_accuracy": 60,
            },
        )
        if exam:
            Lesson.objects.update_or_create(
                section=section2,
                order=2,
                defaults={
                    "title": "Program Mock Quiz",
                    "lesson_type": Lesson.TYPE_QUIZ,
                    "exam": exam,
                    "quiz_completion_mode": "attempt",
                    "quiz_min_score": 0,
                    "quiz_allow_mock": True,
                    "quiz_max_attempts": 3,
                },
            )
