from django.core.paginator import Paginator
from django.db.models import Prefetch

from courses.models import Course
from quiz.models import Category, ContentVertical, Domain, Exam, ExamTrack, LearningShortlist
from subscriptions.models.plan import SubscriptionPlan
from subscriptions.services import AccessService


DEFAULT_PER_PAGE = 12
MAX_PER_PAGE = 48
DOMAIN_PER_PAGE = 24
POPULAR_DOMAIN_COUNT = 8
VALID_RESOURCE_TYPES = {"all", "courses", "tracks"}
VALID_ACCESS_FILTERS = {"", "owned", "available"}
VALID_PRICING_FILTERS = {"", "free", "premium"}
VALID_DOMAIN_SORTS = {"az", "za"}
VALID_CATALOG_VERTICALS = {
    value for value, _ in ContentVertical.TYPE_CHOICES
}


def _public_courses():
    return Course.objects.filter(
        approval_status=Course.APPROVAL_APPROVED,
        is_published=True,
        is_public=True,
        organization__isnull=True,
        category__is_active=True,
        category__organization__isnull=True,
        category__domain__is_active=True,
        category__domain__organization__isnull=True,
    ).select_related("category", "category__domain").prefetch_related(
        Prefetch("subscription_plans", queryset=SubscriptionPlan.objects.filter(is_active=True))
    )


def _public_exams():
    return Exam.objects.filter(
        is_published=True,
        organization__isnull=True,
        primary_category__is_active=True,
        primary_category__organization__isnull=True,
        primary_category__domain__is_active=True,
        primary_category__domain__organization__isnull=True,
    ).select_related("primary_category", "primary_category__domain").prefetch_related(
        Prefetch("subscription_plans", queryset=SubscriptionPlan.objects.filter(is_active=True)),
        "categories",
    )


def _public_tracks():
    return ExamTrack.objects.filter(
        is_active=True,
        organization__isnull=True,
        track_exams__exam__is_published=True,
        track_exams__exam__organization__isnull=True,
        track_exams__exam__primary_category__is_active=True,
        track_exams__exam__primary_category__organization__isnull=True,
        track_exams__exam__primary_category__domain__is_active=True,
        track_exams__exam__primary_category__domain__organization__isnull=True,
    ).prefetch_related(
        "track_exams__exam",
        "track_exams__exam__primary_category__domain",
        Prefetch("subscription_plans", queryset=SubscriptionPlan.objects.filter(is_active=True)),
    ).distinct()


def _track_exams(track):
    manager = getattr(track, "track_exams", None)
    if manager is not None:
        return [item.exam for item in manager.all()]
    legacy_manager = getattr(track, "exams", None)
    if legacy_manager is not None:
        return list(legacy_manager.all())
    return []


def _domain_for_track(track):
    domains = []
    for membership in getattr(track, "track_exams", []).all() if getattr(track, "track_exams", None) is not None else []:
        exam = membership.exam
        if not exam.is_published or exam.organization_id is not None:
            continue
        category = exam.primary_category
        if category and category.domain and category.domain.is_active and category.domain.organization_id is None:
            domains.append(category.domain)
    if not domains:
        return None
    return sorted(domains, key=lambda domain: domain.name.lower())[0]


def _matches_vertical(domain, catalog_vertical):
    if not catalog_vertical:
        return True
    return bool(domain and domain.content_vertical_id and domain.content_vertical.vertical_type == catalog_vertical)


def _domain_summary(domain, courses, exams, tracks):
    course_ids = [course.id for course in courses if course.category and course.category.domain_id == domain.id]
    exam_ids = [exam.id for exam in exams if exam.primary_category and exam.primary_category.domain_id == domain.id]
    track_ids = [track.id for track in tracks if (_domain_for_track(track) and _domain_for_track(track).id == domain.id)]
    return {"domain": domain, "course_count": len(course_ids), "exam_count": len(exam_ids), "track_count": len(track_ids), "course_ids": course_ids, "exam_ids": exam_ids, "track_ids": track_ids}


