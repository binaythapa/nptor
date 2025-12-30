import math
import random
import logging
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

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


# Re-assign User in case a custom user model is used (overrides the imported User if needed)
User = get_user_model()

# Logger
logger = logging.getLogger(__name__)



# -------------------------
# Generic dashboards
# -------------------------
@login_required
def dashboard(request):
    exams_count = Exam.objects.count()
    published = Exam.objects.filter(is_published=True).count()
    active_attempts = UserExam.objects.filter(submitted_at__isnull=True).count()
    users_count = User.objects.count()
    my_attempts = UserExam.objects.filter(user=request.user).order_by('-started_at')[:5]

    context = {
        'exams_count': exams_count,
        'published_count': published,
        'active_attempts': active_attempts,
        'users_count': users_count,
        'my_attempts': my_attempts,
    }
    return render(request, 'quiz/dashboard.html', context)


@login_required
def dashboard_dispatch(request):
    """
    Single entry point: sends admins to admin dashboard, students to student dashboard.
    """
    if request.user.is_staff or request.user.is_superuser:
        return redirect('quiz:admin_dashboard')
    return redirect('quiz:student_dashboard')


from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.shortcuts import render, redirect
from django.utils import timezone
from django.db.models import Avg, Count, Sum, Q
from datetime import timedelta

from django.contrib.auth import get_user_model
from quiz.models import (
    UserExam,
    Exam,
    ExamTrack,
    ExamTrackSubscription,
)

User = get_user_model()


