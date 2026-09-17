from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.forms import inlineformset_factory
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from organizations.permissions import org_teacher_required
from organizations.models.role import OrganizationRole
from organizations.services.content_permissions import user_can_manage_owned_content
from quiz.models import Question, Choice, Category
from quiz.forms import QuestionForm


def _organization_question_form(*, organization, data=None, instance=None):
    """Build a question form restricted to categories owned by this organization."""
    form = QuestionForm(data=data, instance=instance, organization=organization)
    category_qs = Category.objects.filter(
        organization=organization,
        is_active=True,
    ).select_related("domain", "parent").order_by(
        "domain__name", "parent__name", "name"
    )
    form.fields["primary_category"].queryset = category_qs
    form.fields["categories"].queryset = category_qs
    return form


@org_teacher_required
def org_question_dashboard(request, slug):
    org = request.organization
    questions = Question.objects.filter(
        organization=org,
        is_deleted=False,
    ).order_by("-updated_at")
    if request.organization_member.role == OrganizationRole.STAFF:
        questions = questions.filter(created_by=request.user)
    return render(
        request,
        "organizations/admin/questions/dashboard.html",
        {"questions": questions, "org": org},
    )


ChoiceFormSet = inlineformset_factory(
    Question,
    Choice,
    fields=("text", "is_correct", "order"),
    extra=4,
    can_delete=True,
)


def _question_choice_formset(data=None, *, instance=None):
    """Keep choices optional when the submitted form contains no choice data."""
    prefix = "choices"
    if data is not None and f"{prefix}-TOTAL_FORMS" in data:
        has_choice_values = any(
            data.get(f"{prefix}-{index}-text", "").strip()
            or data.get(f"{prefix}-{index}-order", "").strip()
            or data.get(f"{prefix}-{index}-is_correct")
            for index in range(int(data.get(f"{prefix}-TOTAL_FORMS", 0) or 0))
        )
        if has_choice_values:
            return ChoiceFormSet(data, instance=instance, prefix=prefix), True
    return ChoiceFormSet(instance=instance, prefix=prefix), False


@org_teacher_required
def org_add_question(request, slug):
    org = request.organization
    if request.method == "POST":
        form = _organization_question_form(
            organization=org,
            data=request.POST,
        )
        formset, has_choice_payload = _question_choice_formset(request.POST)
        if form.is_valid() and (not has_choice_payload or formset.is_valid()):
            question = form.save(commit=False)
            question.organization = org
            question.created_by = request.user
            question.updated_by = request.user
            question.save()
            if has_choice_payload:
                formset.instance = question
                formset.save()
            return redirect("organizations_admin:questions", slug=slug)
    else:
        form = _organization_question_form(organization=org)
        formset, _ = _question_choice_formset()
    return render(
        request,
        "organizations/admin/questions/add.html",
        {"form": form, "choice_formset": formset, "org": org},
    )


def _ensure_question_mutation_access(request, question):
    if not user_can_manage_owned_content(request.user, request.organization, question):
        raise PermissionDenied("You can only modify questions you created.")


@org_teacher_required
def org_edit_question(request, slug, pk):
    org = request.organization
    question = get_object_or_404(
        Question,
        pk=pk,
        organization=org,
        is_deleted=False,
    )
    _ensure_question_mutation_access(request, question)
    if request.method == "POST":
        form = _organization_question_form(
            organization=org,
            data=request.POST,
            instance=question,
        )
        formset, has_choice_payload = _question_choice_formset(request.POST, instance=question)
        if form.is_valid() and (not has_choice_payload or formset.is_valid()):
            updated = form.save(commit=False)
            updated.updated_by = request.user
            updated.organization = org
            updated.save()
            if has_choice_payload:
                formset.save()
            return redirect("organizations_admin:questions", slug=slug)
    else:
        form = _organization_question_form(
            organization=org,
            instance=question,
        )
        formset, _ = _question_choice_formset(instance=question)
    return render(
        request,
        "organizations/admin/questions/edit.html",
        {"form": form, "choice_formset": formset, "question": question, "org": org},
    )


@require_POST
@org_teacher_required
def org_question_deactivate(request, slug, pk):
    org = request.organization
    question = get_object_or_404(Question, pk=pk, organization=org)
    _ensure_question_mutation_access(request, question)
    question.is_deleted = True
    question.save(update_fields=["is_deleted"])
    messages.success(request, "Question deactivated.")
    return redirect("organizations_admin:questions", slug=slug)


@require_POST
@org_teacher_required
def org_question_delete(request, slug, pk):
    org = request.organization
    question = get_object_or_404(Question, pk=pk, organization=org)
    _ensure_question_mutation_access(request, question)
    question.delete()
    messages.success(request, "Question deleted permanently.")
    return redirect("organizations_admin:questions", slug=slug)
