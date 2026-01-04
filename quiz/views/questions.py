from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.utils import timezone

from quiz.models import Question
from quiz.forms import QuestionForm


def staff_required(user):
    return user.is_staff


from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Q
from django.shortcuts import render
from quiz.models import Question

def question_dashboard(request):
    questions = Question.objects.all().order_by('-updated_at')
    
    # Add filters
    search = request.GET.get('q', '')
    if search:
        questions = questions.filter(
            Q(text__icontains=search) | 
            Q(category__icontains=search)
        )
    
    category = request.GET.get('category', '')
    if category:
        questions = questions.filter(category=category)
    
    difficulty = request.GET.get('difficulty', '')
    if difficulty:
        questions = questions.filter(difficulty=difficulty)
    
    # Get unique categories for filter dropdown
    categories = Question.objects.values_list('category', flat=True).distinct().order_by('category')
    
    # Statistics
    total_questions = Question.objects.count()
    active_questions = Question.objects.filter(is_active=True).count()
    mcq_count = Question.objects.filter(question_type='MCQ').count()
    tf_count = Question.objects.filter(question_type='TF').count()
    
    # Pagination
    paginator = Paginator(questions, 20)  # 20 per page
    page = request.GET.get('page')
    try:
        questions = paginator.page(page)
    except PageNotAnInteger:
        questions = paginator.page(1)
    except EmptyPage:
        questions = paginator.page(paginator.num_pages)
    
    context = {
        'questions': questions,
        'search': search,
        'selected_category': category,
        'selected_difficulty': difficulty,
        'categories': categories,
        'total_questions': total_questions,
        'active_questions': active_questions,
        'mcq_count': mcq_count,
        'tf_count': tf_count,
    }
    
    return render(request, 'questions/dashboard.html', context)

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
