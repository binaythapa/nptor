from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from courses.models import Course, CourseSection, Lesson
from quiz.models import Category, Domain, Exam


COURSE_SLUG = "snowpro-core-certification-preparation"
COURSE_TITLE = "SnowPro Core Certification Preparation"
DOMAIN_SLUG = "snowflake"
EXAM_TITLE = "Snowflake | SnowPro Core Practice Exam"
CONTENT_PREFIX = "SnowPro Core | "


SECTIONS = [
    {
        "title": "Snowflake Architecture",
        "lessons": [
            {
                "title": "Snowflake Architecture Fundamentals",
                "type": Lesson.TYPE_ARTICLE,
                "content": """
                    <h2>Snowflake's Architecture</h2>
                    <p>Snowflake separates storage, compute, and cloud services. This separation allows teams to scale query compute independently from the data stored in Snowflake.</p>
                    <h3>Core layers</h3>
                    <ul>
                        <li><strong>Database storage:</strong> Stores table data in automatically managed micro-partitions.</li>
                        <li><strong>Compute:</strong> Virtual warehouses execute SQL and other workloads.</li>
                        <li><strong>Cloud services:</strong> Provides authentication, metadata management, query parsing, optimization, and coordination.</li>
                    </ul>
                    <p>Remember that a virtual warehouse consumes credits while running, whereas storage and cloud-services usage are managed separately.</p>
                """,
            },
            {
                "title": "Snowflake Architecture Video Resource",
                "type": Lesson.TYPE_VIDEO,
                "video_url": "https://www.youtube.com/results?search_query=Snowflake+architecture+virtual+warehouses",
            },
            {
                "title": "Architecture Practice",
                "type": Lesson.TYPE_PRACTICE,
                "practice_category": "architecture",
                "difficulty": "easy",
            },
        ],
    },
    {
        "title": "Storage and Data Organization",
        "lessons": [
            {
                "title": "Databases, Schemas, Tables, and Micro-partitions",
                "type": Lesson.TYPE_ARTICLE,
                "content": """
                    <h2>Storage and Data Organization</h2>
                    <p>A database contains schemas, and schemas contain objects such as tables, views, stages, file formats, tasks, and streams.</p>
                    <p>Snowflake automatically stores table data in micro-partitions. Micro-partitions contain metadata that can help Snowflake prune unnecessary data during query execution.</p>
                    <h3>Important concepts</h3>
                    <ul>
                        <li>Micro-partitions are managed automatically.</li>
                        <li>Clustering can improve pruning for suitable large tables.</li>
                        <li>Time Travel enables access to historical data within the retention period.</li>
                        <li>Fail-safe is a separate, limited recovery period managed by Snowflake.</li>
                        <li>Zero-copy cloning initially shares underlying storage rather than duplicating all data.</li>
                    </ul>
                """,
            },
            {
                "title": "Storage Concepts Video Resource",
                "type": Lesson.TYPE_VIDEO,
                "video_url": "https://www.youtube.com/results?search_query=Snowflake+micro+partitions+Time+Travel+zero+copy+cloning",
            },
            {
                "title": "Storage Practice",
                "type": Lesson.TYPE_PRACTICE,
                "practice_category": "storage",
                "difficulty": "easy",
            },
        ],
    },
    {
        "title": "Virtual Warehouses and Performance",
        "lessons": [
            {
                "title": "Compute, Warehouses, and Query Performance",
                "type": Lesson.TYPE_ARTICLE,
                "content": """
                    <h2>Compute and Performance</h2>
                    <p>A virtual warehouse is a cluster of compute resources used to execute SQL statements and other supported workloads.</p>
                    <h3>Performance controls</h3>
                    <ul>
                        <li><strong>Resize:</strong> Changes the compute resources available to a warehouse cluster.</li>
                        <li><strong>Auto-suspend:</strong> Stops an idle warehouse after a configured period.</li>
                        <li><strong>Auto-resume:</strong> Starts a suspended warehouse when eligible work arrives.</li>
                        <li><strong>Multi-cluster warehouses:</strong> Add clusters to help handle concurrency and reduce queuing.</li>
                        <li><strong>Query Profile:</strong> Helps identify scans, joins, spills, and other execution bottlenecks.</li>
                    </ul>
                    <p>Resizing generally helps a single workload obtain more resources; multi-cluster configuration is intended primarily for concurrency.</p>
                """,
            },
            {
                "title": "Warehouse Performance Video Resource",
                "type": Lesson.TYPE_VIDEO,
                "video_url": "https://www.youtube.com/results?search_query=Snowflake+virtual+warehouse+performance+optimization",
            },
            {
                "title": "Performance Practice",
                "type": Lesson.TYPE_PRACTICE,
                "practice_category": "compute",
                "difficulty": "medium",
            },
        ],
    },
    {
        "title": "Data Loading and Pipelines",
        "lessons": [
            {
                "title": "Stages, COPY INTO, Snowpipe, and Tasks",
                "type": Lesson.TYPE_ARTICLE,
                "content": """
                    <h2>Data Loading and Pipelines</h2>
                    <p>Snowflake supports bulk loading and continuous ingestion patterns.</p>
                    <ul>
                        <li><strong>Internal stages:</strong> Store files inside Snowflake-managed storage.</li>
                        <li><strong>External stages:</strong> Reference files in supported cloud storage locations.</li>
                        <li><strong>PUT:</strong> Uploads local files to an internal stage from supported clients.</li>
                        <li><strong>COPY INTO:</strong> Loads staged files into a table or unloads table data to a stage.</li>
                        <li><strong>Snowpipe:</strong> Supports continuous or near-real-time file ingestion.</li>
                        <li><strong>Streams and tasks:</strong> Support change tracking and scheduled or event-driven processing patterns.</li>
                    </ul>
                    <p>File formats define how structured and semi-structured files are interpreted during loading.</p>
                """,
            },
            {
                "title": "Data Loading Video Resource",
                "type": Lesson.TYPE_VIDEO,
                "video_url": "https://www.youtube.com/results?search_query=Snowflake+COPY+INTO+Snowpipe+data+loading",
            },
            {
                "title": "Data Loading Practice",
                "type": Lesson.TYPE_PRACTICE,
                "practice_category": "ingestion",
                "difficulty": "medium",
            },
        ],
    },
    {
        "title": "Security and Governance",
        "lessons": [
            {
                "title": "Roles, Privileges, and Data Protection",
                "type": Lesson.TYPE_ARTICLE,
                "content": """
                    <h2>Security and Governance</h2>
                    <p>Snowflake uses role-based access control. Privileges are granted to roles, and roles can be granted to users or other roles.</p>
                    <h3>Key governance features</h3>
                    <ul>
                        <li>Use least privilege when granting access.</li>
                        <li>Use secure views and secure functions when sharing governed logic.</li>
                        <li>Use masking policies to control how sensitive column values are displayed.</li>
                        <li>Use row access policies to control which rows a consumer can see.</li>
                        <li>Use tags and classification capabilities to support governance workflows.</li>
                        <li>Use network policies and authentication controls to restrict access.</li>
                    </ul>
                """,
            },
            {
                "title": "Security and Governance Video Resource",
                "type": Lesson.TYPE_VIDEO,
                "video_url": "https://www.youtube.com/results?search_query=Snowflake+RBAC+masking+policies+row+access+policies",
            },
            {
                "title": "Security Practice",
                "type": Lesson.TYPE_PRACTICE,
                "practice_category": "security",
                "difficulty": "medium",
            },
        ],
    },
    {
        "title": "SQL and Data Transformation",
        "lessons": [
            {
                "title": "SQL, Semi-structured Data, and Transformations",
                "type": Lesson.TYPE_ARTICLE,
                "content": """
                    <h2>SQL and Data Transformation</h2>
                    <p>Snowflake supports standard SQL together with extensions for analytical and semi-structured workloads.</p>
                    <ul>
                        <li><strong>MERGE:</strong> Combines matched-row updates and unmatched-row inserts.</li>
                        <li><strong>Window functions:</strong> Calculate values across related rows while preserving row-level detail.</li>
                        <li><strong>VARIANT:</strong> Stores semi-structured values such as JSON.</li>
                        <li><strong>FLATTEN:</strong> Explodes arrays and objects into relational rows.</li>
                        <li><strong>CTEs:</strong> Make complex transformations easier to read and maintain.</li>
                    </ul>
                    <p>Use explicit casts and carefully validate data types when transforming semi-structured data.</p>
                """,
            },
            {
                "title": "SQL and Transformation Video Resource",
                "type": Lesson.TYPE_VIDEO,
                "video_url": "https://www.youtube.com/results?search_query=Snowflake+SQL+VARIANT+FLATTEN+window+functions",
            },
            {
                "title": "SQL Practice",
                "type": Lesson.TYPE_PRACTICE,
                "practice_category": "sql",
                "difficulty": "medium",
            },
        ],
    },
    {
        "title": "Data Sharing and Final Assessment",
        "lessons": [
            {
                "title": "Secure Data Sharing and Collaboration",
                "type": Lesson.TYPE_ARTICLE,
                "content": """
                    <h2>Data Sharing and Collaboration</h2>
                    <p>Snowflake Secure Data Sharing enables providers to share governed data with consumers without requiring the provider to copy the shared data into the consumer account.</p>
                    <ul>
                        <li>Shares expose selected databases, schemas, tables, views, or other supported objects.</li>
                        <li>Providers control what is included in a share.</li>
                        <li>Secure views and policies can help protect sensitive data.</li>
                        <li>Marketplace and listings provide managed ways to discover and distribute data products.</li>
                    </ul>
                    <p>Always review provider and consumer roles, object privileges, and data protection requirements before sharing.</p>
                """,
            },
            {
                "title": "Data Sharing Video Resource",
                "type": Lesson.TYPE_VIDEO,
                "video_url": "https://www.youtube.com/results?search_query=Snowflake+Secure+Data+Sharing",
            },
            {
                "title": "Sharing Practice",
                "type": Lesson.TYPE_PRACTICE,
                "practice_category": "sharing",
                "difficulty": "easy",
            },
            {
                "title": "SnowPro Core Final Practice Quiz",
                "type": Lesson.TYPE_QUIZ,
            },
        ],
    },
]


