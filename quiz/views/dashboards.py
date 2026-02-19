import math
import random
import logging
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal
from courses.models import CourseSubscription
from django.db.models import Count


from organizations.models.access import CourseAccess


from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import login, authenticate, get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView,
)
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Avg, Count, Q, Sum
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.dateformat import DateFormat
from django.utils.formats import get_format
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import CreateView, DetailView, TemplateView, UpdateView

# Project-specific imports
from courses.models import Course, CourseSubscription, LessonProgress
from organizations.models.access import CourseAccess

from quiz.forms import *
from quiz.models import (
    Exam,
    ExamTrack,
    UserExam,
    ExamSubscription,
    ExamTrackSubscription,
    Coupon,
)
from quiz.services.access import can_access_exam
from quiz.services.pricing import apply_coupon
from quiz.services.subscription import has_valid_subscription
from quiz.utils import get_leaf_category_name

User = get_user_model()




import logging
from core.utils.memory import get_memory_usage_mb

logger = logging.getLogger("django")




@login_required
def dashboard_dispatch(request):
    """
    Single entry point: sends admins to admin dashboard, students to student dashboard.
    """
    if request.user.is_staff or request.user.is_superuser:
        return redirect('quiz:admin_dashboard')
    return redirect('quiz:student_dashboard')

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Sum, Avg, Q, F
from django.shortcuts import render, redirect
from django.utils import timezone
from datetime import timedelta

from django.contrib.auth.models import User
from quiz.models import (
    UserExam,
    Exam,
    ExamTrack,
    ExamTrackSubscription,
)
from courses.models import Course, CourseEnrollment
from organizations.models.organization import Organization
from organizations.models.membership import OrganizationMember


