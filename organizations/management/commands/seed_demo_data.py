from datetime import date

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from courses.models import Course
from organizations.models import (
    AcademicYear,
    ClassSection,
    ClassTeacher,
    Organization,
    OrganizationClass,
    OrganizationMember,
    OrganizationStudent,
    StudentEnrollment,
)
from organizations.services.assignments import assign_resource
from quiz.models import Category, Choice, Domain, Exam, ExamTrack, Question, TrackExam


User = get_user_model()


class Command(BaseCommand):
    help = "Create a complete, repeatable NPTOR demo organization and learning dataset."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            default="NptorDemo123!",
            help="Password assigned to all demo users (development/demo use only).",
        )
        parser.add_argument(
            "--no-assignments",
            action="store_true",
            help="Do not create sample course/track/exam assignments.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        password = options["password"]
        today = timezone.localdate()

        users = self._create_users(password)
        organization = self._create_organization(users["owner"])
        self._create_memberships(organization, users)
        academic_year, sections = self._create_academics(organization, today, users["teacher"])
        students = self._create_students(organization, users, academic_year, sections)
        domain, categories = self._create_catalog(organization)
        courses = self._create_courses(organization, users["teacher"], categories)
        tracks = self._create_tracks(organization)
        exams = self._create_exams(organization, users["teacher"], categories, tracks)
        questions = self._create_questions(organization, users["teacher"], categories)

        if not options["no_assignments"]:
            self._create_assignments(organization, users["teacher"], students, courses, tracks, exams)

        self.stdout.write(self.style.SUCCESS("Demo dataset created/updated successfully."))
        self.stdout.write("")
        self.stdout.write(f"Organization: {organization.name} ({organization.slug})")
        self.stdout.write("Demo users:")
        for key, user in users.items():
            role = {
                "platform_admin": "Platform Admin",
                "owner": "Organization Owner",
                "admin": "Organization Admin",
                "teacher": "Staff / Teacher",
            }.get(key, "Student")
            self.stdout.write(f"  {role}: {user.username} / {password}")
        self.stdout.write("")
        self.stdout.write(
            f"Created/reused: {len(students)} students, {len(courses)} courses, "
            f"{len(tracks)} tracks, {len(exams)} exams, {len(questions)} questions, "
            f"{len(categories)} categories, 1 domain."
        )
        if options["no_assignments"]:
            self.stdout.write("Sample assignments were skipped (--no-assignments).")
        else:
            self.stdout.write("Sample course/track/exam assignments were created/reused.")

    def _user(self, username, email, first_name, last_name, password, *, staff=False, superuser=False):
        user, _ = User.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "is_staff": staff,
                "is_superuser": superuser,
            },
        )
        changed = []
        for field, value in {
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "is_staff": staff,
            "is_superuser": superuser,
        }.items():
            if getattr(user, field) != value:
                setattr(user, field, value)
                changed.append(field)
        user.set_password(password)
        changed.append("password")
        user.save(update_fields=list(dict.fromkeys(changed)))
        return user

    def _create_users(self, password):
        return {
            "platform_admin": self._user("demo_platform_admin", "platform-admin@demo.nptor.local", "Platform", "Admin", password, staff=True, superuser=True),
            "owner": self._user("demo_owner", "owner@demo.nptor.local", "Demo", "Owner", password),
            "admin": self._user("demo_admin", "admin@demo.nptor.local", "Demo", "Admin", password),
            "teacher": self._user("demo_teacher", "teacher@demo.nptor.local", "Demo", "Teacher", password),
            "student1": self._user("demo_student1", "student1@demo.nptor.local", "Aarav", "Sharma", password),
            "student2": self._user("demo_student2", "student2@demo.nptor.local", "Ananya", "Thapa", password),
            "student3": self._user("demo_student3", "student3@demo.nptor.local", "Rohan", "Karki", password),
        }

    def _create_organization(self, owner):
        organization, _ = Organization.objects.update_or_create(
            slug="demo-academy",
            defaults={
                "name": "NPTOR Demo Academy",
                "org_type": Organization.TYPE_INSTITUTE,
                "is_active": True,
                "created_by": owner,
                "primary_color": "#3273dc",
            },
        )
        return organization

    def _create_memberships(self, organization, users):
        roles = {
            "owner": OrganizationMember.ROLE_OWNER,
            "admin": OrganizationMember.ROLE_ADMIN,
            "teacher": OrganizationMember.ROLE_STAFF,
            "student1": OrganizationMember.ROLE_STUDENT,
            "student2": OrganizationMember.ROLE_STUDENT,
            "student3": OrganizationMember.ROLE_STUDENT,
        }
        for key, role in roles.items():
            OrganizationMember.objects.update_or_create(
                organization=organization,
                user=users[key],
                defaults={"role": role, "is_active": True},
            )

    def _create_academics(self, organization, today, teacher):
        year_name = f"{today.year}-{today.year + 1}"
        academic_year, _ = AcademicYear.objects.update_or_create(
            organization=organization,
            name=year_name,
            defaults={
                "start_date": date(today.year, 4, 1),
                "end_date": date(today.year + 1, 3, 31),
                "is_current": True,
            },
        )
        OrganizationClass.objects.filter(organization=organization).update(is_active=True)
        class_a, _ = OrganizationClass.objects.update_or_create(
            organization=organization,
            name="Data Analytics",
            defaults={"code": "DA", "description": "Demo data analytics class", "is_active": True},
        )
        class_b, _ = OrganizationClass.objects.update_or_create(
            organization=organization,
            name="Business Intelligence",
            defaults={"code": "BI", "description": "Demo business intelligence class", "is_active": True},
        )
        section_a, _ = ClassSection.objects.update_or_create(
            academic_year=academic_year,
            class_group=class_a,
            name="A",
            defaults={"organization": organization, "capacity": 30, "is_active": True},
        )
        section_b, _ = ClassSection.objects.update_or_create(
            academic_year=academic_year,
            class_group=class_b,
            name="A",
            defaults={"organization": organization, "capacity": 30, "is_active": True},
        )
        for section, subject in ((section_a, "Data Analytics"), (section_b, "Business Intelligence")):
            ClassTeacher.objects.update_or_create(
                teacher=teacher,
                class_section=section,
                subject=subject,
                defaults={"organization": organization, "academic_year": academic_year, "is_primary": True, "is_active": True},
            )
        return academic_year, {"data": section_a, "bi": section_b}

    def _create_students(self, organization, users, academic_year, sections):
        students = []
        for index, key in enumerate(("student1", "student2", "student3"), start=1):
            student, _ = OrganizationStudent.objects.update_or_create(
                organization=organization,
                user=users[key],
                defaults={
                    "student_id": f"DEMO-{index:03d}",
                    "admission_no": f"ADM-{2026}-{index:03d}",
                    "date_of_birth": date(2010 + index, 5, 10 + index),
                    "guardian_name": f"Guardian {index}",
                    "guardian_phone": f"+9199000000{index:02d}",
                    "address": "Demo City",
                    "status": OrganizationStudent.STATUS_ACTIVE,
                    "joined_date": academic_year.start_date,
                },
            )
            section = sections["data"] if index < 3 else sections["bi"]
            StudentEnrollment.objects.update_or_create(
                student=student,
                academic_year=academic_year,
                class_section=section,
                defaults={"roll_number": str(index), "status": StudentEnrollment.STATUS_ACTIVE},
            )
            students.append(student)
        return students

    def _create_catalog(self, organization):
        domain, _ = Domain.objects.update_or_create(
            organization=organization,
            slug="data-analytics",
            defaults={"name": "Data Analytics", "is_active": True},
        )
        definitions = [
            ("SQL", "sql", None),
            ("Python", "python", None),
            ("Snowflake", "snowflake", None),
            ("ETL", "etl", None),
        ]
        categories = []
        for name, slug, parent in definitions:
            category, _ = Category.objects.update_or_create(
                organization=organization,
                slug=slug,
                defaults={"name": name, "domain": domain, "parent": parent, "is_active": True},
            )
            categories.append(category)
        return domain, categories

    def _create_courses(self, organization, teacher, categories):
        definitions = [
            ("SQL Fundamentals", "beginner", categories[0]),
            ("Python for Data Analysis", "intermediate", categories[1]),
            ("Snowflake Data Engineering", "advanced", categories[2]),
        ]
        courses = []
        for title, level, category in definitions:
            course, _ = Course.objects.update_or_create(
                slug=slugify(f"demo-{title}"),
                defaults={
                    "title": title,
                    "description": f"Demo course: {title}",
                    "category": category,
                    "level": level,
                    "owner_type": Course.OWNER_ORGANIZATION,
                    "organization": organization,
                    "created_by": teacher,
                    "is_public": False,
                    "is_published": True,
                    "approval_status": Course.APPROVAL_APPROVED,
                },
            )
            courses.append(course)
        return courses

    def _create_tracks(self, organization):
        definitions = [
            ("Data Analyst Certification", "data-analyst-certification"),
            ("BI Engineer Certification", "bi-engineer-certification"),
        ]
        tracks = []
        for title, slug in definitions:
            track, _ = ExamTrack.objects.update_or_create(
                organization=organization,
                slug=slug,
                defaults={
                    "title": title,
                    "description": f"Demo track: {title}",
                    "subscription_scope": ExamTrack.TRACK,
                    "pricing_type": ExamTrack.PRICING_FREE,
                    "currency": "INR",
                    "is_active": True,
                },
            )
            tracks.append(track)
        return tracks

    def _create_exams(self, organization, teacher, categories, tracks):
        definitions = [
            ("SQL Fundamentals Assessment", categories[0], tracks[0]),
            ("Snowflake Engineering Assessment", categories[2], tracks[1]),
        ]
        exams = []
        for index, (title, category, track) in enumerate(definitions, start=1):
            exam, _ = Exam.objects.update_or_create(
                organization=organization,
                title=title,
                defaults={
                    "primary_category": category,
                    "question_count": 5,
                    "duration_seconds": 1800,
                    "level": index,
                    "passing_score": 60,
                    "is_published": True,
                    "max_mock_attempts": 3,
                    "allow_review": True,
                    "created_by": teacher,
                },
            )
            TrackExam.objects.update_or_create(
                track=track,
                exam=exam,
                defaults={"order": 1, "is_required": True},
            )
            exams.append(exam)
        return exams

    def _create_questions(self, organization, teacher, categories):
        definitions = [
            ("Which SQL clause filters rows before grouping?", "WHERE", ["WHERE", "HAVING", "GROUP BY", "ORDER BY"], categories[0]),
            ("Which Python library is commonly used for tabular data analysis?", "Pandas", ["Django", "Pandas", "Flask", "Requests"], categories[1]),
            ("What is Snowflake primarily used for?", "Cloud data warehousing", ["Image editing", "Cloud data warehousing", "Web hosting", "Email delivery"], categories[2]),
            ("What does ETL stand for?", "Extract, Transform, Load", ["Extract, Transform, Load", "Evaluate, Test, Launch", "Encode, Transfer, Link", "Execute, Track, Log"], categories[3]),
            ("Which SQL keyword removes duplicate rows from a result?", "DISTINCT", ["UNIQUE", "DISTINCT", "DEDUP", "ONLY"], categories[0]),
        ]
        questions = []
        for text, correct, choices, category in definitions:
            question, _ = Question.objects.update_or_create(
                organization=organization,
                text=text,
                defaults={
                    "primary_category": category,
                    "question_type": Question.SINGLE,
                    "difficulty": Question.MEDIUM,
                    "is_active": True,
                    "is_deleted": False,
                    "explanation": f"Correct answer: {correct}.",
                    "created_by": teacher,
                    "updated_by": teacher,
                },
            )
            question.categories.set([category])
            for order, choice_text in enumerate(choices, start=1):
                Choice.objects.update_or_create(
                    question=question,
                    order=order,
                    defaults={"text": choice_text, "is_correct": choice_text == correct},
                )
            questions.append(question)
        return questions

    def _create_assignments(self, organization, teacher, students, courses, tracks, exams):
        resource_sets = [
            ("course", courses[0]),
            ("track", tracks[0]),
            ("exam", exams[0]),
        ]
        for student in students:
            for resource_type, resource in resource_sets:
                try:
                    assign_resource(
                        student=student.user,
                        organization=organization,
                        resource_type=resource_type,
                        resource_id=resource.id,
                        actor=teacher,
                        notes="Seeded demo assignment.",
                    )
                except Exception as exc:
                    # The command is idempotent; an already-active assignment is expected.
                    if "already assigned" not in str(exc).lower():
                        raise
