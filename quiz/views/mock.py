

from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import get_user_model

from django.core.paginator import Paginator
from django.db.models import Q
from quiz.models import UserExam, Exam
from django.contrib.auth import get_user_model

User = get_user_model()


@staff_member_required
def reset_mock_attempts(request):
    """
    Admin-only:
    Reset mock attempts for a selected user + exam
    """

    if request.method != "POST":
        return redirect("quiz:admin_dashboard")

    user_id = request.POST.get("user_id")
    exam_id = request.POST.get("exam_id")

    if not user_id or not exam_id:
        messages.error(request, "Please select both student and exam.")
        return redirect("quiz:admin_dashboard")

    user = get_object_or_404(User, id=user_id)
    exam = get_object_or_404(Exam, id=exam_id)

    deleted_count, _ = UserExam.objects.filter(
        user=user,
        exam=exam,
        passed__isnull=True,            # ✅ mock attempt
        submitted_at__isnull=False
    ).delete()

    if deleted_count > 0:
        messages.success(
            request,
            f"Reset {deleted_count} mock attempt(s) for {user.username} — {exam.title}"
        )
    else:
        messages.info(
            request,
            "No mock attempts found for the selected student & exam."
        )

    return redirect("quiz:admin_dashboard")




@staff_member_required
def admin_mock_attempts(request):
    """
    Dedicated admin page for managing mock attempts.
    Reset logic stays in reset_mock_attempts view.
    """

    context = {
        "students": User.objects.filter(is_active=True).order_by("username"),
        "exams": Exam.objects.order_by("title"),
    }

    return render(
        request,
        "quiz/subscription/admin/mock_attempts.html",
        context
    )


@staff_member_required
def admin_mock_attempt_history(request):
    """
    Mock attempt history with filters + pagination
    """

    attempts = (
        UserExam.objects
        .select_related("user", "exam")
        .filter(
            submitted_at__isnull=False,
            exam__max_mock_attempts__gt=0  # mock exams only
        )
        .order_by("-submitted_at")
    )

    # ---------------- FILTERS ----------------
    user_id = request.GET.get("user")
    exam_id = request.GET.get("exam")
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")

    if user_id:
        attempts = attempts.filter(user_id=user_id)

    if exam_id:
        attempts = attempts.filter(exam_id=exam_id)

    if date_from:
        attempts = attempts.filter(submitted_at__date__gte=date_from)

    if date_to:
        attempts = attempts.filter(submitted_at__date__lte=date_to)

    # ---------------- PAGINATION ----------------
    paginator = Paginator(attempts, 20)  # 20 rows per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "attempts": page_obj.object_list,

        # filter dropdown data
        "users": User.objects.filter(is_active=True).order_by("username"),
        "exams": Exam.objects.order_by("title"),

        # preserve filter state
        "selected_user": user_id,
        "selected_exam": exam_id,
        "date_from": date_from,
        "date_to": date_to,
    }

    return render(
        request,
        "quiz/subscription/admin/mock_attempt_history.html",
        context
    )


