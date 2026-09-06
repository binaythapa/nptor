from django.contrib.auth.decorators import login_required
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render

from cv.forms import CareerProfileForm, CVBuilderForm, CVForm
from cv.forms_import import CVImportForm
from cv.models import CV, CVTemplate
from cv.models_ai import AIConversation, AIExtraction, AISuggestion, ATSAnalysis
from cv.services.ai.career_interviewer import confirm_interview_extraction, interview_turn
from cv.services.ai.provider import AIProviderNotConfigured
from cv.services.cv_ai import AIProviderError, accept_suggestion, analyze_ats, reject_suggestion, review_cv, tailor_cv
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
        conversation = AIConversation.objects.create(owner=request.user, purpose=AIConversation.PURPOSE_INTERVIEW)
    else:
        conversation = get_object_or_404(AIConversation, pk=conversation_id, owner=request.user, purpose=AIConversation.PURPOSE_INTERVIEW)

    error_message = None
    if request.method == "POST":
        try:
            interview_turn(conversation, request.POST.get("message", ""))
        except (AIProviderNotConfigured, AIProviderError, ValueError) as exc:
            error_message = str(exc)
        else:
            return redirect("cv:career_interview_conversation", conversation_id=conversation.pk)

    return render(request, "cv/career_interview.html", {"conversation": conversation, "messages": conversation.messages.all(), "extractions": conversation.extractions.all(), "error_message": error_message})


@login_required
def career_interview_confirm(request, pk):
    extraction = get_object_or_404(AIExtraction, pk=pk, conversation__owner=request.user, conversation__purpose=AIConversation.PURPOSE_INTERVIEW)
    if request.method == "POST":
        try:
            confirm_interview_extraction(extraction.pk, request.user, request.POST.get("value", ""))
        except ValueError as exc:
            return render(request, "cv/career_interview.html", {"conversation": extraction.conversation, "messages": extraction.conversation.messages.all(), "extractions": extraction.conversation.extractions.all(), "error_message": str(exc)})
    return redirect("cv:career_interview_conversation", conversation_id=extraction.conversation_id)


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