@staff_member_required
def admin_dashboard(request):
    now = timezone.now()

    # =====================================================
    # RESET MOCK ATTEMPTS (ADMIN ACTION)
    # =====================================================
    if request.method == "POST" and request.POST.get("action") == "reset_mock":
        user_id = request.POST.get("user_id")
        exam_id = request.POST.get("exam_id")

        if not user_id or not exam_id:
            messages.error(request, "Please select both student and exam.")
            return redirect("quiz:admin_dashboard")

        try:
            user = User.objects.get(id=user_id)
            exam = Exam.objects.get(id=exam_id)
        except (User.DoesNotExist, Exam.DoesNotExist):
            messages.error(request, "Invalid student or exam selected.")
            return redirect("quiz:admin_dashboard")

        # Delete ONLY mock attempts
        deleted_count, _ = UserExam.objects.filter(
            user=user,
            exam=exam,
            passed__isnull=True  # ✅ mock attempts only
        ).delete()

        messages.success(
            request,
            f"Reset {deleted_count} mock attempt(s) for {user.username} – {exam.title}"
        )
        return redirect("quiz:admin_dashboard")

    # =====================================================
    # GLOBAL KPIs
    # =====================================================
    total_users = User.objects.count()

    total_attempts = UserExam.objects.filter(
        submitted_at__isnull=False
    ).count()

    passed_attempts = UserExam.objects.filter(
        passed=True
    ).count()

    avg_score = (
        UserExam.objects
        .filter(score__isnull=False)
        .aggregate(avg=Avg("score"))["avg"]
    )

    pass_rate = (
        (passed_attempts / total_attempts) * 100
        if total_attempts else 0
    )

    # =====================================================
    # SUBSCRIPTIONS
    # =====================================================
    total_track_subs = ExamTrackSubscription.objects.count()

    active_track_subs = ExamTrackSubscription.objects.filter(
        is_active=True
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
    # REVENUE
    # =====================================================
    total_revenue = (
        ExamTrackSubscription.objects
        .filter(payment_required=True)
        .aggregate(total=Sum("amount"))["total"]
    ) or 0

    arpu = total_revenue / paid_subs if paid_subs else 0

    # =====================================================
    # EXPIRING SOON
    # =====================================================
    expiring_soon = ExamTrackSubscription.objects.filter(
        is_active=True,
        expires_at__isnull=False,
        expires_at__lte=now + timedelta(days=7),
        expires_at__gte=now
    ).count()

    # =====================================================
    # TRACK ANALYTICS
    # =====================================================
    track_rows = []
    tracks = ExamTrack.objects.filter(is_active=True)

    for track in tracks:
        exams = Exam.objects.filter(track=track, is_published=True)
        exam_count = exams.count()

        enrolled_users = (
            ExamTrackSubscription.objects
            .filter(track=track, is_active=True)
            .values("user")
            .distinct()
            .count()
        )

        completed_users = 0
        if exam_count:
            completed_users = (
                UserExam.objects
                .filter(exam__in=exams, passed=True)
                .values("user")
                .annotate(cnt=Count("exam", distinct=True))
                .filter(cnt=exam_count)
                .count()
            )

        completion_rate = (
            (completed_users / enrolled_users) * 100
            if enrolled_users else 0
        )

        avg_track_score = (
            UserExam.objects
            .filter(exam__in=exams, score__isnull=False)
            .aggregate(avg=Avg("score"))["avg"]
        )

        revenue_by_track = (
            ExamTrackSubscription.objects
            .filter(track=track, payment_required=True)
            .aggregate(total=Sum("amount"))["total"]
        ) or 0

        track_rows.append({
            "track": track,
            "enrolled": enrolled_users,
            "completed": completed_users,
            "completion_rate": round(completion_rate, 2),
            "avg_score": round(avg_track_score, 2) if avg_track_score else None,
            "revenue": revenue_by_track,
            "drop_exam": "—",
        })

    return render(request, "quiz/admin_dashboard.html", {
        # KPIs
        "total_users": total_users,
        "total_attempts": total_attempts,
        "pass_rate": round(pass_rate, 2),
        "avg_score": round(avg_score, 2) if avg_score else None,

        # Subscriptions
        "total_track_subs": total_track_subs,
        "active_track_subs": active_track_subs,
        "expired_track_subs": expired_track_subs,
        "trial_subs": trial_subs,
        "paid_subs": paid_subs,
        "conversion_rate": round(conversion_rate, 2),

        # Revenue
        "total_revenue": total_revenue,
        "arpu": round(arpu, 2),

        # Alerts
        "expiring_soon": expiring_soon,

        # Track table
        "track_rows": track_rows,

        # NEW: Reset form data
        "students": User.objects.order_by("username"),
        "exams": Exam.objects.filter(is_published=True),
    })



from collections import defaultdict
from django.conf import settings
from django.shortcuts import render
from django.utils import timezone
from django.contrib.auth.decorators import login_required

from quiz.models import (
    Exam,
    UserExam,
    ExamSubscription,
    ExamTrackSubscription,
)

@login_required
def student_dashboard(request):
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

    # ---------------- SUBSCRIPTIONS ----------------
    subscribed_tracks = set(
        ExamTrackSubscription.objects
        .filter(user=user, is_active=True)
        .values_list("track_id", flat=True)
    )

    subscribed_exams = set(
        ExamSubscription.objects
        .filter(user=user, is_active=True)
        .values_list("exam_id", flat=True)
    )

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

    passed_levels_by_track = defaultdict(set)

    passed_attempts = (
        UserExam.objects
        .filter(user=user, passed=True)
        .select_related("exam")
    )

    for ue in passed_attempts:
        if ue.exam.track:
            passed_levels_by_track[ue.exam.track_id].add(ue.exam.level)

    for exam in exams:
        track = exam.track
        if not track:
            continue

        if track.id not in subscribed_tracks and exam.id not in subscribed_exams:
            continue

        # ---------- LEVEL LOCK ----------
        locked = False
        if exam.level > 1:
            if (exam.level - 1) not in passed_levels_by_track[track.id]:
                locked = True

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
        if is_passed:
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

            # mock
            "mock_attempts": list(mock_attempts),
            "mock_used": mock_used,
            "mock_allowed": mock_allowed,
        })

    return render(request, "quiz/student_dashboard.html", {
        "active_attempt": active_attempt,
        "total_attempts": total_attempts,
        "passed_count": passed_count,
        "failed_count": failed_count,
        "track_map": dict(track_map),
    })
