from django.contrib.auth.decorators import login_required
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render

from cv.forms import CareerProfileForm, CVForm
from cv.forms_import import CVImportForm
from cv.models import CV, CVTemplate
from cv.services.cv_builder import build_cv_payload, create_cv, create_cv_version, duplicate_cv
from cv.services.documents.docx import generate_docx
from cv.services.documents.pdf import generate_pdf
from cv.services.importers.service import confirm_import_field, import_cv_source
from cv.services.profile import account_contact_defaults, get_or_create_career_profile


@login_required
def dashboard(request):
    profile = get_or_create_career_profile(request.user)
    cvs = CV.objects.filter(owner=request.user).select_related("template")
    return render(request, "cv/dashboard.html", {"profile": profile, "cvs": cvs, "contact": account_contact_defaults(request.user)})


@login_required
def profile(request):
    career_profile = get_or_create_career_profile(request.user)
    if request.method == "POST":
        form = CareerProfileForm(request.POST, instance=career_profile)
        if form.is_valid(): form.save(); return redirect("cv:profile")
    else: form = CareerProfileForm(instance=career_profile)
    return render(request, "cv/profile.html", {"form": form, "contact": account_contact_defaults(request.user), "profile": career_profile})


@login_required
def cv_create(request):
    if request.method == "POST":
        form = CVForm(request.POST, owner=request.user)
        if form.is_valid():
            template = form.cleaned_data.get("template") or CVTemplate.objects.filter(is_active=True).first()
            if template is None: form.add_error("template", "No active CV template is available.")
            else:
                cv = create_cv(request.user, form.cleaned_data["title"], template)
                cv.status = form.cleaned_data["status"]
                cv.overrides = form.cleaned_data.get("overrides") or {}
                cv.save(update_fields=["status", "overrides", "updated_at"])
                return redirect("cv:cv_edit", pk=cv.pk)
    else: form = CVForm(owner=request.user, initial={"status": CV.STATUS_DRAFT})
    return render(request, "cv/cv_form.html", {"form": form, "heading": "Create CV"})


@login_required
def cv_edit(request, pk):
    cv = get_object_or_404(CV, pk=pk, owner=request.user)
    if request.method == "POST":
        form = CVForm(request.POST, instance=cv, owner=request.user)
        if form.is_valid(): form.save(); return redirect("cv:cv_edit", pk=cv.pk)
    else: form = CVForm(instance=cv, owner=request.user)
    return render(request, "cv/cv_form.html", {"form": form, "cv": cv, "heading": "Edit CV"})


@login_required
def cv_duplicate(request, pk):
    cv = get_object_or_404(CV, pk=pk, owner=request.user)
    return redirect("cv:cv_edit", pk=duplicate_cv(cv).pk)


@login_required
def cv_templates(request):
    return render(request, "cv/template_select.html", {"templates": CVTemplate.objects.filter(is_active=True).order_by("name")})


@login_required
def cv_preview(request, pk):
    cv = get_object_or_404(CV, pk=pk, owner=request.user)
    return render(request, "cv/preview.html", {"cv": cv, "payload": build_cv_payload(cv)})


@login_required
def cv_versions(request, pk):
    cv = get_object_or_404(CV, pk=pk, owner=request.user)
    return render(request, "cv/versions.html", {"cv": cv, "versions": cv.versions.order_by("-version_number")})


@login_required
def cv_import(request):
    if request.method == "POST":
        form = CVImportForm(request.POST, request.FILES)
        if form.is_valid():
            try: imported = import_cv_source(request.user, form.cleaned_data["source_file"])
            except ValueError as exc: form.add_error("source_file", str(exc))
            else: return redirect("cv:cv_import_review", pk=imported.pk)
    else: form = CVImportForm()
    return render(request, "cv/import.html", {"form": form})


@login_required
def cv_import_review(request, pk):
    imported = get_object_or_404(request.user.cv_imports.prefetch_related("fields"), pk=pk)
    if request.method == "POST":
        for field in imported.fields.all():
            value = request.POST.get(f"field_{field.pk}")
            if value is not None: confirm_import_field(field.pk, request.user, value)
        return redirect("cv:cv_import_review", pk=pk)
    return render(request, "cv/import_review.html", {"imported": imported})


def _download_artifact(artifact):
    return FileResponse(artifact.file.open("rb"), as_attachment=True, filename=artifact.file.name.rsplit("/", 1)[-1], content_type=artifact.mime_type)


@login_required
def cv_export_pdf(request, pk):
    cv = get_object_or_404(CV, pk=pk, owner=request.user)
    return _download_artifact(generate_pdf(create_cv_version(cv)))


@login_required
def cv_export_docx(request, pk):
    cv = get_object_or_404(CV, pk=pk, owner=request.user)
    return _download_artifact(generate_docx(create_cv_version(cv)))
