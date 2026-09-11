from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from courses.models import Course
from quiz.models import ExamTrack

User = get_user_model()

SEARCH_LIMIT = 20


def _query(request):
    return (request.GET.get("q") or "").strip()


@staff_member_required
@require_GET
def admin_subscription_user_search(request):
    query = _query(request)
    if not query:
        return JsonResponse({"results": []})

    users = (
        User.objects
        .filter(is_active=True)
        .filter(username__istartswith=query)
        .order_by("username")[:SEARCH_LIMIT]
    )
    return JsonResponse({
        "results": [
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "label": f"{user.username} — {user.email}" if user.email else user.username,
            }
            for user in users
        ]
    })


@staff_member_required
@require_GET
def admin_subscription_course_search(request):
    query = _query(request)
    if not query:
        return JsonResponse({"results": []})

    courses = (
        Course.objects
        .prefetch_related("subscription_plans")
        .filter(is_published=True, title__istartswith=query)
        .order_by("title")[:SEARCH_LIMIT]
    )
    results = []
    for course in courses:
        plans = course.subscription_plans.filter(
            is_active=True,
            scope="resource",
        ).order_by("price", "id")
        results.append({
            "id": course.id,
            "title": course.title,
            "plans": [
                {
                    "id": plan.id,
                    "name": plan.name,
                    "price": str(plan.price),
                    "currency": plan.currency,
                    "duration_days": plan.duration_days,
                }
                for plan in plans
            ],
        })

    return JsonResponse({"results": results})


@staff_member_required
@require_GET
def admin_subscription_track_search(request):
    query = _query(request)
    if not query:
        return JsonResponse({"results": []})

    tracks = (
        ExamTrack.objects
        .filter(is_active=True, title__istartswith=query)
        .order_by("title")[:SEARCH_LIMIT]
    )
    return JsonResponse({
        "results": [
            {
                "id": track.id,
                "title": track.title,
            }
            for track in tracks
        ]
    })
