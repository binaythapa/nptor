# scripts/benchmark_large_dataset.py
"""
NPTOR Phase 3 - Large-Dataset Historical Analytics Scalability & Performance Benchmark.
Executes on Staging MariaDB against realistic volume:
- 500 Student enrollments across 12 months
- 1,000 Resource assignments across lifecycle states
- 2,500 Exam attempts across 12 months
Measures:
- Memory consumption (tracemalloc)
- SQL query count and execution time (django.db.connection.queries)
- DB-level aggregation verification (TruncMonth with UTC tzinfo)
- HTTP End-to-End latency across all date filters (7d, 30d, 90d, 1y, all)
Cleans up all benchmark artifacts upon completion.
"""

import os
import sys
import time
import json
import random
import datetime
import tracemalloc
from datetime import timedelta

# Ensure staging project root in sys.path
sys.path.insert(0, '/home3/nptorcom/repositories/nptor_staging/project')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'objective_exam.settings')

import django
django.setup()

from django.conf import settings
settings.DEBUG = True
if "*" not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS.append("*")

from django.contrib.auth import get_user_model
from django.db import connection, reset_queries
from django.utils import timezone
from django.test import Client

from organizations.models import (
    AcademicYear,
    ClassSection,
    ClassTeacher,
    ClassResourceAssignment,
    Organization,
    OrganizationClass,
    OrganizationMember,
    OrganizationRole,
    OrganizationStudent,
    ResourceAssignment,
    StudentEnrollment,
)
from courses.models import Course
from quiz.models import Category, Domain, Exam, UserExam
from organizations.services.analytics import (
    get_admin_analytics,
    get_teacher_analytics,
    get_student_analytics,
)

User = get_user_model()

BENCH_SLUG = "bench-scale-perf-org"

def clean_all():
    # Delete in strict dependency order due to PROTECT foreign keys
    UserExam.objects.filter(user__username__startswith="bench_").delete()
    ResourceAssignment.objects.filter(organization__slug=BENCH_SLUG).delete()
    ClassResourceAssignment.objects.filter(organization__slug=BENCH_SLUG).delete()
    StudentEnrollment.objects.filter(student__organization__slug=BENCH_SLUG).delete()
    ClassTeacher.objects.filter(organization__slug=BENCH_SLUG).delete()
    ClassSection.objects.filter(organization__slug=BENCH_SLUG).delete()
    OrganizationClass.objects.filter(organization__slug=BENCH_SLUG).delete()
    AcademicYear.objects.filter(organization__slug=BENCH_SLUG).delete()
    
    # Exams & Courses
    for ex in Exam.objects.filter(organization__slug=BENCH_SLUG):
        ex.categories.clear()
        ex.delete()
    Course.objects.filter(organization__slug=BENCH_SLUG).delete()
    Category.objects.filter(organization__slug=BENCH_SLUG).delete()
    Domain.objects.filter(organization__slug=BENCH_SLUG).delete()
    
    # Also clean unlinked test entities if any
    Course.objects.filter(slug__startswith="bench-").delete()
    Domain.objects.filter(slug__startswith="bench-").delete()
    
    # Students & Members
    OrganizationStudent.objects.filter(organization__slug=BENCH_SLUG).delete()
    OrganizationMember.objects.filter(organization__slug=BENCH_SLUG).delete()
    Organization.objects.filter(slug=BENCH_SLUG).delete()
    User.objects.filter(username__startswith="bench_").delete()

