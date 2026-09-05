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
    ExamTrack,
    GovernmentExamProgram,
    PreparationProgram,
    Question,
    TrackExam,
)


PROGRAMS = [
    ("academic", "MBA Entrance Preparation", "mba-entrance", "MBA entrance preparation"),
    ("academic", "MBBS Entrance Preparation", "mbbs-entrance", "MBBS entrance preparation"),
    ("academic", "IOE Entrance Preparation", "ioe-entrance", "IOE entrance preparation"),
    ("academic", "Class 11 Entrance Preparation", "class-11-entrance", "Class 11 entrance preparation"),
    ("professional", "SnowPro Core Preparation", "snowpro-core", "Snowflake professional certification preparation"),
    ("professional", "AWS Solutions Architect Preparation", "aws-solutions-architect", "AWS architecture certification preparation"),
    ("professional", "Azure Administrator Preparation", "azure-administrator", "Azure administration certification preparation"),
]

TAXONOMY = {
    "MBA": ["Quantitative Aptitude", "Logical Reasoning", "Verbal Ability", "Data Interpretation"],
    "MBBS": ["Biology", "Chemistry", "Physics", "Human Physiology"],
    "IOE": ["Mathematics", "Physics", "Chemistry", "English"],
    "Class 11": ["Mathematics", "Science", "English", "Logical Reasoning"],
    "Snowflake": ["Architecture", "Data Loading", "Performance", "Security"],
    "AWS": ["Compute", "Storage", "Networking", "Security"],
    "Azure": ["Identity", "Compute", "Storage", "Networking"],
    "Government": ["General Awareness", "Quantitative Aptitude", "Reasoning", "English Language"],
}

QUESTION_FIXTURES = [
    {"key": "single", "type": Question.SINGLE, "text": "Which data structure follows FIFO order?", "choices": [("Queue", True), ("Stack", False), ("Tree", False), ("Graph", False)]},
    {"key": "multi", "type": Question.MULTI, "text": "Which are valid examples of cloud storage services? Select all that apply.", "choices": [("Amazon S3", True), ("Azure Blob Storage", True), ("PostgreSQL", False), ("CPU cache", False)]},
    {"key": "tf", "type": Question.TRUE_FALSE, "text": "A primary key uniquely identifies a row in a relational table.", "choices": [("True", True), ("False", False)]},
    {"key": "dropdown", "type": Question.DROPDOWN, "text": "Which service is an object storage service?", "choices": [("Amazon S3", True), ("Amazon EC2", False), ("Amazon RDS", False), ("Amazon Route 53", False)]},
    {"key": "fill", "type": Question.FILL_BLANK, "text": "The SQL command used to retrieve rows from a table is ____.", "correct_text": "SELECT"},
    {"key": "numeric", "type": Question.NUMERIC, "text": "If a course has 5 sections and each section has 4 lessons, how many lessons are there?", "numeric_answer": 20, "numeric_tolerance": 0},
    {"key": "match", "type": Question.MATCHING, "text": "Match each cloud service with its primary purpose.", "matching_pairs": {"S3": "Object storage", "EC2": "Virtual compute", "RDS": "Managed relational database"}},
    {"key": "order", "type": Question.ORDERING, "text": "Put these software delivery steps in the usual order.", "ordering_items": ["Plan", "Develop", "Test", "Deploy"]},
]