@staff_member_required
def admin_dashboard(request):
    now = timezone.now()
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)

    # =====================================================
    # USER INTELLIGENCE
    # =====================================================
    total_users = User.objects.count()

    active_users_7d = User.objects.filter(
        last_login__gte=seven_days_ago
    ).count()

    new_users_7d = User.objects.filter(
        date_joined__gte=seven_days_ago
    ).count()

    users_with_no_attempts = User.objects.annotate(
        attempts=Count("exam_attempts")
    ).filter(attempts=0).count()

    # =====================================================
    # EXAM INTELLIGENCE
    # =====================================================
    total_attempts = UserExam.objects.filter(
        submitted_at__isnull=False
    ).count()

    passed_attempts = UserExam.objects.filter(
        passed=True
    ).count()

    avg_score = UserExam.objects.aggregate(
        avg=Avg("score")
    )["avg"]

    pass_rate = (
        (passed_attempts / total_attempts) * 100
        if total_attempts else 0
    )

    most_attempted_exam = (
        Exam.objects
        .annotate(attempts=Count("userexam"))
        .order_by("-attempts")
        .first()
    )

    # =====================================================
    # COURSE INTELLIGENCE
    # =====================================================
    total_courses = Course.objects.filter(
        is_deleted=False
    ).count()

    published_courses = Course.objects.filter(
        is_published=True,
        is_deleted=False
    ).count()

    platform_courses = Course.objects.filter(
        owner_type="platform"
    ).count()

    org_courses = Course.objects.filter(
        owner_type="organization"
    ).count()

    total_enrollments = CourseEnrollment.objects.count()

    most_popular_course = (
        Course.objects
        .annotate(enroll_count=Count("enrollments"))
        .order_by("-enroll_count")
        .first()
    )

    # =====================================================
    # ORGANIZATION INTELLIGENCE
    # =====================================================
    total_orgs = Organization.objects.count()

    active_orgs = Organization.objects.filter(
        is_active=True
    ).count()

    total_org_members = OrganizationMember.objects.filter(
        is_active=True
    ).count()

    org_student_count = OrganizationMember.objects.filter(
        role="student",
        is_active=True
    ).count()

    org_admin_count = OrganizationMember.objects.filter(
        role="org_admin",
        is_active=True
    ).count()

    # =====================================================
    # SUBSCRIPTION INTELLIGENCE
    # =====================================================
    total_track_subs = ExamTrackSubscription.objects.count()

    active_track_subs = ExamTrackSubscription.objects.filter(
        is_active=True,
        expires_at__gte=now
    ).count()

    expired_track_subs = ExamTrackSubscription.objects.filter(
        is_active=True,
        expires_at__lt=now
    ).count()

    trial_subs = ExamTrackSubscription.objects.filter(
        is_trial=True
    ).count()

    paid_subs = ExamTrackSubscription.objects.filter(
        payment_required=True
    ).count()

    conversion_rate = (
        (paid_subs / trial_subs) * 100
        if trial_subs else 0
    )

    # =====================================================
    # REVENUE INTELLIGENCE
    # =====================================================
    total_revenue = (
        ExamTrackSubscription.objects
        .filter(payment_required=True)
        .aggregate(total=Sum("amount"))["total"]
    ) or 0

    revenue_30d = (
        ExamTrackSubscription.objects
        .filter(
            payment_required=True,
            subscribed_at__gte=thirty_days_ago
        )
        .aggregate(total=Sum("amount"))["total"]
    ) or 0

    arpu = total_revenue / paid_subs if paid_subs else 0

    # =====================================================
    # BUSINESS HEALTH
    # =====================================================
    churn_risk_users = User.objects.filter(
        track_subscriptions__is_active=True,
        last_login__lt=thirty_days_ago
    ).distinct().count()

    # =====================================================
    # TRACK ANALYTICS (Optimized)
    # =====================================================
    tracks = (
        ExamTrack.objects
        .annotate(
            enrolled=Count(
                "subscriptions__user",
                filter=Q(subscriptions__is_active=True),
                distinct=True
            ),
            revenue=Sum(
                "subscriptions__amount",
                filter=Q(subscriptions__payment_required=True)
            )
        )
    )

    track_rows = []
    for track in tracks:
        track_rows.append({
            "track": track,
            "enrolled": track.enrolled,
            "revenue": track.revenue or 0,
        })





    # =====================================================
    # COURSE SUBSCRIPTIONS
    # =====================================================

    total_course_subs = CourseSubscription.objects.count()

    active_course_subs = CourseSubscription.objects.filter(
        is_active=True
    ).count()

    expired_course_subs = CourseSubscription.objects.filter(
        is_active=True,
        expires_at__lt=now
    ).count()   


    trial_course_subs = CourseSubscription.objects.filter(
        payment_required=False
    ).count()


    paid_course_subs = CourseSubscription.objects.filter(
        payment_required=True
    ).count()

    course_conversion_rate = (
        (paid_course_subs / trial_course_subs) * 100
        if trial_course_subs else 0
    )

    course_revenue = (
        CourseSubscription.objects
        .filter(payment_required=True)
        .aggregate(total=Sum("amount"))["total"]
    ) or 0


    source_breakdown = (
        CourseSubscription.objects
        .values("source")
        .annotate(count=Count("id"))
        )
    
 

    most_subscribed_course = (
        Course.objects
        .annotate(sub_count=Count("subscriptions"))
        .order_by("-sub_count")
        .first()
    )




    # =====================================================
    # CONTEXT
    # =====================================================
    context = {
        # User Intelligence
        "total_users": total_users,
        "active_users_7d": active_users_7d,
        "new_users_7d": new_users_7d,
        "users_with_no_attempts": users_with_no_attempts,

        # Exam Intelligence
        "total_attempts": total_attempts,
        "pass_rate": round(pass_rate, 2),
        "avg_score": round(avg_score, 2) if avg_score else None,
        "most_attempted_exam": most_attempted_exam,

        # Course Intelligence
        "total_courses": total_courses,
        "published_courses": published_courses,
        "platform_courses": platform_courses,
        "org_courses": org_courses,
        "total_enrollments": total_enrollments,
        "most_popular_course": most_popular_course,

        # Organization Intelligence
        "total_orgs": total_orgs,
        "active_orgs": active_orgs,
        "total_org_members": total_org_members,
        "org_student_count": org_student_count,
        "org_admin_count": org_admin_count,

        # Subscription Intelligence
        "total_track_subs": total_track_subs,
        "active_track_subs": active_track_subs,
        "expired_track_subs": expired_track_subs,
        "trial_subs": trial_subs,
        "paid_subs": paid_subs,
        "conversion_rate": round(conversion_rate, 2),

        # Revenue
        "total_revenue": total_revenue,
        "revenue_30d": revenue_30d,
        "arpu": round(arpu, 2),

        # Business Health
        "churn_risk_users": churn_risk_users,

        # Tracks
        "track_rows": track_rows,

        # Course Subscription KPIs
        "total_course_subs": total_course_subs,
        "active_course_subs": active_course_subs,
        "expired_course_subs": expired_course_subs,
        "trial_course_subs": trial_course_subs,
        "paid_course_subs": paid_course_subs,
        "course_conversion_rate": round(course_conversion_rate, 2),
        "course_revenue": course_revenue,
        "source_breakdown": source_breakdown,
        "most_subscribed_course": most_subscribed_course,

    }

    return render(request, "quiz/admin/admin_dashboard.html", context)



