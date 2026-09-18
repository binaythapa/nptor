from django.core.management.base import BaseCommand
from django.db import transaction

from courses.models import Course, CourseSection, Lesson
from quiz.models import (
    Category,
    Choice,
    ContentVertical,
    Country,
    Domain,
    Exam,
    ExamTrack,
    PreparationProgram,
    Question,
    TrackExam,
)


QUESTIONS = [
    ("What is the value of 12 × 8?", [("96", True), ("86", False), ("108", False), ("88", False)]),
    ("Which planet is known as the Red Planet?", [("Mars", True), ("Venus", False), ("Jupiter", False), ("Mercury", False)]),
    ("Choose the synonym of 'rapid'.", [("Fast", True), ("Slow", False), ("Weak", False), ("Late", False)]),
]


class Command(BaseCommand):
    help = "Seed sample academic and entrance preparation data."

    @transaction.atomic
    def handle(self, *args, **options):
        country, _ = Country.objects.get_or_create(
            code="NPL",
            defaults={"name": "Nepal", "slug": "nepal", "is_active": True},
        )
        vertical, _ = ContentVertical.objects.get_or_create(
            vertical_type=ContentVertical.ACADEMIC_EXAM,
            defaults={
                "name": "Academic & Entrance",
                "code": "academic-entrance",
                "is_active": True,
            },
        )
        vertical.name = "Academic & Entrance"
        vertical.code = "academic-entrance"
        vertical.is_active = True
        vertical.save()

        program, _ = PreparationProgram.objects.get_or_create(
            content_vertical=vertical,
            code="tu-bachelor-entrance",
            defaults={
                "country": country,
                "name": "Tribhuvan University – Bachelor Entrance Preparation",
                "slug": "tu-bachelor-entrance",
                "description": "Sample preparation program for bachelor-level entrance examinations.",
                "official_website": "https://tu.edu.np/",
                "is_active": True,
                "is_published": True,
            },
        )
        program.country = country
        program.name = "Tribhuvan University – Bachelor Entrance Preparation"
        program.description = "Sample preparation program for bachelor-level entrance examinations."
        program.is_active = True
        program.is_published = True
        program.save()

        domain, _ = Domain.objects.get_or_create(
            organization=None,
            slug="academic-entrance-preparation",
            defaults={"name": "Academic & Entrance Preparation", "is_active": True, "content_vertical": vertical},
        )
        domain.name = "Academic & Entrance Preparation"
        domain.is_active = True
        domain.content_vertical = vertical
        domain.save()

        category, _ = Category.objects.get_or_create(
            organization=None,
            slug="general-entrance-aptitude",
            defaults={"domain": domain, "name": "General Entrance Aptitude", "is_active": True},
        )
        category.domain = domain
        category.name = "General Entrance Aptitude"
        category.is_active = True
        category.save()

        exam, _ = Exam.objects.get_or_create(
            title="Bachelor Entrance – General Aptitude Mock Test",
            organization=None,
            defaults={
                "question_count": len(QUESTIONS),
                "duration_seconds": 30 * 60,
                "level": 1,
                "passing_score": 50.0,
                "is_published": True,
                "max_mock_attempts": 3,
                "allow_review": True,
            },
        )
        exam.question_count = len(QUESTIONS)
        exam.duration_seconds = 30 * 60
        exam.passing_score = 50.0
        exam.is_published = True
        exam.max_mock_attempts = 3
        exam.allow_review = True
        exam.categories.add(category)
        exam.save()

        for index, (text, choices) in enumerate(QUESTIONS, start=1):
            question, _ = Question.objects.get_or_create(
                primary_category=category,
                text=text,
                defaults={"question_type": Question.SINGLE, "difficulty": Question.MEDIUM, "is_active": True, "is_deleted": False},
            )
            question.is_active = True
            question.is_deleted = False
            question.categories.add(category)
            question.save()
            for order, (choice_text, is_correct) in enumerate(choices, start=1):
                choice, _ = Choice.objects.get_or_create(question=question, text=choice_text, defaults={"is_correct": is_correct, "order": order})
                choice.is_correct = is_correct
                choice.order = order
                choice.save()

        course, _ = Course.objects.get_or_create(
            slug="tu-bachelor-entrance-preparation",
            defaults={
                "title": "Bachelor Entrance Preparation – General Aptitude",
                "description": "Foundational preparation for bachelor-level entrance examinations.",
                "category": domain,
                "level": "beginner",
                "owner_type": Course.OWNER_PLATFORM,
                "organization": None,
                "is_public": True,
                "is_published": True,
                "approval_status": Course.APPROVAL_APPROVED,
            },
        )
        course.title = "Bachelor Entrance Preparation – General Aptitude"
        course.description = "Foundational preparation for bachelor-level entrance examinations."
        course.category = domain
        course.level = "beginner"
        course.owner_type = Course.OWNER_PLATFORM
        course.organization = None
        course.is_public = True
        course.is_published = True
        course.approval_status = Course.APPROVAL_APPROVED
        course.save()
        program.courses.add(course)

        section, _ = CourseSection.objects.get_or_create(course=course, order=1, defaults={"title": "General Aptitude", "is_visible": True})
        section.title = "General Aptitude"
        section.is_visible = True
        section.save()
        lesson, _ = Lesson.objects.get_or_create(section=section, order=1, defaults={"title": "General Aptitude Mock Test", "lesson_type": Lesson.TYPE_QUIZ, "exam": exam, "quiz_allow_mock": True})
        lesson.title = "General Aptitude Mock Test"
        lesson.lesson_type = Lesson.TYPE_QUIZ
        lesson.exam = exam
        lesson.quiz_allow_mock = True
        lesson.save()

        track, _ = ExamTrack.objects.get_or_create(organization=None, slug="tu-bachelor-entrance-track", defaults={"title": "Bachelor Entrance Preparation Track", "description": "A guided track for general bachelor entrance preparation.", "subscription_scope": ExamTrack.TRACK, "pricing_type": ExamTrack.PRICING_FREE, "is_active": True})
        track.title = "Bachelor Entrance Preparation Track"
        track.description = "A guided track for general bachelor entrance preparation."
        track.is_active = True
        track.save()
        TrackExam.objects.get_or_create(track=track, exam=exam, defaults={"order": 1, "is_required": True})
        program.exams.add(exam)

        self.stdout.write(self.style.SUCCESS(f"Seeded academic/entrance data: program_id={program.id}, course_id={course.id}, track_id={track.id}, exam_id={exam.id}, questions={len(QUESTIONS)}"))