def create_benchmark_dataset():
    print(f"\n[1/5] Seeding large-scale representative dataset for {BENCH_SLUG}...")
    t0 = time.perf_counter()

    clean_all()

    admin = User.objects.create_user(
        username="bench_admin",
        email="bench_admin@staging.nptor.com",
        password="BenchPassword123!",
        first_name="Bench",
        last_name="Admin"
    )

    teacher = User.objects.create_user(
        username="bench_teacher",
        email="bench_teacher@staging.nptor.com",
        password="BenchPassword123!",
        first_name="Bench",
        last_name="Teacher"
    )

    org = Organization.objects.create(
        name="Benchmark Scalability Academy",
        slug=BENCH_SLUG,
        org_type=Organization.TYPE_SCHOOL,
        is_active=True
    )

    OrganizationMember.objects.create(user=admin, organization=org, role=OrganizationRole.ORG_ADMIN, is_active=True)
    OrganizationMember.objects.create(user=teacher, organization=org, role=OrganizationRole.STAFF, is_active=True)

    today = timezone.now().date()
    acad_year = AcademicYear.objects.create(
        organization=org,
        name="2026-2027",
        start_date=today - timedelta(days=365),
        end_date=today + timedelta(days=60),
        is_current=True
    )

    org_class = OrganizationClass.objects.create(organization=org, name="Grade 10")
    sec_a = ClassSection.objects.create(organization=org, academic_year=acad_year, class_group=org_class, name="A")
    sec_b = ClassSection.objects.create(organization=org, academic_year=acad_year, class_group=org_class, name="B")

    ClassTeacher.objects.create(organization=org, academic_year=acad_year, class_section=sec_a, teacher=teacher, is_primary=True)

    ts_now = int(time.time())
    course = Course.objects.create(
        title="Scalability Engineering 101",
        slug=f"bench-scalability-{ts_now}",
        organization=org,
        is_published=True
    )

    domain = Domain.objects.create(name=f"Bench Domain {ts_now}", slug=f"bench-dom-{ts_now}", organization=org)
    cat = Category.objects.create(domain=domain, name=f"Bench Cat {ts_now}", slug=f"bench-cat-{ts_now}", organization=org)

    exam = Exam.objects.create(
        title="Institutional Bench Exam",
        duration_seconds=3600,
        organization=org,
        is_published=True
    )
    exam.categories.add(cat)

    # 1. Create 500 Students
    print(" -> Creating 500 students and enrollments...")
    now = timezone.now()
    
    # Pre-generate user instances
    user_objs = [
        User(
            username=f"bench_std_{i:04d}",
            email=f"bench_std_{i:04d}@staging.nptor.com",
            first_name=f"Student{i}",
            last_name="Scale",
            is_active=True
        )
        for i in range(1, 501)
    ]
    User.objects.bulk_create(user_objs)
    persisted_users = list(User.objects.filter(username__startswith="bench_std_").order_by("id"))

    # Memberships
    member_objs = [
        OrganizationMember(
            user=u,
            organization=org,
            role=OrganizationRole.STUDENT,
            is_active=True
        )
        for u in persisted_users
    ]
    OrganizationMember.objects.bulk_create(member_objs)

    # Org Students
    org_student_objs = [
        OrganizationStudent(
            organization=org,
            user=u,
            student_id=f"STU-{u.id:05d}",
            admission_no=f"ADM-{u.id:05d}"
        )
        for u in persisted_users
    ]
    OrganizationStudent.objects.bulk_create(org_student_objs)
    persisted_org_students = list(OrganizationStudent.objects.filter(organization=org).order_by("id"))

    # Enrollments distributed over past 12 months (360 days)
    enrollment_objs = []
    for i, ost in enumerate(persisted_org_students):
        days_ago = (i % 12) * 30 + (i % 28)
        joined_date = (now - timedelta(days=days_ago)).date()
        sec = sec_a if i % 2 == 0 else sec_b
        enrollment_objs.append(
            StudentEnrollment(
                student=ost,
                academic_year=acad_year,
                class_section=sec,
                roll_number=str(i + 1),
                joined_at=joined_date,
                status=StudentEnrollment.STATUS_ACTIVE
            )
        )
    StudentEnrollment.objects.bulk_create(enrollment_objs)

    # 2. Create 1,000 Resource Assignments
    print(" -> Creating 1,000 resource assignments across lifecycle states...")
    assignment_objs = []
    statuses = [
        (ResourceAssignment.STATUS_ASSIGNED, True),
        (ResourceAssignment.STATUS_STARTED, True),
        (ResourceAssignment.STATUS_COMPLETED, False),
        (ResourceAssignment.STATUS_ASSIGNED, True), # overdue candidate
    ]
    for i in range(1000):
        std_user = persisted_users[i % len(persisted_users)]
        st, is_act = statuses[i % len(statuses)]
        days_offset = (i % 360)
        due = now - timedelta(days=days_offset - 5) if i % 4 == 3 else now + timedelta(days=10)
        comp = (now - timedelta(days=days_offset)) if st == ResourceAssignment.STATUS_COMPLETED else None
        
        assignment_objs.append(
            ResourceAssignment(
                organization=org,
                student=std_user,
                resource_type=ResourceAssignment.RESOURCE_EXAM if i % 2 == 0 else ResourceAssignment.RESOURCE_COURSE,
                exam=exam if i % 2 == 0 else None,
                course=course if i % 2 == 1 else None,
                assigned_by=teacher,
                status=st,
                is_active=is_act,
                due_at=due,
                completed_at=comp
            )
        )
    ResourceAssignment.objects.bulk_create(assignment_objs)

    # 3. Create 2,500 UserExam attempts
    print(" -> Creating 2,500 UserExam attempts across 12 months...")
    user_exam_objs = []
    random.seed(42)
    for i in range(2500):
        std_user = persisted_users[i % len(persisted_users)]
        days_ago = (i % 360)
        sub_time = now - timedelta(days=days_ago, minutes=random.randint(10, 180))
        score = round(random.uniform(40.0, 98.0), 1)
        passed = score >= 60.0
        
        user_exam_objs.append(
            UserExam(
                user=std_user,
                exam=exam,
                status=UserExam.STATUS_SUBMITTED,
                score=score,
                passed=passed,
                submitted_at=sub_time,
                started_at=sub_time - timedelta(minutes=45)
            )
        )
    UserExam.objects.bulk_create(user_exam_objs)

    elapsed = time.perf_counter() - t0
    print(f" -> Seeding completed in {elapsed:.2f}s.")
    return org, admin, teacher, persisted_users[0]

