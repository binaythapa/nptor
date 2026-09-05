from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from cv.forms import CareerProfileForm, CVForm
from cv.models import CV, CVTemplate
from cv.services.cv_builder import build_cv_payload, create_cv, duplicate_cv
from cv.services.profile import account_contact_defaults, get_or_create_career_profile


@login_required
def dashboard(request):
    profile = get_or_create_career_profile(request.user)
    cvs = CV.objects.filter(owner=request.user).select_related("template")
    return render(request, "cv/dashboard.html", {
        "profile": profile,
        "cvs": cvs,
        "contact": account_contact_defaults(request.user),
    })


@login_required
def profile(request):
    career_profile = get_or_create_career_profile(request.user)
    if request.method == "POST":
        form = CareerProfileForm(request.POST, instance=career_profile)
        if form.is_valid():
            form.save()
            return redirect("cv:profile")
    else:
        form = CareerProfileForm(instance=career_profile)
    return render(request, "cv/profile.html", {
        "form": form,
        "contact": account_contact_defaults(request.user),
        "profile": career_profile,
    })


@login_required
def cv_create(request):
    if request.method == "POST":
        form = CVForm(request.POST, owner=request.user)
        if form.is_valid():
            template = form.cleaned_data.get("template") or CVTemplate.objects.filter(is_active=True).first()
            if template is None:
                form.add_error("template", "No active CV template is available.")
            else:
                cv = create_cv(request.user, form.cleaned_data["title"], template)
                cv.status = form.cleaned_data["status"]
                cv.overrides = form.cleaned_data.get("overrides") or {}
                cv.save(update_fields=["status", "overrides", "updated_at"])
                return redirect("cv:cv_edit", pk=cv.pk)
    else:
        form = CVForm(owner=request.user, initial={"status": CV.STATUS_DRAFT})
    return render(request, "cv/cv_form.html", {"form": form, "heading": "Create CV"})


@login_required
def cv_edit(request, pk):
    cv = get_object_or_404(CV, pk=pk, owner=request.user)
    if request.method == "POST":
        form = CVForm(request.POST, instance=cv, owner=request.user)
        if form.is_valid():
            form.save()
            return redirect("cv:cv_edit", pk=cv.pk)
    else:
        form = CVForm(instance=cv, owner=request.user)
    return render(request, "cv/cv_form.html", {"form": form, "cv": cv, "heading": "Edit CV"})


@login_required
def cv_duplicate(request, pk):
    cv = get_object_or_404(CV, pk=pk, owner=request.user)
    copy = duplicate_cv(cv)
    return redirect("cv:cv_edit", pk=copy.pk)


@login_required
def cv_templates(request):
    templates = CVTemplate.objects.filter(is_active=True).order_by("name")
    return render(request, "cv/template_select.html", {"templates": templates})


@login_required
def cv_preview(request, pk):
    cv = get_object_or_404(CV, pk=pk, owner=request.user)
    return render(request, "cv/preview.html", {"cv": cv, "payload": build_cv_payload(cv)})


@login_required
def cv_versions(request, pk):
    cv = get_object_or_404(CV, pk=pk, owner=request.user)
    versions = cv.versions.order_by("-version_number")
    return render(request, "cv/versions.html", {"cv": cv, "versions": versions})
