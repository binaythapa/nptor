from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from courses.models import Course
from quiz.models import Category, Difficulty, Exam, ExamTrack, Notification, Question

SEARCH_LIMIT = 20
ALLOWED_SCOPES = {
    "users", "courses", "tracks", "exams", "questions",
    "categories", "domains", "difficulties", "coupons", "notifications",
}

User = get_user_model()


def _query(request):
    return (request.GET.get("q") or "").strip()


def _result(item_id, label, subtitle=""):
    return {"id": item_id, "label": label, "subtitle": subtitle}


@staff_member_required
@require_GET
def admin_autocomplete(request):
    """Return small, prefix-matched recommendation lists for admin search fields."""
    query = _query(request)
    scope = (request.GET.get("scope") or "").strip().lower()

    if not query or scope not in ALLOWED_SCOPES:
        return JsonResponse({"results": []})

    if scope == "users":
        qs = (
            User.objects.filter(is_active=True)
            .filter(
                Q(username__istartswith=query)
                | Q(first_name__istartswith=query)
                | Q(last_name__istartswith=query)
                | Q(email__istartswith=query)
            )
            .order_by("username")[:SEARCH_LIMIT]
        )
        results = [_result(u.id, u.username, u.email or u.get_full_name()) for u in qs]
    elif scope == "courses":
        qs = Course.objects.filter(title__istartswith=query).order_by("title")[:SEARCH_LIMIT]
        results = [_result(item.id, item.title) for item in qs]
    elif scope == "tracks":
        qs = ExamTrack.objects.filter(title__istartswith=query).order_by("title")[:SEARCH_LIMIT]
        results = [_result(item.id, item.title) for item in qs]
    elif scope == "exams":
        qs = Exam.objects.filter(title__istartswith=query).order_by("title")[:SEARCH_LIMIT]
        results = [_result(item.id, item.title) for item in qs]
    elif scope == "questions":
        qs = Question.objects.filter(text__istartswith=query).order_by("id")[:SEARCH_LIMIT]
        results = [_result(item.id, item.text) for item in qs]
    elif scope == "categories":
        qs = Category.objects.filter(is_active=True, name__istartswith=query).order_by("name")[:SEARCH_LIMIT]
        results = [_result(item.id, item.name) for item in qs]
    elif scope == "domains":
        qs = __import__("quiz.models", fromlist=["Domain"]).Domain.objects.filter(
            is_active=True, name__istartswith=query
        ).order_by("name")[:SEARCH_LIMIT]
        results = [_result(item.id, item.name) for item in qs]
    elif scope == "difficulties":
        qs = Difficulty.objects.filter(is_active=True, name__istartswith=query).order_by("name")[:SEARCH_LIMIT]
        results = [_result(item.id, item.name) for item in qs]
    elif scope == "coupons":
        qs = __import__("quiz.models", fromlist=["Coupon"]).Coupon.objects.filter(
            is_active=True, code__istartswith=query
        ).order_by("code")[:SEARCH_LIMIT]
        results = [_result(item.id, item.code) for item in qs]
    else:
        qs = Notification.objects.filter(title__istartswith=query).order_by("-created_at")[:SEARCH_LIMIT]
        results = [_result(item.id, item.title) for item in qs]

    return JsonResponse({"results": results, "limit": SEARCH_LIMIT, "scope": scope})