@login_required
def student_dashboard(request):
    mem = get_memory_usage_mb()
    logger.info(f"Student Dashboard memory usage: {mem} MB")
    user = request.user

    # ---------------- ACTIVE ATTEMPT ----------------
    active_attempt = (
        UserExam.objects
        .filter(user=user, submitted_at__isnull=True)
        .order_by("-started_at")
        .first()
    )

    # ---------------- BASIC STATS ----------------
    total_attempts = UserExam.objects.filter(
        user=user, submitted_at__isnull=False
    ).count()

    passed_count = UserExam.objects.filter(
        user=user, passed=True
    ).count()

    failed_count = UserExam.objects.filter(
        user=user, passed=False
    ).count()

    # ---------------- SUBSCRIPTIONS (FULL OBJECTS) ----------------
    track_subs = {
        s.track_id: s
        for s in ExamTrackSubscription.objects.filter(user=user)
    }

    exam_subs = {
        s.exam_id: s
        for s in ExamSubscription.objects.filter(user=user)
    }

    # ---------------- GROUP EXAMS BY TRACK ----------------
    track_map = defaultdict(lambda: {
        "items": [],
        "passed": 0,
        "failed": 0,
        "attempted": 0,
    })

    exams = (
        Exam.objects
        .filter(is_published=True)
        .select_related("track")
        .order_by("level")
    )

    # ---------------- PASSED LEVELS ----------------
    passed_levels_by_track = defaultdict(set)

    passed_attempts = (
        UserExam.objects
        .filter(user=user, passed=True)
        .select_related("exam")
    )

    for ue in passed_attempts:
        if ue.exam.track:
            passed_levels_by_track[ue.exam.track_id].add(ue.exam.level)

    # ---------------- MAIN LOOP ----------------
    for exam in exams:
        track = exam.track
        if not track:
            continue

        track_sub = track_subs.get(track.id)
        exam_sub = exam_subs.get(exam.id)

        has_valid_subscription = (
            (track_sub and track_sub.is_valid()) or
            (exam_sub and exam_sub.is_valid())
        )

        has_expired_subscription = (
            (track_sub and not track_sub.is_valid()) or
            (exam_sub and not exam_sub.is_valid())
        )

        if not has_valid_subscription and not has_expired_subscription:
            continue

        # ---------- LEVEL LOCK ----------
        locked = False
        lock_reason = None

        if exam.level > 1:
            if (exam.level - 1) not in passed_levels_by_track[track.id]:
                locked = True
                lock_reason = f"Complete Level {exam.level - 1} to unlock"

        # ---------- ATTEMPTS ----------
        attempts = list(
            UserExam.objects
            .filter(user=user, exam=exam, submitted_at__isnull=False)
            .order_by("submitted_at")
        )

        scores = [a.score for a in attempts if a.score is not None]
        last_score = scores[-1] if scores else None
        best_score = max(scores) if scores else None
        retry_count = max(0, len(attempts) - 1)

        status = None
        is_passed = False

        if attempts:
            track_map[track]["attempted"] += 1
            is_passed = attempts[-1].passed is True
            if is_passed:
                track_map[track]["passed"] += 1
                status = "passed"
            else:
                track_map[track]["failed"] += 1
                status = "failed"

        # ---------- ACTIVE / COOLDOWN ----------
        active = (
            UserExam.objects
            .filter(user=user, exam=exam, submitted_at__isnull=True)
            .first()
        )

        cooldown_remaining = 0
        can_retake = True

        if attempts and not is_passed:
            last_attempt = attempts[-1]
            cd = getattr(settings, "RETAKE_COOLDOWN_MINUTES", 0)
            if cd and last_attempt.submitted_at:
                elapsed = (timezone.now() - last_attempt.submitted_at).total_seconds()
                remaining = (cd * 60) - elapsed
                if remaining > 0:
                    can_retake = False
                    cooldown_remaining = int(remaining)

        # ---------- ACTION ----------
        if has_expired_subscription:
            action = "renew"
        elif is_passed:
            action = None
        elif active:
            action = "resume"
        elif locked:
            action = "locked"
        elif not can_retake:
            action = "cooldown"
        elif attempts:
            action = "retake"
        else:
            action = "start"

        # ---------- MOCK ATTEMPTS ----------
        mock_attempts = (
            UserExam.objects
            .filter(
                user=user,
                exam=exam,
                passed__isnull=True,
                submitted_at__isnull=False
            )
            .order_by("-submitted_at")
        )

        mock_used = mock_attempts.count()
        mock_allowed = exam.max_mock_attempts or 0

        # ---------- APPEND ----------
        track_map[track]["items"].append({
            "exam": exam,
            "status": status,
            "is_passed": is_passed,
            "action": action,
            "last_attempt": active,
            "retry_count": retry_count,
            "last_score": last_score,
            "best_score": best_score,
            "cooldown_remaining": cooldown_remaining,
            "locked": locked,
            "lock_reason": lock_reason,
            "subscription_expired": has_expired_subscription,
            "track_subscription": track_sub,
            "exam_subscription": exam_sub,
            "mock_attempts": list(mock_attempts),
            "mock_used": mock_used,
            "mock_allowed": mock_allowed,
        })

    # =====================================================
    # ORGANIZATION-ASSIGNED COURSES (NO PUBLIC COURSES)
    # =====================================================
    course_access_qs = (
        CourseAccess.objects
        .filter(
            user=user,
            is_active=True,
            source="organization",          # 🚫 excludes public & individual
            organization__isnull=False,
            course__is_published=True
        )
        .select_related("course", "organization")
        .order_by("-granted_at")
    )

    org_courses = defaultdict(list)

    for access in course_access_qs:
        org_courses[access.organization].append(access)

    # ---------------- COURSE SUBSCRIPTIONS ----------------
    course_subs = (
        CourseSubscription.objects
        .filter(user=user, is_active=True)
        .select_related("course")
        
    )

    courses_data = []

    for sub in course_subs:
        course = sub.course

        # Total lessons
        total_lessons = course.sections.count() and sum(
            s.lessons.count() for s in course.sections.all()
        )

        # Completed lessons
        completed_lessons = LessonProgress.objects.filter(
            user=user,
            lesson__section__course=course,
            completed=True
        ).count()

        progress = 0
        if total_lessons:
            progress = int((completed_lessons / total_lessons) * 100)

        courses_data.append({
            "course": course,
            "progress": progress,
            "completed": completed_lessons,
            "total": total_lessons,
        })

    return render(request, "quiz/student/student_dashboard.html", {
        "active_attempt": active_attempt,
        "total_attempts": total_attempts,
        "passed_count": passed_count,
        "failed_count": failed_count,
        "track_map": dict(track_map),

        # 👇 NEW (courses)
        "org_courses": dict(org_courses),
        "courses": courses_data,
    })