class Command(BaseCommand):
    help = "Seed a complete SnowPro Core course with article, video, practice, and quiz lessons."

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            help="User to own the course. Defaults to the first superuser, then first active user.",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete the seeded course and its sections/lessons before recreating it.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["reset"]:
            Course.objects.filter(slug=COURSE_SLUG).delete()

        owner = self._get_owner(options.get("username"))
        domain = self._get_domain()
        categories = self._get_categories(domain)
        exam = self._get_exam()
        course = self._get_course(owner, domain)

        lesson_count = 0
        practice_count = 0
        video_count = 0
        article_count = 0
        quiz_count = 0

        for section_order, section_spec in enumerate(SECTIONS, start=1):
            section, _ = CourseSection.objects.update_or_create(
                course=course,
                order=section_order,
                defaults={
                    "title": f"{CONTENT_PREFIX}{section_spec['title']}",
                    "is_visible": True,
                },
            )

            for lesson_order, lesson_spec in enumerate(section_spec["lessons"], start=1):
                lesson_type = lesson_spec["type"]
                defaults = {
                    "title": f"{CONTENT_PREFIX}{lesson_spec['title']}",
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
                    defaults["article_content"] = lesson_spec["content"]
                    article_count += 1
                elif lesson_type == Lesson.TYPE_VIDEO:
                    defaults["video_url"] = lesson_spec["video_url"]
                    video_count += 1
                elif lesson_type == Lesson.TYPE_PRACTICE:
                    category = categories[lesson_spec["practice_category"]]
                    defaults.update(
                        {
                            "practice_domain": domain,
                            "practice_category": category,
                            "practice_difficulty": lesson_spec["difficulty"],
                            "practice_threshold": 10,
                            "practice_lock_filters": True,
                        }
                    )
                    practice_count += 1
                elif lesson_type == Lesson.TYPE_QUIZ:
                    defaults.update(
                        {
                            "exam": exam,
                            "quiz_completion_mode": "pass",
                            "quiz_min_score": 70,
                            "quiz_allow_mock": False,
                            "quiz_max_attempts": 3,
                        }
                    )
                    quiz_count += 1

                Lesson.objects.update_or_create(
                    section=section,
                    order=lesson_order,
                    defaults=defaults,
                )
                lesson_count += 1

        self.stdout.write(self.style.SUCCESS("SnowPro Core course seeded successfully."))
        self.stdout.write(f"Course: {course.title} ({course.slug})")
        self.stdout.write(f"Sections: {len(SECTIONS)} | Lessons: {lesson_count}")
        self.stdout.write(
            f"Articles: {article_count} | Videos: {video_count} | "
            f"Practice: {practice_count} | Quizzes: {quiz_count}"
        )
        self.stdout.write("Recreate: python manage.py seed_snowpro_core_course --reset")

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

    def _get_domain(self):
        domain, _ = Domain.objects.get_or_create(
            organization=None,
            slug=DOMAIN_SLUG,
            defaults={"name": "Snowflake", "is_active": True},
        )
        if not domain.is_active:
            domain.is_active = True
            domain.save(update_fields=["is_active"])
        return domain

    def _get_categories(self, domain):
        category_map = {}
        category_names = {
            "architecture": "Architecture & Platform",
            "storage": "Storage & Data Organization",
            "compute": "Compute & Performance",
            "security": "Security & Governance",
            "ingestion": "Data Loading & Pipelines",
            "sql": "SQL & Data Transformation",
            "sharing": "Sharing & Collaboration",
        }
        for slug, name in category_names.items():
            category_map[slug] = Category.objects.get(
                organization=None,
                domain=domain,
                slug=f"snowflake-{slug}",
            )
        return category_map

    def _get_exam(self):
        try:
            return Exam.objects.get(title=EXAM_TITLE)
        except Exam.DoesNotExist as exc:
            raise CommandError(
                "The SnowPro Core exam was not found. Run "
                "python manage.py seed_snowflake_catalog first."
            ) from exc

    def _get_course(self, owner, domain):
        course, _ = Course.objects.update_or_create(
            slug=COURSE_SLUG,
            defaults={
                "title": COURSE_TITLE,
                "description": (
                    "A structured SnowPro Core preparation course covering Snowflake "
                    "architecture, storage, compute, loading, security, SQL, sharing, "
                    "practice activities, video resources, and a final practice quiz. "
                    "The content is educational and is not official Snowflake material."
                ),
                "category": domain,
                "level": "intermediate",
                "owner_type": Course.OWNER_PLATFORM,
                "organization": None,
                "is_public": True,
                "is_published": True,
                "approval_status": Course.APPROVAL_APPROVED,
                "created_by": owner,
            },
        )
        return course
