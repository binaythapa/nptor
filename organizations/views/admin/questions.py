from organizations.permissions import org_admin_required
from quiz.models import Question
from django.shortcuts import render
from quiz.forms import QuestionForm
from organizations.permissions import org_admin_required
from quiz.models import Question
from django.shortcuts import render
from django.shortcuts import render, redirect, get_object_or_404


@org_admin_required
def org_question_dashboard(request, slug):

    org = request.organization

    questions = Question.objects.filter(
        organization=org,
        is_deleted=False
    ).order_by("-updated_at")

    return render(
        request,
        "organizations/admin/questions/dashboard.html",
        {
            "questions": questions,
            "org": org,
        }
    )
from django.shortcuts import render, redirect
from django.forms import inlineformset_factory

from organizations.permissions import org_admin_required

from quiz.models import Question, Choice
from quiz.forms import QuestionForm


# Formset for choices
ChoiceFormSet = inlineformset_factory(
    Question,
    Choice,
    fields=("text", "is_correct", "order"),
    extra=4,
    can_delete=True,
)


@org_admin_required
def org_add_question(request, slug):

    org = request.organization

    if request.method == "POST":

        form = QuestionForm(request.POST)

        formset = ChoiceFormSet(
            request.POST,
            prefix="choices"
        )

        if form.is_valid() and formset.is_valid():

            # Save question
            question = form.save(commit=False)

            question.organization = org
            question.created_by = request.user
            question.updated_by = request.user

            question.save()

            # Save choices
            formset.instance = question
            formset.save()

            return redirect(
                "organizations_admin:questions",
                slug=slug
            )

    else:

        form = QuestionForm()

        formset = ChoiceFormSet(prefix="choices")

    return render(
        request,
        "organizations/admin/questions/add.html",
        {
            "form": form,
            "choice_formset": formset,
            "org": org,
        }
    )








@org_admin_required
def org_edit_question(request, slug, pk):

    org = request.organization

    question = get_object_or_404(
        Question,
        pk=pk,
        organization=org,
        is_deleted=False
    )

    if request.method == "POST":

        form = QuestionForm(request.POST, instance=question)

        formset = ChoiceFormSet(
            request.POST,
            instance=question,
            prefix="choices"
        )

        if form.is_valid() and formset.is_valid():

            updated = form.save(commit=False)
            updated.updated_by = request.user
            updated.save()

            formset.save()

            return redirect(
                "organizations_admin:questions",
                slug=slug
            )

    else:

        form = QuestionForm(instance=question)

        formset = ChoiceFormSet(
            instance=question,
            prefix="choices"
        )

    return render(
        request,
        "organizations/admin/questions/edit.html",
        {
            "form": form,
            "choice_formset": formset,
            "question": question,
        }
    )


@org_admin_required
def org_question_deactivate(request, slug, pk):

    org = request.organization

    question = get_object_or_404(
        Question,
        pk=pk,
        organization=org
    )

    question.is_deleted = True
    question.save(update_fields=["is_deleted"])

    messages.success(request, "Question deactivated.")

    return redirect("organizations_admin:questions", slug=slug)


@org_admin_required
def org_question_delete(request, slug, pk):

    org = request.organization

    question = get_object_or_404(
        Question,
        pk=pk,
        organization=org
    )

    question.delete()

    messages.success(request, "Question deleted permanently.")

    return redirect("organizations_admin:questions", slug=slug)