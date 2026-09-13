from django.contrib.auth import get_user_model
from django.db.models import Q
from django.http import JsonResponse
from django.utils.html import strip_tags
from django.views.decorators.http import require_GET

from courses.models import Course
from organizations.models import Organization, OrganizationMember
from organizations.models.role import OrganizationRole
from quiz.models import Category, Difficulty, Exam, ExamTrack, Notification, Question

SEARCH_LIMIT = 20
ALLOWED_SCOPES = {
    "users", "courses", "tracks", "exams", "questions",
    "categories", "domains", "difficulties", "coupons", "notifications",
    "organizations",
}

User = get_user_model()


def _query(request):
    return (request.GET.get("q") or "").strip()


def _result(item_id, label, subtitle=""):
    return {"id": item_id, "label": label, "subtitle": subtitle}


def _tenant_queryset(queryset, request, include_global=False):
    """Scope searchable content to one tenant; no tenant means platform content."""
    organization_id = (request.GET.get("organization") or "").strip()
    if organization_id:
        if include_global:
            return queryset.filter(Q(organization_id=organization_id) | Q(organization__isnull=True))
        return queryset.filter(organization_id=organization_id)
    return queryset.filter(organization__isnull=True)


def _allowed_ids(request):
    """Return an optional comma-separated ID allow-list for dependent selectors."""
    raw = (request.GET.get("ids") or "").strip()
    if not raw:
        return None
    values = []
    for value in raw.split(","):
        value = value.strip()
        if value.isdigit():
            values.append(int(value))
    return values


def _can_use_autocomplete(request):
    """Allow platform staff or authorized organization teaching members."""
    if not request.user.is_authenticated:
        return False
    if request.user.is_staff:
        return True

    organization_id = (request.GET.get("organization") or "").strip()
    if not organization_id or not organization_id.isdigit():
        return False

    return OrganizationMember.objects.filter(
        user=request.user,
        organization_id=int(organization_id),
        is_active=True,
        role__in=OrganizationRole.teaching_roles(),
    ).exists()


@require_GET
def admin_autocomplete(request):
    """Return small, prefix-matched recommendation lists for admin search fields."""
    if not _can_use_autocomplete(request):
        return JsonResponse({"results": []}, status=403)

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
        qs = _tenant_queryset(Course.objects.filter(title__istartswith=query), request).filter(
            owner_type=Course.OWNER_PLATFORM
        ).order_by("title")[:SEARCH_LIMIT]
        results = [_result(item.id, item.title) for item in qs]
    elif scope == "tracks":
        qs = _tenant_queryset(ExamTrack.objects.filter(title__istartswith=query), request).order_by("title")[:SEARCH_LIMIT]
        results = [_result(item.id, item.title) for item in qs]
    elif scope == "exams":
        qs = _tenant_queryset(
            Exam.objects.filter(title__istartswith=query, is_published=True),
            request,
            include_global=True,
        )
        allowed_ids = _allowed_ids(request)
        if allowed_ids is not None:
            qs = qs.filter(pk__in=allowed_ids)
        qs = qs.order_by("title")[:SEARCH_LIMIT]
        results = [_result(item.id, item.title) for item in qs]
    elif scope == "questions":
        qs = Question.objects.filter(text__istartswith=query).order_by("id")[:SEARCH_LIMIT]
        results = [_result(item.id, strip_tags(item.text or "").strip()[:160]) for item in qs]
    elif scope == "categories":
        qs = _tenant_queryset(
            Category.objects.filter(is_active=True, name__istartswith=query),
            request,
            include_global=True,
        ).select_related("domain", "parent").order_by("name")[:SEARCH_LIMIT]
        results = [
            _result(
                item.id,
                item.full_path(),
                item.domain.name if item.domain else "",
            )
            for item in qs
        ]
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
    elif scope == "organizations":
        qs = Organization.objects.filter(
            Q(name__istartswith=query) | Q(slug__istartswith=query)
        ).order_by("name")[:SEARCH_LIMIT]
        results = [_result(item.id, item.name, item.slug) for item in qs]
    else:
        qs = Notification.objects.filter(title__istartswith=query).order_by("-created_at")[:SEARCH_LIMIT]
        results = [_result(item.id, item.title) for item in qs]

    return JsonResponse({"results": results, "limit": SEARCH_LIMIT, "scope": scope})