def benchmark_analytics_service(org, admin, teacher, student):
    print("\n[2/5] Benchmarking Analytics Service Layer (Queries, Latency, Memory)...")
    results = {}

    date_filters = ["7d", "30d", "90d", "1y", "all"]
    results["admin"] = {}

    for df in date_filters:
        reset_queries()
        tracemalloc.start()
        t0 = time.perf_counter()
        
        data = get_admin_analytics(org, date_range=df)
        
        t_service = (time.perf_counter() - t0) * 1000
        current_mem, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        sql_queries = list(connection.queries)
        sql_time = sum(float(q.get("time", 0)) for q in sql_queries) * 1000

        results["admin"][df] = {
            "service_time_ms": round(t_service, 2),
            "sql_time_ms": round(sql_time, 2),
            "query_count": len(sql_queries),
            "peak_memory_kb": round(peak_mem / 1024, 2),
            "enrollment_trend_points": len(data.get("charts", {}).get("enrollment_trends", {}).get("labels", [])),
            "exam_trend_points": len(data.get("charts", {}).get("exam_trends", {}).get("labels", [])),
            "total_students": data.get("kpi", {}).get("total_students"),
            "total_assignments": data.get("kpi", {}).get("total_assignments"),
        }

    # Verify SQL TruncMonth generation
    print(" -> Inspecting Database-Level SQL Grouping...")
    trunc_queries = [q["sql"] for q in sql_queries if "DATE_FORMAT" in q["sql"] or "joined_at" in q["sql"]]
    results["db_trunc_sql_sample"] = trunc_queries[0] if trunc_queries else "N/A"

    # Teacher Benchmarks
    results["teacher"] = {}
    for df in ["30d", "all"]:
        reset_queries()
        tracemalloc.start()
        t0 = time.perf_counter()
        data_t = get_teacher_analytics(org, teacher, date_range=df)
        t_service = (time.perf_counter() - t0) * 1000
        _, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        sql_queries = list(connection.queries)
        sql_time = sum(float(q.get("time", 0)) for q in sql_queries) * 1000
        results["teacher"][df] = {
            "service_time_ms": round(t_service, 2),
            "sql_time_ms": round(sql_time, 2),
            "query_count": len(sql_queries),
            "peak_memory_kb": round(peak_mem / 1024, 2),
            "scoped_students": data_t.get("kpi", {}).get("total_students"),
        }

    # Student Benchmarks
    results["student"] = {}
    reset_queries()
    tracemalloc.start()
    t0 = time.perf_counter()
    data_s = get_student_analytics(org, student)
    t_service = (time.perf_counter() - t0) * 1000
    _, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    sql_queries = list(connection.queries)
    sql_time = sum(float(q.get("time", 0)) for q in sql_queries) * 1000
    results["student"]["lifetime"] = {
        "service_time_ms": round(t_service, 2),
        "sql_time_ms": round(sql_time, 2),
        "query_count": len(sql_queries),
        "peak_memory_kb": round(peak_mem / 1024, 2),
    }

    return results

