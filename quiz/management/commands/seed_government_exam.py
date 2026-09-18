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
    ExamCategoryAllocation,
    GovernmentBody,
    GovernmentExamProgram,
    GovernmentExamStage,
    GovernmentExamVersion,
    GovernmentJob,
    Question,
)


QUESTIONS = [
    {
        "text": "नेपालको संविधान कहिले जारी भयो?",
        "choices": [("२०७२ असोज ३", True), ("२०७१ असोज ३", False), ("२०७३ असोज ३", False), ("२०७४ असोज ३", False)],
        "explanation": "नेपालको संविधान २०७२ असोज ३ गते जारी भएको हो।",
    },
    {
        "text": "नेपालको संघीय संसद् कति सदनात्मक छ?",
        "choices": [("एक", False), ("दुई", True), ("तीन", False), ("चार", False)],
        "explanation": "नेपालको संघीय संसद् प्रतिनिधि सभा र राष्ट्रिय सभा गरी दुई सदनात्मक छ।",
    },
    {
        "text": "नेपालको राष्ट्रिय फूल कुन हो?",
        "choices": [("गुराँस", True), ("कमल", False), ("सयपत्री", False), ("गोदावरी", False)],
        "explanation": "लालीगुराँस नेपालको राष्ट्रिय फूल हो।",
    },
    {
        "text": "नेपालमा स्थानीय तहको संख्या कति छ?",
        "choices": [("७५३", True), ("७४४", False), ("७७७", False), ("७०३", False)],
        "explanation": "नेपालमा ७५३ स्थानीय तह छन्।",
    },
    {
        "text": "लोक सेवा आयोग नेपालको संविधानको कुन भागमा व्यवस्था गरिएको छ?",
        "choices": [("भाग २१", False), ("भाग २२", True), ("भाग २३", False), ("भाग २४", False)],
        "explanation": "लोक सेवा आयोगसम्बन्धी व्यवस्था संविधानको भाग २२ मा छ।",
    },
]


