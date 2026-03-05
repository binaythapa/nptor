from django.shortcuts import render, redirect, get_object_or_404
from organizations.permissions import org_admin_required
from quiz.models import Category, Domain
from quiz.forms import CategoryForm


# =========================
# LIST
# =========================
@org_admin_required
def org_category_list(request, slug):

    categories = (
        Category.objects
        .select_related("domain", "parent")
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

    if request.method == "POST":

        form = CategoryForm(request.POST)

        if form.is_valid():
            form.save()
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

    category = get_object_or_404(Category, pk=pk)

    if request.method == "POST":

        form = CategoryForm(
            request.POST,
            instance=category
        )

        if form.is_valid():
            form.save()

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

    category = get_object_or_404(Category, pk=pk)

    category.delete()

    return redirect(
        "organizations_admin:category_list",
        slug=slug
    )