def benchmark_http_latency(org, admin, teacher, student):
    print("\n[3/5] Benchmarking End-to-End HTTP Request Latency across Viewports...")
    client = Client(SERVER_NAME="staging.nptor.com")
    http_results = {}

    views = [
        ("Admin Dashboard", f"/org/{org.slug}/admin/dashboard/", admin, ["7d", "30d", "90d", "1y", "all"]),
        ("Teacher Dashboard", f"/org/{org.slug}/admin/teacher/", teacher, ["7d", "30d", "90d", "1y", "all"]),
        ("Student Learning", f"/org/{org.slug}/learning/", student, [None]),
    ]

    for view_name, url_base, user, filters in views:
        client.force_login(user)
        http_results[view_name] = {}
        for df in filters:
            url = f"{url_base}?range={df}" if df else url_base
            times = []
            status_codes = []
            resp_sizes = []
            
            # Execute 3 iterations to get warm mean
            for _ in range(3):
                t0 = time.perf_counter()
                resp = client.get(url, HTTP_HOST="staging.nptor.com")
                elapsed_ms = (time.perf_counter() - t0) * 1000
                times.append(elapsed_ms)
                status_codes.append(resp.status_code)
                resp_sizes.append(len(resp.content))
            
            avg_ms = sum(times) / len(times)
            label = df if df else "default"
            http_results[view_name][label] = {
                "http_status": status_codes[0],
                "avg_latency_ms": round(avg_ms, 2),
                "min_latency_ms": round(min(times), 2),
                "max_latency_ms": round(max(times), 2),
                "response_bytes": resp_sizes[0],
            }

    return http_results

def cleanup_benchmark_dataset():
    print("\n[4/5] Cleaning up all benchmark artifacts from staging MariaDB...")
    t0 = time.perf_counter()
    clean_all()
    elapsed = time.perf_counter() - t0
    print(f" -> Cleaned up benchmark data in {elapsed:.2f}s.")

def main():
    try:
        org, admin, teacher, student = create_benchmark_dataset()
        service_results = benchmark_analytics_service(org, admin, teacher, student)
        http_results = benchmark_http_latency(org, admin, teacher, student)
    finally:
        cleanup_benchmark_dataset()

    print("\n[5/5] Benchmark Summary Report:")
    report = {
        "dataset_profile": {
            "students": 500,
            "assignments": 1000,
            "exam_attempts": 2500,
            "timespan_months": 12,
            "db_backend": connection.vendor,
        },
        "service_performance": service_results,
        "http_performance": http_results,
    }

    print(json.dumps(report, indent=2))
    with open("/home3/nptorcom/repositories/nptor_staging/benchmark_results.json", "w") as f:
        json.dump(report, f, indent=2)

if __name__ == "__main__":
    main()
