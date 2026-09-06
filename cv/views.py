from django.contrib.auth.decorators import login_required
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render

from cv.forms import CareerProfileForm, CVBuilderForm, CVForm
from cv.forms_import import CVImportForm
from cv.models import CV, CVTemplate
from cv.models_ai import AIConversation, AIExtraction, AISuggestion, ATSAnalysis
from cv.services.ai.career_interviewer import confirm_interview_extraction, interview_turn
from cv.services.ai.provider import AIProviderError
from cv.services.cv_ai import accept_suggestion, analyze_ats, reject_suggestion, review_cv, tailor_cv
from cv.services.cv_builder import build_cv_payload, create_cv, create_cv_version, duplicate_cv
from cv.services.documents.docx import generate_docx
from cv.services.documents.pdf import generate_pdf
from cv.services.importers.service import confirm_import_field, import_cv_source
from cv.services.profile import account_contact_defaults, get_or_create_career_profile


BUILDER_SECTIONS = (
    ("experiences", "Work Experience", "careerexperience_records"),
    ("educations", "Education", "careereducation_records"),
    ("skills", "Skills", "careerskill_records"),
    ("certifications", "Certifications", "careercertification_records"),
    ("projects", "Projects", "careerproject_records"),
    ("achievements", "Achievements", "careerachievement_records"),
)


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
def career_interview(request, conversation_id=None):
    get_or_create_career_profile(request.user)
    if conversation_id is None:
        conversation = AIConversation.objects.create(
            owner=request.user,
            purpose=AIConversation.PURPOSE_INTERVIEW,
        )
    else:
        conversation = get_object_or_404(
            AIConversation,
            pk=conversation_id,
            owner=request.user,
            purpose=AIConversation.PURPOSE_INTERVIEW,
        )

    error_message = None
    if request.method == "POST":
        try:
            interview_turn(conversation, request.POST.get("message", ""))
        except (AIProviderError, ValueError) as exc:
            error_message = str(exc)
        else:
            return redirect("cv:career_interview", conversation_id=conversation.pk)

    messages = conversation.messages.all()
    extractions = conversation.extractions.select_related("confirmed_by").all()
    return render(
        request,
        "cv/career_interview.html",
        {
            "conversation": conversation,
            "messages": messages,
            "extractions": extractions,
            "error_message": error_message,
        },
    )


@login_required
def career_interview_confirm(request, pk):
    extraction = get_object_or_404(
        AIExtraction,
        pk=pk,
        conversation__owner=request.user,
        conversation__purpose=AIConversation.PURPOSE_INTERVIEW,
    )
    if request.method == "POST":
        try:
            confirm_interview_extraction(extraction.pk, request.user, request.POST.get("value", ""))
        except ValueError as exc:
            return render(request, "cv/career_interview.html", {"conversation": extraction.conversation, "messages": extraction.conversation.messages.all(), "extractions": extraction.conversation.extractions.all(), "error_message": str(exc)})
    return redirect("cv:career_interview", conversation_id=extraction.conversation_id)


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
                return redirect("cv:cv_builder", pk=cv.pk)
    else: form = CVForm(owner=request.user, initial={"status": CV.STATUS_DRAFT})
    return render(request, "cv/cv_form.html", {"form": form, "heading": "Create CV"})


@login_required
def cv_edit(request, pk):
    cv = get_object_or_404(CV, pk=pk, owner=request.user)
    return redirect("cv:cv_builder", pk=cv.pk)