class Command(BaseCommand):
    help = "Seed a complete original NPTOR demo catalog for end-to-end development testing."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("Preparing prerequisite government and preparation catalogs...")
        from django.core.management import call_command
        call_command("seed_government_catalog", verbosity=0)
        call_command("seed_preparation_programs", verbosity=0)

        verticals = self._verticals()
        countries = self._countries()
        domains = self._domains()
        categories = self._categories(domains)
        questions = self._questions(categories)
        exams = self._exams(categories)
        tracks = self._tracks(exams)
        prep_programs = self._preparation_programs(verticals, countries, exams)
        courses = self._courses(categories, exams, domains)
        self._link_programs(prep_programs, courses, exams)
        self._enrich_government_courses(categories, domains, exams)

        self.stdout.write(self.style.SUCCESS("Complete NPTOR demo catalog seeded successfully."))
        self.stdout.write(
            f"Domains: {Domain.objects.filter(organization=None).count()} | "
            f"Categories: {Category.objects.filter(organization=None).count()} | "
            f"Questions: {Question.objects.filter(organization=None, is_deleted=False).count()} | "
            f"Exams: {Exam.objects.filter(organization=None).count()} | "
            f"Tracks: {ExamTrack.objects.filter(organization=None).count()} | "
            f"Courses: {Course.objects.filter(organization=None).count()}"
        )

    def _verticals(self):
        values = {}
        data = [
            ("professional", "Professional Certification", ContentVertical.PROFESSIONAL_CERTIFICATION),
            ("government", "Government / Competitive Exam", ContentVertical.GOVERNMENT_EXAM),
            ("academic", "Academic Exam", ContentVertical.ACADEMIC_EXAM),
            ("skill", "Skill Assessment", ContentVertical.SKILL_ASSESSMENT),
        ]
        for code, name, vertical_type in data:
            values[code], _ = ContentVertical.objects.update_or_create(
                vertical_type=vertical_type,
                defaults={"name": name, "code": code.replace("_", "-"), "is_active": True},
            )
        return values

    def _countries(self):
        values = {}
        for name, code, slug in [("Nepal", "NPL", "nepal"), ("India", "IND", "india"), ("United States", "USA", "united-states")]:
            values[code], _ = Country.objects.update_or_create(
                code=code, defaults={"name": name, "slug": slug, "is_active": True}
            )
        return values

    def _domains(self):
        values = {}
        for key, name in [("MBA", "MBA Entrance"), ("MBBS", "MBBS Entrance"), ("IOE", "IOE Entrance"), ("Class 11", "Class 11 Entrance"), ("Snowflake", "Snowflake"), ("AWS", "AWS"), ("Azure", "Azure"), ("Government", "Government Exams")]:
            values[key], _ = Domain.objects.update_or_create(
                organization=None, slug=name.lower().replace(" ", "-").replace("/", "-"),
                defaults={"name": name, "is_active": True},
            )
        return values

    def _categories(self, domains):
        values = {}
        for group, names in TAXONOMY.items():
            domain = domains[group]
            root = None
            for name in names:
                slug = f"{domain.slug}-{name.lower().replace(' ', '-') }".replace(" ", "-")
                values[(group, name)], _ = Category.objects.update_or_create(
                    organization=None, slug=slug,
                    defaults={"domain": domain, "name": name, "parent": root, "is_active": True},
                )
        return values

    def _questions(self, categories):
        result = {}
        category = categories[("Snowflake", "Architecture")]
        for fixture in QUESTION_FIXTURES:
            question, _ = Question.objects.update_or_create(
                organization=None,
                primary_category=category,
                text=fixture["text"],
                defaults={
                    "question_type": fixture["type"],
                    "difficulty": Question.MEDIUM,
                    "is_active": True,
                    "is_deleted": False,
                    "correct_text": fixture.get("correct_text"),
                    "numeric_answer": fixture.get("numeric_answer"),
                    "numeric_tolerance": fixture.get("numeric_tolerance", 0),
                    "matching_pairs": fixture.get("matching_pairs"),
                    "ordering_items": fixture.get("ordering_items"),
                    "explanation": "Original NPTOR demo question used to exercise the assessment engine.",
                },
            )
            question.categories.set([category])
            if "choices" in fixture:
                question.choices.all().delete()
                Choice.objects.bulk_create([
                    Choice(question=question, text=text, is_correct=correct, order=i)
                    for i, (text, correct) in enumerate(fixture["choices"], 1)
                ])
            result[fixture["key"]] = question
        return result

    def _exams(self, categories):
        result = {}
        definitions = [
            ("mba", "MBA Entrance Mock Exam", "MBA", 20, 1800),
            ("mbbs", "MBBS Entrance Mock Exam", "MBBS", 20, 1800),
            ("ioe", "IOE Entrance Mock Exam", "IOE", 20, 1800),
            ("class11", "Class 11 Entrance Mock Exam", "Class 11", 20, 1500),
            ("snowflake", "SnowPro Core Practice Exam", "Snowflake", 30, 3600),
            ("aws", "AWS Solutions Architect Practice Exam", "AWS", 30, 3600),
            ("azure", "Azure Administrator Practice Exam", "Azure", 30, 3600),
        ]
        for key, title, group, count, duration in definitions:
            primary = categories[(group, TAXONOMY[group][0])]
            exam, _ = Exam.objects.update_or_create(
                organization=None, title=title,
                defaults={"primary_category": primary, "question_count": count, "duration_seconds": duration, "level": 2, "passing_score": 60, "is_published": True, "max_mock_attempts": 3, "allow_review": True},
            )
            exam.categories.set([categories[(group, n)] for n in TAXONOMY[group]])
            allocations = [25, 25, 25, 25]
            for n, percentage in zip(TAXONOMY[group], allocations):
                ExamCategoryAllocation.objects.update_or_create(
                    exam=exam, category=categories[(group, n)],
                    defaults={"percentage": percentage, "fixed_count": None, "include_descendants": True},
                )
            result[key] = exam
        return result

    def _tracks(self, exams):
        result = {}
        definitions = [
            ("mba-track", "MBA Entrance Track", "mba"),
            ("mbbs-track", "MBBS Entrance Track", "mbbs"),
            ("ioe-track", "IOE Entrance Track", "ioe"),
            ("class11-track", "Class 11 Entrance Track", "class11"),
            ("snowpro-track", "SnowPro Core Track", "snowflake"),
            ("aws-track", "AWS Solutions Architect Track", "aws"),
            ("azure-track", "Azure Administrator Track", "azure"),
        ]
        for slug, title, exam_key in definitions:
            track, _ = ExamTrack.objects.update_or_create(
                organization=None, slug=slug,
                defaults={"title": title, "description": f"Original NPTOR learning and assessment track for {title}.", "subscription_scope": ExamTrack.TRACK, "pricing_type": ExamTrack.PRICING_FREE, "trial_days": 7, "currency": "INR", "is_active": True},
            )
            TrackExam.objects.update_or_create(track=track, exam=exams[exam_key], defaults={"order": 1, "is_required": True})
            result[exam_key] = track
        return result

    def _preparation_programs(self, verticals, countries, exams):
        result = {}
        for group, name, slug, description in PROGRAMS:
            program, _ = PreparationProgram.objects.update_or_create(
                content_vertical=verticals[group], code=slug,
                defaults={"country": countries["NPL"], "name": name, "slug": slug, "description": f"Original NPTOR {description} catalog. Attach original courses, practice and mock exams for development testing.", "is_active": True, "is_published": True},
            )
            key = slug.split("-")[0]
            result[slug] = program
            exam_key = {"mba": "mba", "mbbs": "mbbs", "ioe": "ioe", "class": "class11", "snowpro": "snowflake", "aws": "aws", "azure": "azure"}.get(key)
            if exam_key:
                program.exams.add(exams[exam_key])
        return result

    def _courses(self, categories, exams, domains):
        result = {}
        definitions = [
            ("mba", "MBA Entrance Complete Preparation", "MBA", "mba"),
            ("mbbs", "MBBS Entrance Complete Preparation", "MBBS", "mbbs"),
            ("ioe", "IOE Entrance Complete Preparation", "IOE", "ioe"),
            ("class11", "Class 11 Entrance Complete Preparation", "Class 11", "class11"),
            ("snowflake", "SnowPro Core Complete Preparation", "Snowflake", "snowflake"),
            ("aws", "AWS Solutions Architect Complete Preparation", "AWS", "aws"),
            ("azure", "Azure Administrator Complete Preparation", "Azure", "azure"),
        ]
        for key, title, group, exam_key in definitions:
            category = categories[(group, TAXONOMY[group][0])]
            course, _ = Course.objects.update_or_create(
                slug=f"{key}-complete-preparation",
                defaults={"title": title, "description": f"Original NPTOR development course for {title}.", "category": category, "level": "intermediate", "owner_type": Course.OWNER_PLATFORM, "organization": None, "is_public": True, "is_published": True, "approval_status": Course.APPROVAL_APPROVED, "created_by": None},
            )
            self._course_content(course, domains[group], category, exams[exam_key])
            result[key] = course
        return result

    def _course_content(self, course, domain, category, exam):
        section1, _ = CourseSection.objects.update_or_create(course=course, order=1, defaults={"title": "Core Concepts", "is_visible": True})
        section2, _ = CourseSection.objects.update_or_create(course=course, order=2, defaults={"title": "Practice & Assessment", "is_visible": True})
        Lesson.objects.update_or_create(section=section1, order=1, defaults={"title": "Introduction and Study Strategy", "lesson_type": Lesson.TYPE_ARTICLE, "article_content": "<h2>Welcome to NPTOR</h2><p>This is original demo lesson content. Study the concepts, complete practice, then take the mock assessment.</p>"})
        Lesson.objects.update_or_create(section=section1, order=2, defaults={"title": "Concept Video", "lesson_type": Lesson.TYPE_VIDEO, "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"})
        Lesson.objects.update_or_create(section=section2, order=1, defaults={"title": "Targeted Practice", "lesson_type": Lesson.TYPE_PRACTICE, "practice_domain": domain, "practice_category": category, "practice_difficulty": "medium", "practice_threshold": 5, "practice_lock_filters": True, "practice_require_correct": False, "practice_min_accuracy": 60})
        Lesson.objects.update_or_create(section=section2, order=2, defaults={"title": "Mock Quiz", "lesson_type": Lesson.TYPE_QUIZ, "exam": exam, "quiz_completion_mode": "attempt", "quiz_min_score": 0, "quiz_allow_mock": True, "quiz_max_attempts": 3})

    def _link_programs(self, programs, courses, exams):
        mapping = {
            "mba-entrance": "mba", "mbbs-entrance": "mbbs", "ioe-entrance": "ioe", "class-11-entrance": "class11",
            "snowpro-core": "snowflake", "aws-solutions-architect": "aws", "azure-administrator": "azure",
        }
        for slug, course_key in mapping.items():
            if slug in programs:
                programs[slug].courses.add(courses[course_key])
                programs[slug].exams.add(exams[course_key])

    def _enrich_government_courses(self, categories, domains, exams):
        try:
            government_programs = GovernmentExamProgram.objects.filter(is_active=True).prefetch_related("courses")
        except Exception:
            return
        gov_domain = domains["Government"]
        gov_category = categories[("Government", "General Awareness")]
        gov_exam = exams["snowflake"]
        for program in government_programs:
            for course in program.courses.all():
                section1, _ = CourseSection.objects.update_or_create(course=course, order=1, defaults={"title": "Government Exam Fundamentals", "is_visible": True})
                section2, _ = CourseSection.objects.update_or_create(course=course, order=2, defaults={"title": "Practice & Mock", "is_visible": True})
                Lesson.objects.update_or_create(section=section1, order=1, defaults={"title": "Preparation Guide", "lesson_type": Lesson.TYPE_ARTICLE, "article_content": f"<h2>{program.name}</h2><p>Original NPTOR preparation guidance. Verify the current official notification and syllabus before relying on exam-specific requirements.</p>"})
                Lesson.objects.update_or_create(section=section1, order=2, defaults={"title": "Preparation Video", "lesson_type": Lesson.TYPE_VIDEO, "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"})
                Lesson.objects.update_or_create(section=section2, order=1, defaults={"title": "Government Practice", "lesson_type": Lesson.TYPE_PRACTICE, "practice_domain": gov_domain, "practice_category": gov_category, "practice_difficulty": "medium", "practice_threshold": 5, "practice_min_accuracy": 60})
                Lesson.objects.update_or_create(section=section2, order=2, defaults={"title": "Government Mock Quiz", "lesson_type": Lesson.TYPE_QUIZ, "exam": gov_exam, "quiz_completion_mode": "attempt", "quiz_allow_mock": True, "quiz_max_attempts": 3})
