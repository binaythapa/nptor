from django import forms
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify

from quiz.models import Category, ContentVertical, Domain


class GlobalDomainForm(forms.ModelForm):
    class Meta:
        model = Domain
        fields = ["content_vertical", "name", "slug", "is_active"]
        widgets = {
            "content_vertical": forms.Select(attrs={"class": "select"}),
            "name": forms.TextInput(attrs={"class": "input", "placeholder": "Domain name"}),
            "slug": forms.TextInput(attrs={"class": "input", "placeholder": "domain-slug"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["content_vertical"].queryset = ContentVertical.objects.filter(is_active=True).order_by("name")
        self.fields["content_vertical"].required = False
        self.fields["content_vertical"].help_text = "Optional top-level catalog vertical."
        self.fields["slug"].help_text = "Used in URLs and must be unique among global domains."

    def clean_slug(self):
        value = slugify(self.cleaned_data.get("slug", ""))
        if not value:
            raise forms.ValidationError("Enter a valid slug.")
        qs = Domain.objects.filter(organization__isnull=True, slug=value)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A global domain with this slug already exists.")
        return value


class GlobalCategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["domain", "name", "slug", "parent", "is_active"]
        widgets = {
            "domain": forms.Select(attrs={"class": "select"}),
            "name": forms.TextInput(attrs={"class": "input", "placeholder": "Category name"}),
            "slug": forms.TextInput(attrs={"class": "input", "placeholder": "category-slug"}),
            "parent": forms.Select(attrs={"class": "select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["domain"].queryset = Domain.objects.filter(organization__isnull=True).order_by("name")
        self.fields["domain"].required = False
        self.fields["domain"].help_text = "A global category can optionally belong to a global domain."
        self.fields["parent"].required = False
        self.fields["parent"].queryset = Category.objects.filter(organization__isnull=True).select_related("domain").order_by("name")

    def clean_slug(self):
        value = slugify(self.cleaned_data.get("slug", ""))
        if not value:
            raise forms.ValidationError("Enter a valid slug.")
        qs = Category.objects.filter(organization__isnull=True, slug=value)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A global category with this slug already exists.")
        return value

    def clean(self):
        cleaned = super().clean()
        domain = cleaned.get("domain")
        parent = cleaned.get("parent")
        if parent and parent.organization_id is not None:
            self.add_error("parent", "Parent must be a global category.")
        if parent and domain and parent.domain_id != domain.id:
            self.add_error("parent", "Parent and category must belong to the same domain.")
        if parent and self.instance.pk:
            descendants = self.instance.get_descendants_include_self()
            if parent.pk in descendants:
                self.add_error("parent", "A category cannot be its own ancestor.")
        return cleaned


def _global_domain_queryset():
    return Domain.objects.filter(organization__isnull=True).select_related("content_vertical").prefetch_related("categories")


def _global_category_queryset():
    return Category.objects.filter(organization__isnull=True).select_related("domain", "parent")


@staff_member_required
def admin_domain_list(request):
    query = (request.GET.get("q") or "").strip()
    domains = _global_domain_queryset()
    if query:
        domains = domains.filter(Q(name__icontains=query) | Q(slug__icontains=query))
    return render(request, "quiz/admin/classification/domain_list.html", {"domains": domains, "query": query})


@staff_member_required
def admin_domain_create(request):
    form = GlobalDomainForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        domain = form.save(commit=False)
        domain.organization = None
        domain.save()
        messages.success(request, "Global domain created successfully.")
        return redirect("quiz:admin_domain_list")
    return render(request, "quiz/admin/classification/domain_form.html", {"form": form, "page_title": "Add domain", "submit_label": "Create domain"})


@staff_member_required
def admin_domain_update(request, pk):
    domain = get_object_or_404(_global_domain_queryset(), pk=pk)
    form = GlobalDomainForm(request.POST or None, instance=domain)
    if request.method == "POST" and form.is_valid():
        domain = form.save(commit=False)
        domain.organization = None
        domain.save()
        messages.success(request, "Global domain updated successfully.")
        return redirect("quiz:admin_domain_list")
    return render(request, "quiz/admin/classification/domain_form.html", {"form": form, "page_title": "Edit domain", "submit_label": "Save changes", "domain": domain})


@staff_member_required
def admin_domain_toggle(request, pk):
    if request.method != "POST":
        raise Http404
    domain = get_object_or_404(_global_domain_queryset(), pk=pk)
    domain.is_active = not domain.is_active
    domain.save(update_fields=["is_active"])
    messages.success(request, f"Domain {'activated' if domain.is_active else 'deactivated'}.")
    return redirect("quiz:admin_domain_list")


@staff_member_required
def admin_domain_delete(request, pk):
    if request.method != "POST":
        raise Http404
    domain = get_object_or_404(_global_domain_queryset(), pk=pk)
    if domain.categories.exists():
        messages.error(request, "This domain cannot be deleted while it has categories. Deactivate it instead, or remove its categories first.")
    else:
        domain.delete()
        messages.success(request, "Global domain deleted.")
    return redirect("quiz:admin_domain_list")


@staff_member_required
def admin_category_list(request):
    query = (request.GET.get("q") or "").strip()
    domain_id = request.GET.get("domain") or ""
    categories = _global_category_queryset()
    if query:
        categories = categories.filter(Q(name__icontains=query) | Q(slug__icontains=query))
    if domain_id.isdigit():
        categories = categories.filter(domain_id=domain_id)
    domains = Domain.objects.filter(organization__isnull=True).order_by("name")
    return render(request, "quiz/admin/classification/category_list.html", {"categories": categories, "domains": domains, "query": query, "selected_domain": domain_id})


@staff_member_required
def admin_category_create(request):
    form = GlobalCategoryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        category = form.save(commit=False)
        category.organization = None
        category.save()
        messages.success(request, "Global category created successfully.")
        return redirect("quiz:admin_category_list")
    return render(request, "quiz/admin/classification/category_form.html", {"form": form, "page_title": "Add category", "submit_label": "Create category"})


@staff_member_required
def admin_category_update(request, pk):
    category = get_object_or_404(_global_category_queryset(), pk=pk)
    form = GlobalCategoryForm(request.POST or None, instance=category)
    if request.method == "POST" and form.is_valid():
        category = form.save(commit=False)
        category.organization = None
        category.save()
        messages.success(request, "Global category updated successfully.")
        return redirect("quiz:admin_category_list")
    return render(request, "quiz/admin/classification/category_form.html", {"form": form, "page_title": "Edit category", "submit_label": "Save changes", "category": category})


@staff_member_required
def admin_category_toggle(request, pk):
    if request.method != "POST":
        raise Http404
    category = get_object_or_404(_global_category_queryset(), pk=pk)
    category.is_active = not category.is_active
    category.save(update_fields=["is_active"])
    messages.success(request, f"Category {'activated' if category.is_active else 'deactivated'}.")
    return redirect("quiz:admin_category_list")


@staff_member_required
def admin_category_delete(request, pk):
    if request.method != "POST":
        raise Http404
    category = get_object_or_404(_global_category_queryset(), pk=pk)
    if category.children.exists() or category.primary_questions.exists() or category.questions.exists() or category.exams.exists() or category.exam_allocations.exists():
        messages.error(request, "This category cannot be deleted while it is referenced by child categories, questions, or exams. Deactivate it instead.")
    else:
        category.delete()
        messages.success(request, "Global category deleted.")
    return redirect("quiz:admin_category_list")
