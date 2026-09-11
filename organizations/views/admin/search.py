from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET

from courses.models import Course
from organizations.models import OrganizationMember, OrganizationStudent
from organizations.permissions import org_admin_required
from quiz.models import Category, Exam, ExamTrack, Question
from quiz.models.category import Domain

SEARCH_LIMIT = 20


def _result(label, subtitle, url, result_type):
    return {
        "label": label,
        "subtitle": subtitle,
        "url": url,
        "type": result_type,
    }


def _search_results(organization, query, slug):
    q = query.strip()
    if not q:
        return []

    results = []
    student_qs = (
        OrganizationStudent.objects.filter(
            organization=organization,
            status=OrganizationStudent.STATUS_ACTIVE,
        )
        .filter(
            Q(user__username__istartswith=q)
            | Q(user__first_name__istartswith=q)
            | Q(user__last_name__istartswith=q)
            | Q(student_id__istartswith=q)
            | Q(admission_no__istartswith=q)
        )
        .select_related("user")
        .order_by("user__username")[:SEARCH_LIMIT]
    )
    results.extend(
        _result(
            student.display_name,
            "Student",
            reverse("organizations_public:student_profile_admin", kwargs={"slug": slug, "student_id": student.id}),
            "student",
        )
        for student in student_qs
    )

    courses = (
        Course.objects.filter(Q(organization=organization) | Q(organization__isnull=True), is_published=True)
        .filter(title__istartswith=q)
        .order_by("title")[:SEARCH_LIMIT]
    )
    results.extend(
        _result(
            course.title,
            "Course",
            reverse("organizations_admin:courses", kwargs={"slug": slug}),
            "course",
        )
        for course in courses
    )

    tracks = (
        ExamTrack.objects.filter(Q(organization=organization) | Q(organization__isnull=True))
        .filter(title__istartswith=q)
        .order_by("title")[:SEARCH_LIMIT]
    )
    results.extend(
        _result(
            track.title,
            "Learning Track",
            reverse("organizations_admin:org_track_list", kwargs={"slug": slug}),
            "track",
        )
        for track in tracks
    )

    exams = (
        Exam.objects.filter(Q(organization=organization) | Q(organization__isnull=True))
        .filter(title__istartswith=q)
        .order_by("title")[:SEARCH_LIMIT]
    )
    results.extend(
        _result(
            exam.title,
            "Exam",
            reverse("organizations_admin:exams", kwargs={"slug": slug}),
            "exam",
        )
        for exam in exams
    )

    questions = (
        Question.objects.filter(Q(organization=organization) | Q(organization__isnull=True))
        .filter(text__istartswith=q)
        .order_by("id")[:SEARCH_LIMIT]
    )
    for question in questions:
        text = " ".join((question.text or "").replace("<", " <").split())[:120]
        results.append(
            _result(
                text,
                "Question",
                reverse("organizations_admin:questions", kwargs={"slug": slug}),
                "question",
            )
        )

    categories = (
        Category.objects.filter(Q(organization=organization) | Q(organization__isnull=True), is_active=True)
        .filter(name__istartswith=q)
        .order_by("name")[:SEARCH_LIMIT]
    )
    results.extend(
        _result(
            category.name,
            "Category",
            reverse("organizations_admin:category_list", kwargs={"slug": slug}),
            "category",
        )
        for category in categories
    )

    domains = (
        Domain.objects.filter(Q(organization=organization) | Q(organization__isnull=True), is_active=True)
        .filter(name__istartswith=q)
        .order_by("name")[:SEARCH_LIMIT]
    )
    results.extend(
        _result(
            domain.name,
            "Domain",
            reverse("organizations_admin:domain_list", kwargs={"slug": slug}),
            "domain",
        )
        for domain in domains
    )

    return results[:SEARCH_LIMIT]


@org_admin_required
@require_GET
def org_autocomplete(request, slug):
    query = (request.GET.get("q") or "").strip()
    if not query:
        return JsonResponse({"results": [], "limit": SEARCH_LIMIT})
    return JsonResponse({"results": _search_results(request.organization, query, slug), "limit": SEARCH_LIMIT})


@org_admin_required
def org_search(request, slug):
    query = (request.GET.get("q") or "").strip()
    results = _search_results(request.organization, query, slug) if query else []
    return render(
        request,
        "organizations/admin/search.html",
        {"org": request.organization, "query": query, "results": results},
    )
