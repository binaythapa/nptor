from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q

from organizations.permissions import org_admin_required

from quiz.models import Category
from quiz.forms import CategoryForm


# =========================
# LIST
# =========================
@org_admin_required
def org_category_list(request, slug):

    org = request.organization

    categories = (
        Category.objects
        .select_related("domain", "parent")
        .filter(
            Q(domain__organization=org) | Q(domain__organization__isnull=True)
        )
        .order_by("domain__name", "name")
    )

    return render(
        request,
        "organizations/admin/categories/list.html",
        {
            "categories": categories
        }
    )


# =========================
# CREATE
# =========================
@org_admin_required
def org_category_create(request, slug):

    org = request.organization

    if request.method == "POST":

        form = CategoryForm(request.POST)

        if form.is_valid():
            obj = form.save(commit=False)

            # 🔒 Prevent assigning category to another org's domain
            if obj.domain and obj.domain.organization not in [org, None]:
                return redirect("organizations_admin:category_list", slug=slug)

            obj.save()

            return redirect(
                "organizations_admin:category_list",
                slug=slug
            )

    else:
        form = CategoryForm()

    return render(
        request,
        "organizations/admin/categories/create.html",
        {"form": form}
    )


# =========================
# UPDATE
# =========================
@org_admin_required
def org_category_edit(request, slug, pk):

    org = request.organization

    category = get_object_or_404(
        Category,
        Q(pk=pk) &
        (Q(domain__organization=org) | Q(domain__organization__isnull=True))
    )

    if request.method == "POST":

        form = CategoryForm(
            request.POST,
            instance=category
        )

        if form.is_valid():
            obj = form.save(commit=False)

            # 🔒 Prevent switching to another org domain
            if obj.domain and obj.domain.organization not in [org, None]:
                return redirect("organizations_admin:category_list", slug=slug)

            obj.save()

            return redirect(
                "organizations_admin:category_list",
                slug=slug
            )

    else:
        form = CategoryForm(instance=category)

    return render(
        request,
        "organizations/admin/categories/edit.html",
        {
            "form": form,
            "category": category
        }
    )


# =========================
# DELETE
# =========================
@org_admin_required
def org_category_delete(request, slug, pk):

    org = request.organization

    category = get_object_or_404(
        Category,
        Q(pk=pk) &
        (Q(domain__organization=org) | Q(domain__organization__isnull=True))
    )

    category.delete()

    return redirect(
        "organizations_admin:category_list",
        slug=slug
    )