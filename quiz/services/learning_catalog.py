from django.core.paginator import Paginator
from django.db.models import Prefetch

from courses.models import Course
from quiz.models import Category, Domain, Exam, ExamTrack, LearningShortlist
from subscriptions.models.plan import SubscriptionPlan
from subscriptions.services import AccessService


DEFAULT_PER_PAGE = 12
MAX_PER_PAGE = 48
VALID_RESOURCE_TYPES = {"all", "courses", "tracks", "exams"}
VALID_ACCESS_FILTERS = {"", "owned", "available"}


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
        Prefetch(
            "subscription_plans",
            queryset=SubscriptionPlan.objects.filter(is_active=True),
        )
    )


def _public_exams():
    return Exam.objects.filter(
        is_published=True,
        organization__isnull=True,
        primary_category__is_active=True,
        primary_category__organization__isnull=True,
        primary_category__domain__is_active=True,
        primary_category__domain__organization__isnull=True,
    ).select_related(
        "primary_category",
        "primary_category__domain",
        "track",
    ).prefetch_related("categories")


def _public_tracks():
    return ExamTrack.objects.filter(
        is_active=True,
        organization__isnull=True,
        exams__is_published=True,
        exams__organization__isnull=True,
        exams__primary_category__is_active=True,
        exams__primary_category__organization__isnull=True,
        exams__primary_category__domain__is_active=True,
        exams__primary_category__domain__organization__isnull=True,
    ).prefetch_related(
        "exams",
        "exams__primary_category__domain",
        Prefetch(
            "subscription_plans",
            queryset=SubscriptionPlan.objects.filter(is_active=True),
        ),
    ).distinct()


def _domain_for_track(track):
    domains = []
    for exam in track.exams.all():
        if not exam.is_published or exam.organization_id is not None:
            continue
        category = exam.primary_category
        if category and category.domain and category.domain.is_active and category.domain.organization_id is None:
            domains.append(category.domain)
    if not domains:
        return None
    return sorted(domains, key=lambda domain: domain.name.lower())[0]


def _domain_summary(domain, courses, exams, tracks):
    course_ids = [course.id for course in courses if course.category and course.category.domain_id == domain.id]
    exam_ids = [exam.id for exam in exams if exam.primary_category and exam.primary_category.domain_id == domain.id]
    track_ids = [track.id for track in tracks if (_domain_for_track(track) and _domain_for_track(track).id == domain.id)]
    return {
        "domain": domain,
        "course_count": len(course_ids),
        "exam_count": len(exam_ids),
        "track_count": len(track_ids),
        "course_ids": course_ids,
        "exam_ids": exam_ids,
        "track_ids": track_ids,
    }


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
    return any(needle in exam.title.lower() for exam in resource.exams.all() if exam.is_published)


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
        return list(prefetched)
    return list(resource.subscription_plans.filter(is_active=True))