def _matches_query(resource, resource_type, needle):
    if not needle:
        return True
    if needle in resource.title.lower():
        return True
    if resource_type == "course":
        category = getattr(resource, "category", None)
        return bool(category and needle in category.name.lower())
    if resource_type == "exam":
        category = getattr(resource, "primary_category", None)
        return bool(category and needle in category.name.lower())
    return any(needle in exam.title.lower() for exam in _track_exams(resource) if exam.is_published)


def _matches_level(resource, resource_type, level):
    if not level:
        return True
    if resource_type == "course":
        return resource.level == level
    try:
        return resource.level == int(level)
    except (TypeError, ValueError):
        return False


def _has_access(user, resource_type, resource):
    return AccessService.has_access(student=user, resource_type=resource_type, resource=resource)


def _active_plans(resource):
    prefetched = getattr(resource, "_prefetched_objects_cache", {}).get("subscription_plans")
    if prefetched is not None:
        return [plan for plan in prefetched if getattr(plan, "is_active", True)]
    manager = getattr(resource, "subscription_plans", None)
    if manager is None:
        return []
    if hasattr(manager, "filter"):
        return list(manager.filter(is_active=True))
    return [plan for plan in manager if getattr(plan, "is_active", True)]


def _resource_item(resource_type, resource):
    item = {
        "type": resource_type,
        "presentation_type": resource_type,
        "resource": resource,
        "is_shortlisted": False,
        "access_label": "Available",
        "pricing_label": "Free",
        "price_label": "Free",
    }
    if resource_type == "course":
        plans = _active_plans(resource)
        item["pricing_label"] = "Premium" if plans else "Free"
        item["description_label"] = "Structured learning course"
        if plans:
            plan = min(plans, key=lambda value: value.price)
            item["price_label"] = f"{plan.currency} {plan.price:,.2f}"
    elif resource_type == "track":
        published_exams = [
            exam for exam in _track_exams(resource)
            if exam.is_published and exam.organization_id is None
        ]
        domain = _domain_for_track(resource)
        item["domain_slug"] = domain.slug if domain else ""
        item["exam_count"] = len(published_exams)
        item["question_count"] = sum(exam.question_count for exam in published_exams)
        is_free = not _active_plans(resource) and resource.pricing_type == resource.PRICING_FREE
        item["pricing_label"] = "Free" if is_free else "Premium"
        item["description_label"] = "Structured certification preparation"
        if is_free:
            item["price_label"] = "Free"
        elif resource.lifetime_price is not None:
            item["price_label"] = f"{resource.currency} {resource.lifetime_price:,.2f}"
        elif resource.monthly_price is not None:
            item["price_label"] = f"{resource.currency} {resource.monthly_price:,.2f} / month"
        elif _active_plans(resource):
            plan = min(_active_plans(resource), key=lambda value: value.price)
            item["price_label"] = f"{plan.currency} {plan.price:,.2f}"
        else:
            item["price_label"] = "Premium"
        item["metrics_label"] = f"{item['exam_count']} exams included · {item['question_count']} questions"
    return item


def _add_user_state(user, items):
    shortlist_rows = LearningShortlist.objects.filter(user=user)
    shortlisted = {(row.resource_type, row.course_id or row.track_id or row.exam_id) for row in shortlist_rows}
    for item in items:
        resource_type = getattr(AccessService, f"RESOURCE_{item['type'].upper()}")
        resource = item["resource"]
        item["has_access"] = _has_access(user, resource_type, resource)
        item["is_shortlisted"] = (resource_type, resource.id) in shortlisted
        if item["has_access"]:
            item["access_label"] = "You have access"
        elif item["pricing_label"] == "Premium":
            item["access_label"] = "Premium"
        else:
            item["access_label"] = "Free"


def _paginate(items, page, per_page=DEFAULT_PER_PAGE):
    paginator = Paginator(items, min(max(int(per_page), 1), MAX_PER_PAGE))
    return paginator.get_page(page)
