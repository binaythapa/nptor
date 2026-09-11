from datetime import timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from courses.models import Course
from subscriptions.models import Subscription, SubscriptionEntitlement
from subscriptions.services.course_access_service import CourseAccessService
from subscriptions.services.plan_service import get_plan_for_course

User = get_user_model()


def _course_payload(course):
    plans = course.subscription_plans.filter(
        is_active=True,
        scope="resource",
    ).order_by("price", "id")
    return {
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
    }


@staff_member_required
def admin_course_access_data(request):
    courses = (
        Course.objects
        .prefetch_related("subscription_plans")
        .filter(is_published=True)
        .order_by("title")
    )

    subscriptions = (
        SubscriptionEntitlement.objects
        .select_related("subscription", "subscription__user", "subscription__plan", "course")
        .filter(
            resource_type=SubscriptionEntitlement.RESOURCE_COURSE,
            course__isnull=False,
        )
        .order_by("-created_at")
    )

    now = timezone.now()
    active = []
    for entitlement in subscriptions:
        subscription = entitlement.subscription
        is_active = (
            entitlement.is_active
            and subscription.status == Subscription.STATUS_ACTIVE
            and subscription.starts_at <= now
            and (subscription.expires_at is None or subscription.expires_at > now)
        )
        if not is_active:
            continue
        active.append({
            "id": entitlement.id,
            "user_id": subscription.user_id,
            "username": subscription.user.username,
            "course_id": entitlement.course_id,
            "course_title": entitlement.course.title,
            "plan_name": subscription.plan.name if subscription.plan else "—",
            "expires_at": subscription.expires_at.isoformat() if subscription.expires_at else None,
            "expires_display": subscription.expires_at.strftime("%Y-%m-%d %H:%M") if subscription.expires_at else "Lifetime",
        })

    return JsonResponse({
        "courses": [_course_payload(course) for course in courses],
        "active_course_access": active,
    })


@staff_member_required
@require_POST
def admin_subscribe_course(request):
    user = get_object_or_404(User, id=request.POST.get("user_id"))
    course = get_object_or_404(Course, id=request.POST.get("course_id"), is_published=True)
    plan = get_plan_for_course(course, request.POST.get("plan_id") or None)
    try:
        subscription, entitlement = CourseAccessService.grant_admin_access(
            user=user,
            course=course,
            plan=plan,
            granted_by=request.user,
        )
        return JsonResponse({
            "success": True,
            "subscription_id": subscription.id,
            "entitlement_id": entitlement.id,
        })
    except Exception as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=400)


@staff_member_required
@require_POST
def admin_revoke_course(request):
    user = get_object_or_404(User, id=request.POST.get("user_id"))
    course = get_object_or_404(Course, id=request.POST.get("course_id"))
    try:
        result = CourseAccessService.revoke_admin_access(user=user, course=course)
        return JsonResponse({"success": True, **result})
    except ValueError as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=404)
    except Exception as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=400)


@staff_member_required
@require_POST
def admin_update_course_expiry(request):
    user = get_object_or_404(User, id=request.POST.get("user_id"))
    course = get_object_or_404(Course, id=request.POST.get("course_id"))
    entitlement = CourseAccessService.get_user_course_entitlement(user=user, course=course)
    if not entitlement:
        return JsonResponse({"success": False, "error": "Course subscription not found."}, status=404)

    subscription = entitlement.subscription
    expires_at = request.POST.get("expires_at")
    if expires_at:
        from django.utils.dateparse import parse_datetime
        parsed = parse_datetime(expires_at)
        if parsed is None:
            return JsonResponse({"success": False, "error": "Invalid expiry date."}, status=400)
        if timezone.is_naive(parsed):
            parsed = timezone.make_aware(parsed)
        subscription.expires_at = parsed
    else:
        subscription.expires_at = None
    subscription.status = Subscription.STATUS_ACTIVE
    subscription.cancelled_at = None
    subscription.save(update_fields=["expires_at", "status", "cancelled_at", "updated_at"])

    from organizations.models.access import ResourceAccess
    access = ResourceAccess.objects.filter(
        user=user,
        resource_type=ResourceAccess.RESOURCE_COURSE,
        course=course,
        source=ResourceAccess.SOURCE_ADMIN,
        subscription=subscription,
    ).first()
    if access:
        access.is_active = True
        access.revoked_at = None
        access.expires_at = subscription.expires_at
        access.save(update_fields=["is_active", "revoked_at", "expires_at", "updated_at"])

    return JsonResponse({"success": True})


@staff_member_required
@require_POST
def admin_add_course_days(request):
    user = get_object_or_404(User, id=request.POST.get("user_id"))
    course = get_object_or_404(Course, id=request.POST.get("course_id"))
    try:
        days = int(request.POST.get("days"))
    except (TypeError, ValueError):
        return JsonResponse({"success": False, "error": "Invalid number of days."}, status=400)
    if days <= 0:
        return JsonResponse({"success": False, "error": "Days must be greater than zero."}, status=400)

    entitlement = CourseAccessService.get_user_course_entitlement(user=user, course=course)
    if not entitlement:
        return JsonResponse({"success": False, "error": "Course subscription not found."}, status=404)

    subscription = entitlement.subscription
    subscription.expires_at = (subscription.expires_at or timezone.now()) + timedelta(days=days)
    subscription.status = Subscription.STATUS_ACTIVE
    subscription.cancelled_at = None
    subscription.save(update_fields=["expires_at", "status", "cancelled_at", "updated_at"])

    return JsonResponse({"success": True, "expires_at": subscription.expires_at.isoformat()})
