from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

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
    GovernmentExamVersion,
    Question,
)


QUESTIONS = [
    {
        "text": "नेपालको संविधान कहिले जारी भयो?",
        "choices": [
            ("२०७२ असोज ३", True),
            ("२०७१ असोज ३", False),
            ("२०७३ असोज ३", False),
            ("२०७४ असोज ३", False),
        ],
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
    help = "Seed the Nepal Lok Sewa Nayab Subba government exam and sample questions."

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
        version, _ = GovernmentExamVersion.objects.get_or_create(
            program=program,
            version="sample-2026",
            defaults={
                "slug": "sample-2026",
                "status": GovernmentExamVersion.ACTIVE,
                "notes": "NPTOR starter seed; verify against the latest official syllabus before production use.",
            },
        )

        domain, _ = Domain.objects.get_or_create(
            organization=None,
            slug="nepal-government-exams",
            defaults={"name": "Nepal Government Exams", "is_active": True, "content_vertical": vertical},
        )
        category, _ = Category.objects.get_or_create(
            organization=None,
            slug="nayab-subba-general-knowledge",
            defaults={
                "domain": domain,
                "name": "नायब सुब्बा – सामान्य ज्ञान",
                "is_active": True,
            },
        )

        exam, created = Exam.objects.get_or_create(
            title="लोक सेवा आयोग – नायब सुब्बा नमुना परीक्षा",
            organization=None,
            defaults={
                "question_count": len(QUESTIONS),
                "duration_seconds": 45 * 60,
                "level": 1,
                "passing_score": 45.0,
                "is_published": False,
                "max_mock_attempts": 3,
                "allow_review": True,
            },
        )
        exam.categories.add(category)
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
            question.categories.add(category)
            for order, (choice_text, is_correct) in enumerate(item["choices"], start=1):
                Choice.objects.get_or_create(
                    question=question,
                    text=choice_text,
                    defaults={"is_correct": is_correct, "order": order},
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded: {program.name}; version={version.version}; exam_id={exam.id}; questions={len(QUESTIONS)}"
            )
        )