def _resource_item(resource_type, resource):
    """Build presentation metadata without making access decisions."""
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

    elif resource_type == "exam":
        item["duration_minutes"] = (resource.duration_seconds or 0) // 60
        item["pricing_label"] = "Free" if resource.is_free else "Premium"
        item["description_label"] = "Timed practice and assessment"
        item["metrics_label"] = (
            f"{resource.question_count} questions · "
            f"{item['duration_minutes']} min · "
            f"Pass {resource.passing_score:g}%"
        )
        if not resource.is_free and resource.price is not None:
            item["price_label"] = f"{resource.currency} {resource.price:,.2f}"

    elif resource_type == "track":
        published_exams = [
            exam for exam in resource.exams.all()
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
        item["metrics_label"] = (
            f"{item['exam_count']} exams included · "
            f"{item['question_count']} questions"
        )

    return item


def _add_user_state(user, items):
    shortlist_rows = LearningShortlist.objects.filter(user=user)
    shortlisted = {
        (row.resource_type, row.course_id or row.track_id or row.exam_id)
        for row in shortlist_rows
    }
    for item in items:
        resource_type = getattr(AccessService, f"RESOURCE_{item['type'].upper()}")
        resource = item["resource"]
        item["is_shortlisted"] = (item["type"], resource.id) in shortlisted
        item["has_access"] = _has_access(user, resource_type, resource)
        if item["has_access"]:
            item["access_label"] = "Purchased"
        elif item["pricing_label"] == "Premium":
            item["access_label"] = "Premium"
        else:
            item["access_label"] = "Free"
    return items


def build_learning_catalog(*, user, domain=None, query="", resource_type="all", category=None, level=None, access=None, page=1, per_page=DEFAULT_PER_PAGE):
    """Build the public domain-first learning marketplace catalogue."""
    courses = list(_public_courses().order_by("title"))
    exams = list(_public_exams().order_by("title"))
    tracks = list(_public_tracks().order_by("title"))

    active_domains = list(Domain.objects.filter(is_active=True, organization__isnull=True).order_by("name"))
    domains = [_domain_summary(item, courses, exams, tracks) for item in active_domains]
    domains = [item for item in domains if item["course_count"] or item["exam_count"] or item["track_count"]]

    selected_domain = domain
    if selected_domain is not None:
        courses = [item for item in courses if item.category and item.category.domain_id == selected_domain.id]
        exams = [item for item in exams if item.primary_category and item.primary_category.domain_id == selected_domain.id]
        tracks = [item for item in tracks if (_domain_for_track(item) and _domain_for_track(item).id == selected_domain.id)]

    if category is not None:
        category_ids = set(category.get_descendants_include_self())
        courses = [item for item in courses if item.category_id in category_ids]
        exams = [item for item in exams if item.primary_category_id in category_ids or any(cat.id in category_ids for cat in item.categories.all())]

    if resource_type not in VALID_RESOURCE_TYPES:
        resource_type = "all"
    if access not in VALID_ACCESS_FILTERS:
        access = ""

    needle = query.lower()
    courses = [item for item in courses if _matches_query(item, "course", needle)]
    exams = [item for item in exams if _matches_query(item, "exam", needle)]
    tracks = [item for item in tracks if _matches_query(item, "track", needle)]

    courses = [item for item in courses if _matches_level(item, "course", level)]
    exams = [item for item in exams if _matches_level(item, "exam", level)]
    tracks = [item for item in tracks if not level or any(_matches_level(exam, "exam", level) for exam in item.exams.all())]

    resources = []
    if resource_type in {"all", "courses"}:
        resources.extend(_resource_item("course", item) for item in courses)
    if resource_type in {"all", "tracks"}:
        resources.extend(_resource_item("track", item) for item in tracks)
    if resource_type in {"all", "exams"}:
        resources.extend(_resource_item("exam", item) for item in exams)

    resources.sort(key=lambda item: item["resource"].title.lower())

    if access in {"owned", "available"}:
        resources = _add_user_state(user, resources)
        resources = [item for item in resources if (access == "owned" and item["has_access"]) or (access == "available" and not item["has_access"])]

    try:
        page_size = min(max(int(per_page), 1), MAX_PER_PAGE)
    except (TypeError, ValueError):
        page_size = DEFAULT_PER_PAGE
    paginator = Paginator(resources, page_size)
    try:
        page_number = max(int(page), 1)
    except (TypeError, ValueError):
        page_number = 1
    page_obj = paginator.get_page(page_number)

    if access not in {"owned", "available"}:
        _add_user_state(user, page_obj.object_list)

    selected_categories = (
        Category.objects.filter(
            is_active=True,
            domain=selected_domain,
            organization__isnull=True,
            parent__isnull=True,
        ).order_by("name")
        if selected_domain else Category.objects.none()
    )

    return {
        "domains": domains,
        "resources": page_obj.object_list,
        "page_obj": page_obj,
        "selected_domain": selected_domain,
        "categories": selected_categories,
        "query": query,
        "resource_type": resource_type,
        "category": category,
        "level": level,
        "access": access,
    }
