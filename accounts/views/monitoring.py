from django.contrib.auth.models import User
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render
from django.core.paginator import Paginator
from django.db.models import (
    Q, Count, Exists, OuterRef,
    Avg, Max, F, FloatField,
    ExpressionWrapper, Case, When, Value
)
from django.utils.timezone import now

from quiz.models import UserExam, ExamSubscription, ExamTrackSubscription
from courses.models import CourseSubscription


def is_admin(user):
    return user.is_staff


@user_passes_test(is_admin)
def user_monitoring(request):

    search_query = request.GET.get("q", "")
    sort_by = request.GET.get("sort", "date_joined")
    order = request.GET.get("order", "desc")

    users = User.objects.select_related("profile")

    # =====================================
    # 🔎 SEARCH
    # =====================================
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )

    # =====================================
    # 📝 USER KPIs
    # =====================================
    users = users.annotate(
        total_attempts=Count("exam_attempts", distinct=True),
        avg_score=Avg("exam_attempts__score"),
        passed_count=Count(
            "exam_attempts",
            filter=Q(exam_attempts__passed=True),
            distinct=True
        ),
        last_attempt=Max("exam_attempts__submitted_at"),

                total_course_subs=Count("course_subscriptions", distinct=True),
            )

    # =====================================
    # 🎯 SAFE PASS RATE (avoid division by zero)
    # =====================================
    users = users.annotate(
        pass_rate=Case(
            When(total_attempts=0, then=Value(0.0)),
            default=ExpressionWrapper(
                100.0 * F("passed_count") / F("total_attempts"),
                output_field=FloatField()
            ),
            output_field=FloatField()
        )
    )

    # =====================================
    # 💳 ACTIVE SUBSCRIPTIONS
    # =====================================
    active_exam_sub = ExamSubscription.objects.filter(
        user=OuterRef("pk"),
        is_active=True,
        expires_at__gte=now()
    )

    active_track_sub = ExamTrackSubscription.objects.filter(
        user=OuterRef("pk"),
        is_active=True,
        expires_at__gte=now()
    )

    active_course_sub = CourseSubscription.objects.filter(
        user=OuterRef("pk"),
        is_active=True,
        expires_at__gte=now()
    )

    users = users.annotate(
        has_exam_subscription=Exists(active_exam_sub),
        has_track_subscription=Exists(active_track_sub),
        has_course_subscription=Exists(active_course_sub),
    )

    # =====================================
    # 🔐 SAFE SORTING
    # =====================================
    allowed_sort_fields = {
        "username": "username",
        "first_name": "first_name",
        "email": "email",
        "date_joined": "date_joined",
        "last_login": "last_login",
        "total_attempts": "total_attempts",
        "total_course_subs": "total_course_subs",
        "avg_score": "avg_score",
        "pass_rate": "pass_rate",
    }

    if sort_by in allowed_sort_fields:
        sort_field = allowed_sort_fields[sort_by]
        if order == "desc":
            sort_field = f"-{sort_field}"
        users = users.order_by(sort_field)
    else:
        users = users.order_by("-date_joined")

    # =====================================
    # 📊 GLOBAL KPI SUMMARY
    # =====================================
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()

    total_attempts_all = UserExam.objects.count()

    avg_score_all = UserExam.objects.aggregate(
        avg=Avg("score")
    )["avg"]

    active_exam_subs = ExamSubscription.objects.filter(
        is_active=True,
        expires_at__gte=now()
    ).count()

    active_track_subs = ExamTrackSubscription.objects.filter(
        is_active=True,
        expires_at__gte=now()
    ).count()

    # =====================================
    # 📄 PAGINATION
    # =====================================
    paginator = Paginator(users, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "search_query": search_query,
        "sort_by": sort_by,
        "order": order,
        "total_users": total_users,
        "active_users": active_users,
        "total_attempts_all": total_attempts_all,
        "avg_score_all": avg_score_all,
        "active_exam_subs": active_exam_subs,
        "active_track_subs": active_track_subs,
    }

    return render(request, "accounts/admin/user_monitoring.html", context)
