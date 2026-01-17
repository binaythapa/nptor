from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.utils import timezone

from quiz.models import Question
from quiz.forms import QuestionForm


def staff_required(user):
    return user.is_staff


from django.db.models import Count, Q
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage

from quiz.models import Question, QuestionDiscussion

from django.db.models import Count, Q, Max
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required

from quiz.models import Question, QuestionDiscussion
@staff_member_required
def question_dashboard(request):

    # ================= BASE QUERY =================
    questions = (
        Question.objects
        .filter(is_deleted=False)
        .order_by('-updated_at')
    )

    # ================= ACTIONS (POST) =================
    if request.method == "POST":

        # Deactivate
        if "disable_question" in request.POST:
            qid = request.POST.get("disable_question")
            Question.objects.filter(id=qid).update(is_active=False)
            return redirect(request.path + "?" + request.META.get("QUERY_STRING", ""))

        # Activate
        if "enable_question" in request.POST:
            qid = request.POST.get("enable_question")
            Question.objects.filter(id=qid).update(is_active=True)
            return redirect(request.path + "?" + request.META.get("QUERY_STRING", ""))

        # Delete (soft delete)
        if "delete_question" in request.POST:
            if not request.user.is_superuser:
                return HttpResponseForbidden("Not allowed")

            qid = request.POST.get("delete_question")
            Question.objects.filter(id=qid).update(
                is_deleted=True,
                deleted_by=request.user,
                deleted_at=timezone.now()
            )
            return redirect(request.path + "?" + request.META.get("QUERY_STRING", ""))

    # ================= FILTERS (GET) =================
    search = request.GET.get('q', '')
    if search:
        questions = questions.filter(text__icontains=search)

    category = request.GET.get('category', '')
    if category:
        questions = questions.filter(category=category)

    difficulty = request.GET.get('difficulty', '')
    if difficulty:
        questions = questions.filter(difficulty=difficulty)

    status = request.GET.get('status', '')
    if status == "active":
        questions = questions.filter(is_active=True)
    elif status == "disabled":
        questions = questions.filter(is_active=False)

    only_flagged = request.GET.get('flagged') == "1"
    if only_flagged:
        questions = questions.filter(
            discussions__is_answer_incorrect=True,
            discussions__is_deleted=False
        ).distinct()

    # ================= ANNOTATIONS =================
    questions = questions.annotate(
        discussion_count=Count(
            'discussions',
            filter=Q(discussions__is_deleted=False)
        ),
        flag_count=Count(
            'discussions',
            filter=Q(
                discussions__is_answer_incorrect=True,
                discussions__is_deleted=False
            )
        ),
        latest_comment=Max(
            'discussions__created_at',
            filter=Q(discussions__is_deleted=False)
        )
    )

    # ================= STATS =================
    total_questions = Question.objects.filter(is_deleted=False).count()
    active_questions = Question.objects.filter(
        is_active=True, is_deleted=False
    ).count()
    disabled_questions = Question.objects.filter(
        is_active=False, is_deleted=False
    ).count()
    flagged_questions = Question.objects.filter(
        discussions__is_answer_incorrect=True,
        discussions__is_deleted=False,
        is_deleted=False
    ).distinct().count()

    categories = (
        Question.objects
        .filter(is_deleted=False)
        .values_list('category', flat=True)
        .distinct()
        .order_by('category')
    )

    # ================= PAGINATION =================
    paginator = Paginator(questions, 20)
    page = request.GET.get('page')

    try:
        questions = paginator.page(page)
    except PageNotAnInteger:
        questions = paginator.page(1)
    except EmptyPage:
        questions = paginator.page(paginator.num_pages)

    context = {
        "questions": questions,
        "search": search,
        "selected_category": category,
        "selected_difficulty": difficulty,
        "selected_status": status,
        "categories": categories,
        "only_flagged": only_flagged,

        "total_questions": total_questions,
        "active_questions": active_questions,
        "flagged_questions": flagged_questions,
        "disabled_questions": disabled_questions,
    }

    return render(request, "questions/dashboard.html", context)




# views/questions.py

from django.forms import inlineformset_factory
from django.shortcuts import render, redirect
from quiz.models import Question, Choice
from quiz.forms import QuestionForm

ChoiceFormSet = inlineformset_factory(
    Question,
    Choice,
    fields=("text", "is_correct", "order"),
    extra=6,          # 👈 shows 5 empty rows
    can_delete=True,
)

def add_question(request):
    if request.method == "POST":
        form = QuestionForm(request.POST)
        formset = ChoiceFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            question = form.save(commit=False)
            question.created_by = request.user
            question.updated_by = request.user
            question.save()

            formset.instance = question
            formset.save()

            return redirect("quiz:question_dashboard")
    else:
        form = QuestionForm()
        formset = ChoiceFormSet()

    return render(
        request,
        "questions/add_question.html",
        {
            "form": form,
            "choice_formset": formset,
        }
    )



@login_required
@user_passes_test(staff_required)
def edit_question(request, pk):
    question = get_object_or_404(Question, pk=pk, is_deleted=False)

    if request.method == "POST":
        form = QuestionForm(request.POST, instance=question)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.updated_by = request.user
            obj.save()
            return redirect("quiz:question_dashboard")
    else:
        form = QuestionForm(instance=question)

    return render(
        request,
        "questions/edit_question.html",
        {"form": form, "question": question}
    )


@login_required
def delete_question(request, pk):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Not allowed")

    question = get_object_or_404(Question, pk=pk, is_deleted=False)

    question.is_deleted = True
    question.deleted_by = request.user
    question.deleted_at = timezone.now()
    question.save()

    return redirect("quiz:question_dashboard")
