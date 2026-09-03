from django.core.paginator import Paginator
from django.db.models import Q

from courses.models import Course
from quiz.models import Category, Domain, Exam, ExamTrack


DEFAULT_PER_PAGE = 12
MAX_PER_PAGE = 48


def _public_courses():
    return (
        Course.objects
        .filter(
            approval_status=Course.APPROVAL_APPROVED,
            is_published=True,
            is_public=True,
            organization__isnull=True,
            category__domain__is_active=True,
        )
        .select_related("category", "category__domain")
    )


def _public_exams():
    return (
        Exam.objects
        .filter(
            is_published=True,
            organization__isnull=True,
            primary_category__domain__is_active=True,
        )
        .select_related("primary_category", "primary_category__domain", "track")
        .prefetch_related("categories")
    )


def _public_tracks():
    return (
        ExamTrack.objects
        .filter(
            is_active=True,
            organization__isnull=True,
            exams__is_published=True,
            exams__organization__isnull=True,
            exams__primary_category__domain__is_active=True,
        )
        .prefetch_related(
            "exams",
            "exams__primary_category__domain",
        )
        .distinct()
    )


def _domain_for_track(track):
    domains = []
    for exam in track.exams.all():
        if not exam.is_published or exam.organization_id is not None:
            continue
        category = exam.primary_category
        if category and category.domain and category.domain.is_active:
            domains.append(category.domain)
    if not domains:
        return None
    return sorted(domains, key=lambda domain: domain.name.lower())[0]


def _domain_summary(domain, courses, exams, tracks):
    course_ids = [course.id for course in courses if course.category and course.category.domain_id == domain.id]
    exam_ids = [exam.id for exam in exams if exam.primary_category and exam.primary_category.domain_id == domain.id]
    track_ids = []
    for track in tracks:
        track_domain = _domain_for_track(track)
        if track_domain and track_domain.id == domain.id:
            track_ids.append(track.id)
    return {
        "domain": domain,
        "course_count": len(course_ids),
        "exam_count": len(exam_ids),
        "track_count": len(track_ids),
        "course_ids": course_ids,
        "exam_ids": exam_ids,
        "track_ids": track_ids,
    }


def build_learning_catalog(
    *,
    user,
    domain=None,
    query="",
    resource_type="all",
    category=None,
    level=None,
    access=None,
    page=1,
    per_page=DEFAULT_PER_PAGE,
):
    """Build the public, domain-first learning marketplace catalogue.

    The catalogue is discovery-only. Existing access/payment services remain
    authoritative for whether a learner may consume a resource.
    """
    courses = list(_public_courses().order_by("title"))
    exams = list(_public_exams().order_by("title"))
    tracks = list(_public_tracks().order_by("title"))

    active_domains = list(
        Domain.objects
        .filter(is_active=True, organization__isnull=True)
        .order_by("name")
    )

    domains = [
        _domain_summary(item, courses, exams, tracks)
        for item in active_domains
    ]
    domains = [
        item for item in domains
        if item["course_count"] or item["exam_count"] or item["track_count"]
    ]

    selected_domain = domain
    if selected_domain is not None:
        courses = [
            item for item in courses
            if item.category and item.category.domain_id == selected_domain.id
        ]
        exams = [
            item for item in exams
            if item.primary_category and item.primary_category.domain_id == selected_domain.id
        ]
        tracks = [
            item for item in tracks
            if (_domain_for_track(item) and _domain_for_track(item).id == selected_domain.id)
        ]

    if category is not None:
        category_ids = set(category.get_descendants_include_self())
        courses = [
            item for item in courses
            if item.category_id in category_ids
        ]
        exams = [
            item for item in exams
            if item.primary_category_id in category_ids
            or any(cat.id in category_ids for cat in item.categories.all())
        ]

    if query:
        needle = query.strip().lower()
        courses = [item for item in courses if needle in item.title.lower() or needle in (item.category.name.lower() if item.category else "")]
        exams = [item for item in exams if needle in item.title.lower() or needle in (item.primary_category.name.lower() if item.primary_category else "")]
        tracks = [item for item in tracks if needle in item.title.lower() or any(needle in exam.title.lower() for exam in item.exams.all())]

    if resource_type not in {"all", "courses", "tracks", "exams"}:
        resource_type = "all"

    resources = []
    if resource_type in {"all", "courses"}:
        resources.extend({"type": "course", "resource": item} for item in courses)
    if resource_type in {"all", "tracks"}:
        resources.extend({"type": "track", "resource": item} for item in tracks)
    if resource_type in {"all", "exams"}:
        resources.extend({"type": "exam", "resource": item} for item in exams)

    resources.sort(key=lambda item: item["resource"].title.lower())

    paginator = Paginator(resources, min(max(int(per_page), 1), MAX_PER_PAGE))
    try:
        page_number = max(int(page), 1)
    except (TypeError, ValueError):
        page_number = 1
    page_obj = paginator.get_page(page_number)

    selected_categories = Category.objects.filter(
        is_active=True,
        domain=selected_domain,
        organization__isnull=True,
        parent__isnull=True,
    ).order_by("name") if selected_domain else Category.objects.none()

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