class Command(BaseCommand):
    help = "Seed the Nepal Lok Sewa Nayab Subba government exam, job, course, stage, and sample questions."

    @transaction.atomic
    def handle(self, *args, **options):
        country, _ = Country.objects.get_or_create(
            code="NPL",
            defaults={"name": "Nepal", "slug": "nepal", "is_active": True},
        )
        vertical, _ = ContentVertical.objects.get_or_create(
            vertical_type=ContentVertical.GOVERNMENT_EXAM,
            defaults={
                "name": "Government / Competitive Exam",
                "code": "government-exam",
                "is_active": True,
            },
        )
        body, _ = GovernmentBody.objects.get_or_create(
            country=country,
            code="psc-nepal",
            defaults={
                "name": "लोक सेवा आयोग",
                "slug": "lok-sewa-aayog",
                "official_website": "https://psc.gov.np/",
                "is_active": True,
            },
        )
        program, _ = GovernmentExamProgram.objects.get_or_create(
            government_body=body,
            code="nayab-subba",
            defaults={
                "country": country,
                "content_vertical": vertical,
                "name": "लोक सेवा आयोग – नायब सुब्बा",
                "slug": "lok-sewa-nayab-subba",
                "description": "नेपालको लोक सेवा आयोगअन्तर्गत नायब सुब्बा पदको तयारी।",
                "official_website": "https://psc.gov.np/",
                "is_active": True,
            },
        )

        job, _ = GovernmentJob.objects.get_or_create(
            government_body=body,
            code="nayab-subba",
            defaults={
                "country": country,
                "name": "नायब सुब्बा",
                "slug": "nayab-subba",
                "description": "लोक सेवा आयोगअन्तर्गत नायब सुब्बा पद।",
                "is_active": True,
            },
        )
        job.country = country
        job.name = "नायब सुब्बा"
        job.slug = "nayab-subba"
        job.is_active = True
        job.save()
        program.jobs.add(job)

        version, _ = GovernmentExamVersion.objects.get_or_create(
            program=program,
            version="sample-2026",
            defaults={
                "slug": "sample-2026",
                "status": GovernmentExamVersion.ACTIVE,
                "notes": "NPTOR starter seed; verify against the latest official syllabus before production use.",
            },
        )
        version.slug = "sample-2026"
        version.status = GovernmentExamVersion.ACTIVE
        version.save()

        domain, _ = Domain.objects.get_or_create(
            organization=None,
            slug="nepal-government-exams",
            defaults={
                "name": "Nepal Government Exams",
                "is_active": True,
                "content_vertical": vertical,
            },
        )
        domain.is_active = True
        domain.content_vertical = vertical
        domain.save()

        category, _ = Category.objects.get_or_create(
            organization=None,
            slug="nayab-subba-general-knowledge",
            defaults={
                "domain": domain,
                "name": "नायब सुब्बा – सामान्य ज्ञान",
                "is_active": True,
            },
        )
        category.domain = domain
        category.name = "नायब सुब्बा – सामान्य ज्ञान"
        category.is_active = True
        category.save()

        exam, _ = Exam.objects.get_or_create(
            title="लोक सेवा आयोग – नायब सुब्बा नमुना परीक्षा",
            organization=None,
            defaults={
                "question_count": len(QUESTIONS),
                "duration_seconds": 45 * 60,
                "level": 1,
                "passing_score": 45.0,
                "is_published": True,
                "max_mock_attempts": 3,
                "allow_review": True,
            },
        )
        exam.question_count = len(QUESTIONS)
        exam.duration_seconds = 45 * 60
        exam.passing_score = 45.0
        exam.is_published = True
        exam.max_mock_attempts = 3
        exam.allow_review = True
        exam.categories.add(category)
        exam.save()
        ExamCategoryAllocation.objects.get_or_create(
            exam=exam,
            category=category,
            defaults={"fixed_count": len(QUESTIONS), "include_descendants": True},
        )

        for item in QUESTIONS:
            question, _ = Question.objects.get_or_create(
                primary_category=category,
                text=item["text"],
                defaults={
                    "question_type": Question.SINGLE,
                    "difficulty": Question.MEDIUM,
                    "is_active": True,
                    "is_deleted": False,
                    "explanation": item["explanation"],
                },
            )
            question.explanation = item["explanation"]
            question.is_active = True
            question.is_deleted = False
            question.categories.add(category)
            question.save()
            for order, (choice_text, is_correct) in enumerate(item["choices"], start=1):
                choice, _ = Choice.objects.get_or_create(
                    question=question,
                    text=choice_text,
                    defaults={"is_correct": is_correct, "order": order},
                )
                choice.is_correct = is_correct
                choice.order = order
                choice.save()

        stage, _ = GovernmentExamStage.objects.get_or_create(
            version=version,
            code="general-knowledge-paper-1",
            defaults={
                "exam": exam,
                "name": "प्रथम चरण – सामान्य ज्ञान",
                "order": 1,
                "is_required": True,
                "description": "नायब सुब्बा तयारीका लागि सामान्य ज्ञानको नमुना मूल्याङ्कन।",
                "is_active": True,
            },
        )
        stage.exam = exam
        stage.name = "प्रथम चरण – सामान्य ज्ञान"
        stage.order = 1
        stage.is_required = True
        stage.is_active = True
        stage.save()

        course, _ = Course.objects.get_or_create(
            slug="nayab-subba-exam-preparation",
            defaults={
                "title": "नायब सुब्बा परीक्षा तयारी – सम्पूर्ण पाठ्यक्रम",
                "description": "लोक सेवा आयोगको नायब सुब्बा परीक्षाका लागि NPTOR को प्रारम्भिक तयारी पाठ्यक्रम।",
                "category": domain,
                "level": "beginner",
                "owner_type": Course.OWNER_PLATFORM,
                "organization": None,
                "is_public": True,
                "is_published": True,
                "approval_status": Course.APPROVAL_APPROVED,
            },
        )
        course.title = "नायब सुब्बा परीक्षा तयारी – सम्पूर्ण पाठ्यक्रम"
        course.description = "लोक सेवा आयोगको नायब सुब्बा परीक्षाका लागि NPTOR को प्रारम्भिक तयारी पाठ्यक्रम।"
        course.category = domain
        course.level = "beginner"
        course.owner_type = Course.OWNER_PLATFORM
        course.organization = None
        course.is_public = True
        course.is_published = True
        course.approval_status = Course.APPROVAL_APPROVED
        course.save()
        program.courses.add(course)

        section, _ = CourseSection.objects.get_or_create(
            course=course,
            order=1,
            defaults={"title": "सामान्य ज्ञान तथा नमुना परीक्षा", "is_visible": True},
        )
        section.title = "सामान्य ज्ञान तथा नमुना परीक्षा"
        section.is_visible = True
        section.save()

        lesson, _ = Lesson.objects.get_or_create(
            section=section,
            order=1,
            defaults={
                "title": "नायब सुब्बा तयारीको परिचय",
                "lesson_type": Lesson.TYPE_ARTICLE,
                "article_content": "<p>यस पाठमा नायब सुब्बा परीक्षाको प्रारम्भिक तयारी र सामान्य ज्ञानका विषयहरू समेटिएका छन्।</p>",
            },
        )
        lesson.title = "नायब सुब्बा तयारीको परिचय"
        lesson.lesson_type = Lesson.TYPE_ARTICLE
        lesson.article_content = "<p>यस पाठमा नायब सुब्बा परीक्षाको प्रारम्भिक तयारी र सामान्य ज्ञानका विषयहरू समेटिएका छन्।</p>"
        lesson.exam = None
        lesson.practice_domain = None
        lesson.practice_category = None
        lesson.save()

        quiz_lesson, _ = Lesson.objects.get_or_create(
            section=section,
            order=2,
            defaults={
                "title": "सामान्य ज्ञान – नमुना परीक्षा",
                "lesson_type": Lesson.TYPE_QUIZ,
                "exam": exam,
                "quiz_allow_mock": True,
            },
        )
        quiz_lesson.title = "सामान्य ज्ञान – नमुना परीक्षा"
        quiz_lesson.lesson_type = Lesson.TYPE_QUIZ
        quiz_lesson.exam = exam
        quiz_lesson.quiz_allow_mock = True
        quiz_lesson.practice_domain = None
        quiz_lesson.practice_category = None
        quiz_lesson.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded: {program.name}; job={job.name}; version={version.version}; "
                f"course_id={course.id}; stage_id={stage.id}; exam_id={exam.id}; "
                f"questions={len(QUESTIONS)}"
            )
        )
