import json

import requests
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from cv.forms import CAREER_RECORD_FORMS, CareerProfileForm, CVBuilderForm, CVForm
from cv.forms_import import CVImportForm
from cv.models import CV, CVTemplate
from cv.models_ai import AIConversation, AIExtraction, AISuggestion, ATSAnalysis
from cv.services.ai.career_interviewer import confirm_interview_extraction, interview_turn
from cv.services.ai.cv_writer import rewrite_bullet, suggest_skills, suggest_summary
from cv.services.ai.provider import AIProviderNotConfigured
from cv.services.cv_ai import AIProviderError, accept_suggestion, analyze_ats, reject_suggestion, review_cv, tailor_cv
from cv.services.cv_builder import build_cv_payload, create_cv, create_cv_version, duplicate_cv
from cv.services.cv_workspace import builder_ai_context, save_builder_state
from cv.services.documents.docx import generate_docx
from cv.services.documents.pdf import generate_pdf
from cv.services.documents.renderer import build_cv_render_context, get_render_config, get_template_snapshot
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


def _career_record_config(section):
    try:
        return CAREER_RECORD_FORMS[section]
    except KeyError:
        raise Http404("Unknown career profile section.")


def _career_record_queryset(model, user):
    return model.objects.filter(profile__user=user)


def _json_request(request):
    try:
        value = json.loads(request.body.decode("utf-8") or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Request body must contain valid JSON.") from exc
    if not isinstance(value, dict):
        raise ValueError("Request body must be a JSON object.")
    return value


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
    sections = []
    for section, (_model, _form_class, label) in CAREER_RECORD_FORMS.items():
        records = _model.objects.filter(profile=career_profile)
        sections.append({"key": section, "label": label, "records": records, "count": records.count()})
    return render(request, "cv/profile.html", {"form": form, "contact": account_contact_defaults(request.user), "profile": career_profile, "sections": sections})


@login_required
def profile_record_add(request, section):
    model, form_class, label = _career_record_config(section)
    if request.method == "POST":
        form = form_class(request.POST)
        if form.is_valid():
            record = form.save(commit=False)
            record.profile = get_or_create_career_profile(request.user)
            record.source = "user"
            record.is_confirmed = True
            record.save()
            return redirect("cv:profile")
    else:
        form = form_class()
    return render(request, "cv/career_record_form.html", {"form": form, "heading": f"Add {label}", "section": section})


@login_required
def profile_record_edit(request, section, pk):
    model, form_class, label = _career_record_config(section)
    record = get_object_or_404(_career_record_queryset(model, request.user), pk=pk)
    if request.method == "POST":
        form = form_class(request.POST, instance=record)
        if form.is_valid():
            form.save()
            return redirect("cv:profile")
    else:
        form = form_class(instance=record)
    return render(request, "cv/career_record_form.html", {"form": form, "heading": f"Edit {label}", "section": section, "record": record})


@login_required
def profile_record_delete(request, section, pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    model, _form_class, _label = _career_record_config(section)
    record = get_object_or_404(_career_record_queryset(model, request.user), pk=pk)
    record.delete()
    return redirect("cv:profile")


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
            if template is None:
                form.add_error("template", "No active CV template is available.")
            else:
                cv = create_cv(request.user, form.cleaned_data["title"], template)
                cv.status = form.cleaned_data["status"]
                cv.overrides = {}
                cv.save(update_fields=["status", "overrides", "updated_at"])
                return redirect("cv:cv_builder", pk=cv.pk)
    else:
        form = CVForm(owner=request.user, initial={"status": CV.STATUS_DRAFT})
        template_slug = request.GET.get("template")
        if template_slug:
            selected_template = CVTemplate.objects.filter(slug=template_slug, is_active=True).first()
            if selected_template:
                form.initial["template"] = selected_template
    return render(request, "cv/cv_form.html", {"form": form, "heading": "Create your resume"})


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
            cv.overrides = {
                "professional_title": form.cleaned_data["professional_title"],
                "summary": form.cleaned_data["summary"],
                "linkedin_url": form.cleaned_data["linkedin_url"],
                "portfolio_url": form.cleaned_data["portfolio_url"],
                "target_job": (cv.overrides or {}).get("target_job", {}),
            }
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
    payload = build_cv_payload(cv)
    return render(request, "cv/builder.html", {
        "cv": cv,
        "form": form,
        "contact": account_contact_defaults(request.user),
        "sections": sections,
        "payload": payload,
        "target_job": payload.get("target_job", {}),
    })


@login_required
def cv_builder_autosave(request, pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    cv = get_object_or_404(CV, pk=pk, owner=request.user)
    try:
        save_builder_state(cv, _json_request(request))
    except ValueError as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)
    return JsonResponse({"ok": True, "updated_at": cv.updated_at.isoformat()})


@login_required
def cv_builder_ai(request, pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    cv = get_object_or_404(CV.objects.select_related("profile", "template"), pk=pk, owner=request.user)
    try:
        data = _json_request(request)
        action = str(data.get("action", "")).strip().lower()
        payload, target_job = builder_ai_context(cv)
        if action == "summary":
            suggestion = suggest_summary(payload)
        elif action == "bullet":
            text = str(data.get("text", "")).strip()
            if not text:
                raise ValueError("Enter an experience bullet or description first.")
            suggestion = rewrite_bullet(text, {
                "target_job": target_job,
                "section": data.get("section", "experience"),
            })
        elif action == "skills":
            suggestion = suggest_skills(payload, target_job.get("title", ""))
        else:
            raise ValueError("Unsupported AI builder action.")
    except (AIProviderNotConfigured, AIProviderError, ValueError, requests.RequestException, TypeError) as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)
    return JsonResponse({"ok": True, "suggestion": suggestion})
