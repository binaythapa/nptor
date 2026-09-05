from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from quiz.models import Category, Domain
from quiz.services.learning_catalog import build_learning_catalog


@login_required
def learning_marketplace(request, catalog_vertical=None):
    query = request.GET.get("q", "").strip()
    resource_type = request.GET.get("type", "all").strip().lower()
    level = request.GET.get("level", "").strip()
    access = request.GET.get("access", "").strip().lower()
    pricing = request.GET.get("pricing", "").strip().lower()
    domain_query = request.GET.get("domain_q", "").strip()
    domain_sort = request.GET.get("domain_sort", "az").strip().lower()
    domain_page = request.GET.get("domain_page", 1)

    catalog = build_learning_catalog(
        user=request.user,
        query=query,
        resource_type=resource_type,
        level=level,
        access=access,
        pricing=pricing,
        page=request.GET.get("page", 1),
        domain_query=domain_query,
        domain_sort=domain_sort,
        domain_page=domain_page,
        catalog_vertical=catalog_vertical,
    )

    return render(request, "quiz/student/learning_marketplace.html", catalog)


@login_required
def learning_domain(request, slug):
    domain = get_object_or_404(
        Domain.objects.filter(is_active=True, organization__isnull=True),
        slug=slug,
    )

    query = request.GET.get("q", "").strip()
    resource_type = request.GET.get("type", "all").strip().lower()
    category_slug = request.GET.get("category", "").strip()
    level = request.GET.get("level", "").strip()
    access = request.GET.get("access", "").strip().lower()
    pricing = request.GET.get("pricing", "").strip().lower()

    category = None
    if category_slug:
        category = get_object_or_404(
            Category.objects.filter(
                is_active=True,
                organization__isnull=True,
                domain=domain,
            ),
            slug=category_slug,
        )

    catalog = build_learning_catalog(
        user=request.user,
        domain=domain,
        query=query,
        resource_type=resource_type,
        category=category,
        level=level,
        access=access,
        pricing=pricing,
        page=request.GET.get("page", 1),
    )
    catalog["category"] = category

    return render(request, "quiz/student/domain_hub.html", catalog)