@login_required
def cv_builder(request, pk):
    cv = get_object_or_404(CV.objects.select_related("profile", "template"), pk=pk, owner=request.user)
    profile = cv.profile
    if request.method == "POST":
        form = CVBuilderForm(request.POST, instance=cv)
        if form.is_valid():
            cv.title = form.cleaned_data["title"]
            cv.template = form.cleaned_data["template"]
            cv.status = form.cleaned_data["status"]
            cv.overrides = {"professional_title": form.cleaned_data["professional_title"], "summary": form.cleaned_data["summary"], "linkedin_url": form.cleaned_data["linkedin_url"], "portfolio_url": form.cleaned_data["portfolio_url"]}
            selected_sections = {}
            for key, _label, related_name in BUILDER_SECTIONS:
                valid_ids = set(getattr(profile, related_name).values_list("id", flat=True))
                selected_sections[key] = [int(value) for value in request.POST.getlist(key) if value.isdigit() and int(value) in valid_ids]
            cv.selected_sections = selected_sections
            cv.save(update_fields=["title", "template", "status", "overrides", "selected_sections", "updated_at"])
            return redirect("cv:cv_builder", pk=cv.pk)
    else:
        form = CVBuilderForm(instance=cv)
    sections = []
    for key, label, related_name in BUILDER_SECTIONS:
        records = list(getattr(profile, related_name).all())
        selected = cv.selected_sections.get(key) if cv.selected_sections else None
        selected_ids = {int(value) for value in selected} if selected is not None else {record.id for record in records}
        sections.append({"key": key, "label": label, "records": records, "selected_ids": selected_ids})
    return render(request, "cv/builder.html", {"cv": cv, "form": form, "contact": account_contact_defaults(request.user), "sections": sections, "payload": build_cv_payload(cv)})


@login_required
def cv_duplicate(request, pk):
    cv = get_object_or_404(CV, pk=pk, owner=request.user)
    return redirect("cv:cv_builder", pk=duplicate_cv(cv).pk)


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
def cv_ai_review(request, pk):
    cv = get_object_or_404(CV, pk=pk, owner=request.user)
    error_message = None
    if request.method == "POST":
        try:
            review_cv(cv)
        except AIProviderError as exc:
            error_message = str(exc)
        else:
            return redirect("cv:cv_ai_review", pk=cv.pk)
    conversation = cv.ai_conversations.filter(purpose=AIConversation.PURPOSE_REVIEW).prefetch_related("suggestions").first()
    return render(request, "cv/ai_review.html", {"cv": cv, "conversation": conversation, "error_message": error_message})


@login_required
def cv_ats_analysis(request, pk):
    cv = get_object_or_404(CV, pk=pk, owner=request.user)
    error_message = None
    job_description = ""
    if request.method == "POST":
        job_description = request.POST.get("job_description", "")
        try:
            analyze_ats(cv, job_description)
        except (AIProviderError, ValueError) as exc:
            error_message = str(exc)
        else:
            return redirect("cv:cv_ats_analysis", pk=cv.pk)
    analysis = ATSAnalysis.objects.filter(owner=request.user, cv_version__cv=cv).select_related("cv_version").first()
    return render(request, "cv/ats_analysis.html", {"cv": cv, "analysis": analysis, "job_description": job_description or (analysis.job_description if analysis else ""), "error_message": error_message})


@login_required
def cv_ai_tailor(request, pk):
    cv = get_object_or_404(CV, pk=pk, owner=request.user)
    error_message = None
    job_description = ""
    if request.method == "POST":
        job_description = request.POST.get("job_description", "")
        try:
            tailor_cv(cv, job_description)
        except (AIProviderError, ValueError) as exc:
            error_message = str(exc)
        else:
            return redirect("cv:cv_ai_tailor", pk=cv.pk)
    conversation = cv.ai_conversations.filter(purpose=AIConversation.PURPOSE_JOB_MATCH, metadata__analysis="tailoring").prefetch_related("suggestions").first()
    return render(request, "cv/ai_tailor.html", {"cv": cv, "conversation": conversation, "job_description": job_description or (conversation.metadata.get("job_description", "") if conversation else ""), "error_message": error_message})


@login_required
def cv_ai_suggestion_accept(request, pk):
    suggestion = get_object_or_404(AISuggestion.objects.select_related("conversation", "conversation__cv"), pk=pk, conversation__owner=request.user)
    if request.method == "POST":
        try: accept_suggestion(suggestion, request.user)
        except ValueError: pass
    target = "cv:cv_ai_tailor" if suggestion.conversation.metadata.get("analysis") == "tailoring" else "cv:cv_ai_review"
    return redirect(target, pk=suggestion.conversation.cv_id)


@login_required
def cv_ai_suggestion_reject(request, pk):
    suggestion = get_object_or_404(AISuggestion.objects.select_related("conversation", "conversation__cv"), pk=pk, conversation__owner=request.user)
    if request.method == "POST": reject_suggestion(suggestion, request.user)
    target = "cv:cv_ai_tailor" if suggestion.conversation.metadata.get("analysis") == "tailoring" else "cv:cv_ai_review"
    return redirect(target, pk=suggestion.conversation.cv_id)


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
