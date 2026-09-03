from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.contrib.auth import get_user_model
from django.utils.text import slugify

from courses.models import Course, CourseSection, Lesson
from quiz.models import (
    Category,
    Choice,
    Domain,
    Exam,
    ExamCategoryAllocation,
    ExamTrack,
    Question,
)


PREFIX = "[DEMO]"
COURSE_SLUG = "demo-aws-cloud-course"
DOMAIN_SLUG = "demo-aws-cloud"
CATEGORY_SLUG = "demo-aws-cloud-fundamentals"
TRACK_SLUG = "demo-aws-cloud-course-track"
MID_EXAM_TITLE = f"{PREFIX} AWS Module Quiz"
FINAL_EXAM_TITLE = f"{PREFIX} AWS Final Assessment"


class Command(BaseCommand):
    help = "Create a complete demo course with text, video and exam lessons."

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            help="User to own the demo course. Defaults to the first superuser, then first active user.",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete the existing demo course and its demo learning data first.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["reset"]:
            self._reset()

        owner = self._get_owner(options.get("username"))
        domain = self._domain()
        category = self._category(domain)
        questions = self._questions(category)
        track = self._track()
        mid_exam = self._exam(
            title=MID_EXAM_TITLE,
            track=track,
            category=category,
            question_count=5,
            questions=questions[:5],
        )
        final_exam = self._exam(
            title=FINAL_EXAM_TITLE,
            track=track,
            category=category,
            question_count=10,
            questions=questions,
        )
        final_exam.prerequisite_exams.set([mid_exam])

        course = self._course(owner, category)
        sections = self._sections(course)
        lessons = self._lessons(sections, mid_exam, final_exam, domain, category)

        self.stdout.write(self.style.SUCCESS("Demo course created successfully."))
        self.stdout.write(f"Course: {course.title} ({course.slug})")
        self.stdout.write(f"Owner: {owner.get_username()}")
        self.stdout.write(f"Sections: {len(sections)}")
        self.stdout.write(f"Lessons: {len(lessons)}")
        self.stdout.write(f"Questions: {len(questions)}")
        self.stdout.write(f"Exams: 2 ({mid_exam.title}, {final_exam.title})")
        self.stdout.write("Reset/recreate: python manage.py seed_demo_course --reset")

    def _reset(self):
        Course.objects.filter(slug=COURSE_SLUG).delete()
        Exam.objects.filter(title__in=[MID_EXAM_TITLE, FINAL_EXAM_TITLE]).delete()
        ExamTrack.objects.filter(slug=TRACK_SLUG, organization=None).delete()
        Question.objects.filter(text__startswith=PREFIX).delete()
        Category.objects.filter(slug=CATEGORY_SLUG, organization=None).delete()
        Domain.objects.filter(slug=DOMAIN_SLUG, organization=None).delete()

    def _get_owner(self, username):
        User = get_user_model()
        if username:
            try:
                return User.objects.get(username=username)
            except User.DoesNotExist as exc:
                raise CommandError(f"User '{username}' does not exist.") from exc

        owner = User.objects.filter(is_superuser=True).order_by("id").first()
        owner = owner or User.objects.filter(is_active=True).order_by("id").first()
        if not owner:
            raise CommandError("No active user exists. Create a user first or pass --username.")
        return owner

    def _domain(self):
        domain, _ = Domain.objects.update_or_create(
            slug=DOMAIN_SLUG,
            organization=None,
            defaults={"name": f"{PREFIX} AWS Cloud", "is_active": True},
        )
        return domain

    def _category(self, domain):
        category, _ = Category.objects.update_or_create(
            slug=CATEGORY_SLUG,
            organization=None,
            defaults={
                "name": f"{PREFIX} AWS Cloud Fundamentals",
                "domain": domain,
                "parent": None,
                "is_active": True,
            },
        )
        return category

    def _questions(self, category):
        bank = [
            ("What is AWS primarily used for?", ["Cloud computing services", "Desktop publishing", "Email-only hosting", "Offline accounting"], 0),
            ("Which AWS service provides virtual servers?", ["Amazon EC2", "Amazon S3", "Amazon Route 53", "AWS IAM"], 0),
            ("Which AWS service is designed for object storage?", ["Amazon S3", "Amazon EC2", "Amazon RDS", "Amazon VPC"], 0),
            ("What does IAM help manage?", ["Users, roles and permissions", "Video encoding only", "DNS records only", "Database backups only"], 0),
            ("What is an AWS Region?", ["A geographic area containing multiple Availability Zones", "A single EC2 instance", "A billing document", "A user account"], 0),
            ("What is an Availability Zone?", ["An isolated location within an AWS Region", "A type of IAM policy", "An S3 object", "A pricing plan"], 0),
            ("Which service is a managed relational database service?", ["Amazon RDS", "Amazon S3", "Amazon CloudFront", "Amazon Route 53"], 0),
            ("Which AWS service provides DNS management?", ["Amazon Route 53", "Amazon EBS", "Amazon SQS", "Amazon SNS"], 0),
            ("What is an IAM role commonly used for?", ["Granting temporary permissions to trusted entities", "Storing large video files", "Running DNS queries", "Creating physical servers"], 0),
            ("Which AWS concept helps distribute workloads across isolated Availability Zones?", ["High availability architecture", "Single-instance architecture", "Local-only storage", "Manual billing"], 0),
        ]
        questions = []
        for index, (text, choices, correct) in enumerate(bank, start=1):
            question, _ = Question.objects.update_or_create(
                text=f"{PREFIX} {text}",
                defaults={
                    "primary_category": category,
                    "question_type": Question.SINGLE,
                    "difficulty": Question.EASY if index <= 5 else Question.MEDIUM,
                    "is_active": True,
                    "is_deleted": False,
                    "explanation": f"{PREFIX} Explanation: review the AWS Cloud Fundamentals lesson for the core concept behind this answer.",
                },
            )
            question.categories.set([category])
            Choice.objects.filter(question=question).delete()
            Choice.objects.bulk_create([
                Choice(
                    question=question,
                    text=choice,
                    is_correct=(choice_index == correct),
                    order=choice_index,
                )
                for choice_index, choice in enumerate(choices)
            ])
            questions.append(question)
        return questions

    def _track(self):
        track, _ = ExamTrack.objects.update_or_create(
            slug=TRACK_SLUG,
            organization=None,
            defaults={
                "title": f"{PREFIX} AWS Cloud Course Track",
                "description": "Demo exam track used by the demo course.",
                "subscription_scope": ExamTrack.TRACK,
                "pricing_type": ExamTrack.PRICING_FREE,
                "currency": "INR",
                "is_active": True,
            },
        )
        return track

    def _exam(self, title, track, category, question_count, questions):
        exam, _ = Exam.objects.update_or_create(
            title=title,
            defaults={
                "track": track,
                "primary_category": category,
                "question_count": question_count,
                "duration_seconds": 900 if question_count == 5 else 1800,
                "level": 1,
                "passing_score": 70,
                "is_free": True,
                "price": None,
                "currency": "INR",
                "is_published": True,
                "max_mock_attempts": 3,
                "allow_review": True,
            },
        )
        exam.categories.set([category])
        ExamCategoryAllocation.objects.update_or_create(
            exam=exam,
            category=category,
            defaults={
                "fixed_count": question_count,
                "percentage": None,
                "include_descendants": True,
            },
        )
        # The exam blueprint dynamically selects from the category. This
        # explicit validation keeps the seed self-checking and deterministic.
        if len(questions) < question_count:
            raise CommandError(f"Not enough demo questions for {title}.")
        return exam

    def _course(self, owner, category):
        course, _ = Course.objects.update_or_create(
            slug=COURSE_SLUG,
            defaults={
                "title": f"{PREFIX} AWS Cloud Practitioner — Demo Course",
                "description": (
                    "A complete demonstration course covering AWS cloud fundamentals "
                    "through text lessons, video lessons, a module quiz and a final assessment."
                ),
                "category": category,
                "level": "beginner",
                "owner_type": Course.OWNER_PLATFORM,
                "organization": None,
                "is_public": True,
                "is_published": True,
                "approval_status": Course.APPROVAL_APPROVED,
                "created_by": owner,
            },
        )
        return course

    def _sections(self, course):
        specs = [
            (1, "Cloud Fundamentals"),
            (2, "AWS Core Services"),
            (3, "Assessment"),
        ]
        sections = []
        for order, title in specs:
            section, _ = CourseSection.objects.update_or_create(
                course=course,
                order=order,
                defaults={"title": f"{PREFIX} {title}", "is_visible": True},
            )
            sections.append(section)
        return sections

    def _lessons(self, sections, mid_exam, final_exam, domain, category):
        specs = [
            (sections[0], 1, "What is Cloud Computing?", Lesson.TYPE_ARTICLE, "Cloud computing delivers computing resources over the internet. It provides on-demand access to compute, storage, networking and managed services without requiring you to own the underlying hardware.\n\nKey ideas: on-demand resources, elasticity, pay-as-you-go pricing, shared infrastructure and global availability."),
            (sections[0], 2, "AWS Cloud Basics — Video", Lesson.TYPE_VIDEO, "https://www.youtube.com/watch?v=ulprqHHWlng"),
            (sections[0], 3, "Regions and Availability Zones", Lesson.TYPE_ARTICLE, "An AWS Region is a geographic area containing multiple isolated Availability Zones. Designing across Availability Zones can improve availability and resilience.\n\nFor this demo, remember: Region = geographic area; Availability Zone = isolated location inside a Region."),
            (sections[1], 1, "EC2, S3 and RDS", Lesson.TYPE_ARTICLE, "Amazon EC2 provides virtual compute capacity. Amazon S3 provides object storage. Amazon RDS provides managed relational databases.\n\nA simple architecture may use EC2 for application compute, S3 for object assets and RDS for relational application data."),
            (sections[1], 2, "AWS Core Services — Video", Lesson.TYPE_VIDEO, "https://www.youtube.com/watch?v=3hLmDS179YE"),
            (sections[1], 3, "Identity and Access Management", Lesson.TYPE_ARTICLE, "AWS IAM controls authentication and authorization through users, groups, roles and policies. Apply least privilege: grant only the permissions required to perform a task."),
            (sections[2], 1, "Module Quiz", Lesson.TYPE_QUIZ, mid_exam),
            (sections[2], 2, "Final Assessment", Lesson.TYPE_QUIZ, final_exam),
        ]
        lessons = []
        for section, order, title, lesson_type, content in specs:
            defaults = {
                "title": f"{PREFIX} {title}",
                "lesson_type": lesson_type,
            }
            if lesson_type == Lesson.TYPE_ARTICLE:
                defaults["article_content"] = content
            elif lesson_type == Lesson.TYPE_VIDEO:
                defaults["video_url"] = content
            elif lesson_type == Lesson.TYPE_QUIZ:
                defaults.update({
                    "exam": content,
                    "quiz_completion_mode": "pass",
                    "quiz_min_score": 70,
                    "quiz_allow_mock": False,
                    "quiz_max_attempts": 3,
                })
            lesson, _ = Lesson.objects.update_or_create(
                section=section,
                order=order,
                defaults=defaults,
            )
            lessons.append(lesson)
        return lessons
