# quiz/views.py
import math
import random
from .models import *
from .forms import *
from django.core.mail import send_mail
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import login, get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.utils.dateformat import DateFormat
from django.utils.formats import get_format
from django.contrib import messages
from .forms import RegistrationForm
from django.db import IntegrityError
# quiz/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib import messages
from .forms import RegistrationForm, EmailOrUsernameLoginForm
from django.views.generic import TemplateView, CreateView, DetailView, UpdateView
from django.urls import reverse_lazy

import logging
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from .models import UserExam, UserAnswer, Choice  # adjust import path if needed

logger = logging.getLogger(__name__)
import logging
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages

from .models import UserExam, QuestionFeedback  # adjust import paths
from .models import UserExam, UserAnswer, Choice  # adjust import path if needed
from django.db.models import Q

from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied
from django.db.models import Avg, Q
from django.shortcuts import render

from .models import Exam, UserExam
from django.contrib.auth.models import User


from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.db.models import Avg, Q, Count
from django.shortcuts import render

from .models import Exam, UserExam, Category, Question

logger = logging.getLogger(__name__)

# quiz/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib import messages
from .forms import RegistrationForm

from django.contrib.auth import authenticate, login
# quiz/views.py  ← REPLACE YOUR ENTIRE register() FUNCTION WITH THIS

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, authenticate
from .forms import RegistrationForm
from .utils import get_leaf_category_name
from django.http import JsonResponse, HttpResponseBadRequest
from django.db import transaction
from django.shortcuts import get_object_or_404

# Models (import before helpers that reference them)
from .models import (
    Exam, Question, Choice, UserExam, UserAnswer,
    Category, ExamCategoryAllocation, Notification
)

User = get_user_model()

# at top of quiz/views.py (add these imports)
from django.contrib.auth.views import (
    LoginView, LogoutView,
    PasswordResetView, PasswordResetDoneView,
    PasswordResetConfirmView, PasswordResetCompleteView
)
import random
from django.shortcuts import render
from .models import Question, Choice

from django.shortcuts import render
from .models import Question, Choice, Category

from django.shortcuts import render
from .models import Question, Choice, Category




from django.shortcuts import render, redirect
from .models import Question, Choice, Category

from django.shortcuts import render, redirect
from .models import Question, Choice, Category

import random
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from .models import Question, Choice, Category, PracticeStat


# =====================================================
# BASIC PRACTICE
# =====================================================
from django.shortcuts import render, redirect
from django.conf import settings
from .models import Question, Choice, Domain, Category

def practice(request):
    """
    BASIC PRACTICE (PUBLIC)
    - Supports SINGLE / MULTI / TRUE-FALSE
    - Domain → Category → Difficulty filters
    - Anonymous limit from settings.py
    - Correct / Wrong feedback
    """

    # =====================================================
    # RESET
    # =====================================================
    if request.GET.get("reset") == "1":
        for k in [
            "p_seen", "p_qid", "p_filters",
            "p_total", "p_anon_count"
        ]:
            request.session.pop(k, None)
        return redirect("quiz:practice")

    # =====================================================
    # READ FILTERS
    # =====================================================
    domain_id = request.POST.get("domain") or request.GET.get("domain")
    category_id = request.POST.get("category") or request.GET.get("category")
    difficulty = request.POST.get("difficulty") or request.GET.get("difficulty")

    filters = {
        "domain": domain_id,
        "category": category_id,
        "difficulty": difficulty,
    }

    last_filters = request.session.get("p_filters")

    # =====================================================
    # BASE QUERYSET (IMPORTANT FIX)
    # =====================================================
    qs = Question.objects.filter(
        question_type__in=[
            Question.SINGLE,
            Question.MULTI,
            Question.TRUE_FALSE
        ]
    ).prefetch_related("choices")

    selected_domain = None

    if domain_id and domain_id.isdigit():
        selected_domain = Domain.objects.filter(id=domain_id, is_active=True).first()
        if selected_domain:
            qs = qs.filter(category__domain=selected_domain)

    if category_id and category_id.isdigit() and selected_domain:
        cat = Category.objects.filter(
            id=category_id,
            domain=selected_domain,
            is_active=True
        ).first()
        if cat:
            qs = qs.filter(category_id__in=cat.get_descendants_include_self())

    if difficulty:
        qs = qs.filter(difficulty=difficulty)

    # =====================================================
    # RESET SESSION ON FILTER CHANGE
    # =====================================================
    if filters != last_filters:
        request.session["p_filters"] = filters
        request.session["p_seen"] = []
        request.session.pop("p_qid", None)
        request.session["p_total"] = qs.count()

    seen = request.session.get("p_seen", [])
    total = request.session.get("p_total", qs.count())

    # =====================================================
    # ANON LIMIT
    # =====================================================
    if not request.user.is_authenticated:
        limit = getattr(settings, "BASICS_ANON_LIMIT", 0)
        used = request.session.get("p_anon_count", 0)

        if limit and used >= limit:
            return render(request, "quiz/practice.html", {
                "limit_reached": True,
                "progress_done": used,
                "progress_total": limit,
                "domains": Domain.objects.filter(is_active=True),
                "categories": Category.objects.none(),
                "difficulty_choices": Question.DIFFICULTY_CHOICES,
            })

    # =====================================================
    # REMAINING
    # =====================================================
    remaining = qs.exclude(id__in=seen)

    if not remaining.exists():
        return render(request, "quiz/practice.html", {
            "completed": True,
            "progress_done": total,
            "progress_total": total,
            "domains": Domain.objects.filter(is_active=True),
            "categories": Category.objects.none(),
            "difficulty_choices": Question.DIFFICULTY_CHOICES,
        })

    # =====================================================
    # PICK QUESTION
    # =====================================================
    qid = request.session.get("p_qid")
    question = remaining.filter(id=qid).first() if qid else None

    if not question:
        question = remaining.order_by("?").first()
        request.session["p_qid"] = question.id

    choices = question.choices.order_by("order", "id")

    # =====================================================
    # STATE
    # =====================================================
    result = None
    show_next = False
    correct_choices = choices.filter(is_correct=True)
    selected_choice_id = None
    selected_multi_ids = []

    # =====================================================
    # SUBMIT
    # =====================================================
    if request.method == "POST" and request.POST.get("next") != "1":

        if question.question_type == Question.MULTI:
            selected_multi_ids = list(
                map(int, request.POST.getlist("choice_multi"))
            )
            correct_ids = list(correct_choices.values_list("id", flat=True))
            if set(selected_multi_ids) == set(correct_ids):
                result = "correct"
                show_next = True
            else:
                result = "wrong"

        else:
            selected_choice_id = request.POST.get("choice")
            if selected_choice_id:
                selected = choices.filter(id=selected_choice_id).first()
                if selected and selected.is_correct:
                    result = "correct"
                    show_next = True
                else:
                    result = "wrong"

    # =====================================================
    # NEXT
    # =====================================================
    if request.method == "POST" and request.POST.get("next") == "1":
        seen.append(question.id)
        request.session["p_seen"] = seen
        request.session.pop("p_qid", None)

        if not request.user.is_authenticated:
            request.session["p_anon_count"] = request.session.get("p_anon_count", 0) + 1

        return redirect(request.path + "?" + request.META.get("QUERY_STRING", ""))

    # =====================================================
    # CATEGORIES
    # =====================================================
    categories = Category.objects.filter(
        domain=selected_domain,
        is_active=True
    ) if selected_domain else Category.objects.none()

    # =====================================================
    # RENDER
    # =====================================================
    return render(request, "quiz/practice.html", {
        "question": question,
        "choices": choices,
        "result": result,
        "correct_choice": correct_choices.first(),
        "selected_choice_id": selected_choice_id,
        "selected_multi_ids": selected_multi_ids,
        "show_next": show_next,

        "domains": Domain.objects.filter(is_active=True),
        "categories": categories,

        "domain_id": domain_id,
        "category_id": category_id,
        "difficulty": difficulty,
        "difficulty_choices": Question.DIFFICULTY_CHOICES,

        "progress_done": len(seen),
        "progress_total": total,
    })










import random
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET, require_POST
from django.utils import timezone

from .models import Domain, Category, Question, PracticeStat



# =====================================================
# PRACTICE EXPRESS – PAGE
# =====================================================

def practice_express(request):
    return render(request, "quiz/practice_express.html", {
        "domains": Domain.objects.filter(is_active=True),
        "categories": Category.objects.none(),
        "difficulty_choices": Question.DIFFICULTY_CHOICES,
    })


# =====================================================
# PRACTICE EXPRESS – NEXT QUESTION (AJAX)
# =====================================================
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.conf import settings

from .models import Question, Category

@require_GET
def practice_express_next(request):

    # -------------------------------
    # READ FILTERS
    # -------------------------------
    domain_id = request.GET.get("domain")
    category_id = request.GET.get("category")
    difficulty = request.GET.get("difficulty")

    domain_id = domain_id if domain_id and domain_id.isdigit() else None
    category_id = category_id if category_id and category_id.isdigit() else None
    difficulty = difficulty if difficulty else None

    current_filters = {
        "domain": domain_id,
        "category": category_id,
        "difficulty": difficulty,
    }

    last_filters = request.session.get("pe_filters")

    # -------------------------------
    # BASE QUERYSET (🔥 FIXED)
    # ❌ REMOVED question_type filter
    # -------------------------------
    qs = Question.objects.filter(
        category__isnull=False
    ).prefetch_related("choices")

    # -------------------------------
    # DOMAIN FILTER
    # -------------------------------
    if domain_id:
        qs = qs.filter(category__domain_id=domain_id)

    # -------------------------------
    # CATEGORY FILTER (DESCENDANTS)
    # -------------------------------
    if category_id:
        cat = Category.objects.filter(
            id=category_id,
            domain_id=domain_id,
            is_active=True
        ).first()
        if cat:
            qs = qs.filter(
                category_id__in=cat.get_descendants_include_self()
            )

    # -------------------------------
    # DIFFICULTY FILTER
    # -------------------------------
    if difficulty:
        qs = qs.filter(difficulty=difficulty)

    # -------------------------------
    # RESET WHEN FILTERS CHANGE
    # -------------------------------
    if current_filters != last_filters:
        request.session["pe_filters"] = current_filters
        request.session["pe_seen_qids"] = []
        request.session["pe_total"] = qs.count()
        request.session["pe_anon_attempted"] = 0

    seen_qids = request.session.get("pe_seen_qids", [])
    total_questions = request.session.get("pe_total", qs.count())
    anon_attempted = request.session.get("pe_anon_attempted", 0)

    # -------------------------------
    # NO QUESTIONS
    # -------------------------------
    if total_questions == 0:
        return JsonResponse({
            "no_questions": True,
            "progress_done": 0,
            "progress_total": 0,
        })

    # -------------------------------
    # 🔒 ANON LIMIT (SETTINGS)
    # -------------------------------
    if not request.user.is_authenticated:
        limit = getattr(settings, "EXPRESS_ANON_LIMIT", 0)

        if anon_attempted >= limit:
            return JsonResponse({
                "limit_reached": True,
                "message": f"Free limit of {limit} question(s) reached.",
                "progress_done": anon_attempted,
                "progress_total": limit,
            })

    # -------------------------------
    # REMAINING QUESTIONS
    # -------------------------------
    remaining = qs.exclude(id__in=seen_qids)

    # -------------------------------
    # COMPLETED
    # -------------------------------
    if not remaining.exists():
        request.session["pe_seen_qids"] = []
        return JsonResponse({
            "completed": True,
            "progress_done": total_questions,
            "progress_total": total_questions,
        })

    # -------------------------------
    # PICK NEXT QUESTION
    # -------------------------------
    question = remaining.order_by("?").first()
    correct_choices = question.choices.filter(is_correct=True)

    seen_qids.append(question.id)
    request.session["pe_seen_qids"] = seen_qids

    if not request.user.is_authenticated:
        request.session["pe_anon_attempted"] = anon_attempted + 1

    # -------------------------------
    # RESPONSE (🔥 SUPPORTS ALL TYPES)
    # -------------------------------
    return JsonResponse({
        "id": question.id,
        "text": question.text,
        "question_type": question.question_type,
        "explanation": question.explanation or "",
        "correct_choices": [c.id for c in correct_choices],
        "choices": [
            {"id": c.id, "text": c.text}
            for c in question.choices.all().order_by("order", "id")
        ],
        "progress_done": len(seen_qids),
        "progress_total": total_questions,
    })


# =====================================================
# AJAX: LOAD CATEGORIES BY DOMAIN
# =====================================================
@require_GET
def ajax_categories_by_domain(request):
    domain_id = request.GET.get("domain")

    if not domain_id or not domain_id.isdigit():
        return JsonResponse({"categories": []})

    categories = Category.objects.filter(
        domain_id=domain_id,
        is_active=True
    ).values("id", "name", "parent_id")

    return JsonResponse({
        "categories": list(categories)
    })



# =====================================================
# PRACTICE EXPRESS – SAVE RESULT (AJAX, LOGIN ONLY)
# =====================================================
@require_POST
@login_required
def practice_express_save(request):
    question_id = request.POST.get("question_id")
    is_correct = request.POST.get("is_correct") == "true"

    question = Question.objects.select_related("category").get(id=question_id)
    today = timezone.now().date()

    stat, _ = PracticeStat.objects.get_or_create(
        user=request.user,
        category=question.category
    )

    # streak logic
    if stat.last_practice_date == today:
        pass
    elif stat.last_practice_date == today - timezone.timedelta(days=1):
        stat.streak += 1
    else:
        stat.streak = 1

    stat.last_practice_date = today
    stat.total_attempted += 1
    if is_correct:
        stat.total_correct += 1

    stat.save()

    return JsonResponse({
        "total": stat.total_attempted,
        "correct": stat.total_correct,
        "accuracy": stat.accuracy(),
        "streak": stat.streak
    })

















# -----------------------
# Auth views (login & password reset)
# -----------------------

class CustomLoginView(LoginView):
    """
    Use our custom AuthenticationForm (EmailOrUsernameLoginForm) which
    shows "Username or Email" placeholder and integrates with our backend.
    """
    template_name = 'registration/login.html'
    authentication_form = EmailOrUsernameLoginForm
    redirect_authenticated_user = True


class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('quiz:login')  # change if you prefer different redirect


class CustomPasswordResetView(PasswordResetView):
    template_name = 'registration/password_reset_form.html'
    email_template_name = 'registration/password_reset_email.html'
    success_url = reverse_lazy('quiz:password_reset_done')
    # Optionally set subject_template_name, from_email etc.


class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'registration/password_reset_done.html'


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'registration/password_reset_confirm.html'
    success_url = reverse_lazy('quiz:password_reset_complete')


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'registration/password_reset_complete.html'

# quiz/views.py
from django.views.generic import CreateView
from django.contrib.auth import login, authenticate
from django.contrib.auth.models import User
from django.contrib import messages
from django.db import IntegrityError          # ← THIS WAS MISSING!
from django.urls import reverse_lazy
from django.core.mail import send_mail
from .forms import CustomerRegisterForm

from django.views.generic import CreateView
from django.urls import reverse_lazy
from django.contrib.auth import login, authenticate, get_user_model
from django.contrib import messages
from django.core.mail import send_mail
from django.db import IntegrityError
from django.conf import settings

User = get_user_model()


class CustomerRegisterView(CreateView):
    template_name = 'registration/customerregister.html'
    form_class = CustomerRegisterForm
    success_url = reverse_lazy('quiz:dashboard')

    def form_valid(self, form):
        cleaned = form.cleaned_data

        email = cleaned.get('email')
        password = cleaned.get('password')
        username = cleaned.get('username')
        first_name = cleaned.get('first_name')
        last_name = cleaned.get('last_name')

        try:
            # 1️⃣ Create user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )

            # 2️⃣ Create client profile
            client = form.save(commit=False)
            client.user = user
            client.save()

            # 3️⃣ Send welcome email (SAFE)
            try:
                send_mail(
                    subject="Welcome to nptor.com - Your Learning Journey Starts Now!",
                    message=(
                        f"Hello {first_name or username},\n\n"
                        "Thank you for joining nptor.com.\n\n"
                        "Your account has been created successfully.\n\n"
                        f"Login here: https://nptor.com/quiz/login/\n\n"
                        "Happy Learning!\n"
                        "Team nptor.com"
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=True,   # ✅ NEVER break registration
                )
            except Exception:
                pass

            # 4️⃣ Auto login
            user = authenticate(username=username, password=password)
            if user:
                login(self.request, user)
                messages.success(
                    self.request,
                    f"Welcome, {first_name or username}! You are now logged in."
                )
            else:
                messages.info(
                    self.request,
                    "Account created successfully. Please log in."
                )

            return super().form_valid(form)

        except IntegrityError:
            messages.error(
                self.request,
                "This email or username is already registered. Please log in instead."
            )
            return self.form_invalid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)




def register(request):
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # THIS IS THE ONLY LINE THAT MATTERS IN DJANGO 6.0
            login(request, user, backend='quiz.auth_backends.EmailOrUsernameModelBackend')
            
            messages.success(request, "Welcome!")
            return redirect("quiz:dashboard")
    else:
        form = RegistrationForm()

    return render(request, "registration/register.html", {"form": form})





# -------------------------
# Helpers
# -------------------------
def _user_passed_exam(user, exam):
    """
    Return True if user has any UserExam for `exam` with passed=True.
    Non-destructive check used for gating rules.
    """
    return UserExam.objects.filter(user=user, exam=exam, passed=True).exists()


# -------------------------
# Notifications
# -------------------------
@login_required
def notifications_list(request):
    qs = Notification.objects.order_by('-created_at')
    visible = []

    for n in qs:
        # add transient boolean for template convenience
        n.is_unread = n.unread_for(request.user)
        if (not n.users.exists()) or (request.user in n.users.all()):
            visible.append(n)

    return render(request, 'quiz/notifications_list.html', {'notifications': visible})


@login_required
def notification_read(request, pk):
    n = get_object_or_404(Notification, pk=pk)
    n.mark_read(request.user)
    return render(request, 'quiz/notification_detail.html', {'notification': n})


@login_required
def notifications_mark_all(request):
    qs = Notification.objects.order_by('-created_at')[:200]
    visible = [n for n in qs if (not n.users.exists()) or (request.user in n.users.all())]
    for n in visible:
        n.mark_read(request.user)
    return redirect(request.META.get('HTTP_REFERER', '/'))


# -------------------------
# Generic dashboards
# -------------------------
@login_required
def dashboard(request):
    exams_count = Exam.objects.count()
    published = Exam.objects.filter(is_published=True).count()
    active_attempts = UserExam.objects.filter(submitted_at__isnull=True).count()
    users_count = User.objects.count()
    my_attempts = UserExam.objects.filter(user=request.user).order_by('-started_at')[:5]

    context = {
        'exams_count': exams_count,
        'published_count': published,
        'active_attempts': active_attempts,
        'users_count': users_count,
        'my_attempts': my_attempts,
    }
    return render(request, 'quiz/dashboard.html', context)


@login_required
def dashboard_dispatch(request):
    """
    Single entry point: sends admins to admin dashboard, students to student dashboard.
    """
    if request.user.is_staff or request.user.is_superuser:
        return redirect('quiz:admin_dashboard')
    return redirect('quiz:student_dashboard')


# -------------------------
# Admin dashboard + API
# -------------------------
# add at top of file (if not present)
@staff_member_required
def admin_dashboard(request):
    # Top stats
    exams_count = Exam.objects.count()
    published_count = Exam.objects.filter(is_published=True).count()
    total_users = User.objects.count()
    total_attempts = UserExam.objects.count()
    pending_attempts = UserExam.objects.filter(submitted_at__isnull=True).count()
    avg = (
        UserExam.objects
        .filter(submitted_at__isnull=False)
        .aggregate(avg_score=Avg('score'))['avg_score']
        or 0.0
    )

    # Question & category stats
    total_questions = Question.objects.count()

    # Per-category stats (top 20 by question count)
    categories_stats = (
        Category.objects
        .annotate(
            total_questions=Count('questions', distinct=True),
            easy_count=Count(
                'questions',
                filter=Q(questions__difficulty=Question.EASY),
                distinct=True,
            ),
            medium_count=Count(
                'questions',
                filter=Q(questions__difficulty=Question.MEDIUM),
                distinct=True,
            ),
            hard_count=Count(
                'questions',
                filter=Q(questions__difficulty=Question.HARD),
                distinct=True,
            ),
        )
        .order_by('-total_questions', 'name')[:20]
    )

    context = {
        'exams_count': exams_count,
        'published_count': published_count,
        'total_users': total_users,
        'total_attempts': total_attempts,
        'pending_attempts': pending_attempts,
        'avg_score': round(avg, 2),

        'total_questions': total_questions,
        'categories_stats': categories_stats,
    }
    return render(request, 'quiz/admin_dashboard.html', context)




@staff_member_required
def recent_attempts_api(request):
    """
    Returns JSON of UserExam rows for page `page`.
    Query params:
      - page: int (1-indexed)
      - page_size: optional
      - q: optional filter string (username or exam.title)
    """
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 8))
    q = (request.GET.get('q') or '').strip()

    qs = UserExam.objects.select_related('user', 'exam').order_by('-started_at')
    if q:
        qs = qs.filter(Q(user__username__icontains=q) | Q(exam__title__icontains=q))

    paginator = Paginator(qs, page_size)
    page_obj = paginator.get_page(page)

    fmt = get_format('SHORT_DATETIME_FORMAT')
    rows = []
    for ue in page_obj.object_list:
        started = DateFormat(ue.started_at).format(fmt) if ue.started_at else ''
        if ue.submitted_at is None:
            score_text = "In progress"
        else:
            score_text = f"{round(ue.score or 0.0, 2)}%"
        rows.append({
            'id': ue.id,
            'user': ue.user.username,
            'exam': ue.exam.title,
            'started': started,
            'score': score_text,
            'status': 'in_progress' if ue.submitted_at is None else 'completed'
        })

    return JsonResponse({
        'results': rows,
        'has_next': page_obj.has_next(),
        'next_page': page_obj.next_page_number() if page_obj.has_next() else None,
        'page': page,
        'page_size': page_size,
    })







# -------------------------
# Student dashboard
# -------------------------
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone
from django.conf import settings

from .models import Exam, UserExam
from .utils import cleanup_illegal_attempts, check_exam_lock


@login_required
def student_dashboard(request):
    user = request.user

    # 🔒 Clean only illegal ACTIVE attempts (UNCHANGED)
    cleanup_illegal_attempts(user)

    # -----------------------------
    # SUMMARY STATS (UNCHANGED)
    # -----------------------------
    attempts = UserExam.objects.filter(user=user)

    completed = attempts.filter(submitted_at__isnull=False)
    passed = completed.filter(passed=True)
    failed = completed.filter(passed=False)

    active_attempt = attempts.filter(
        submitted_at__isnull=True
    ).select_related("exam").first()

    # -----------------------------
    # SETTINGS (ADD-ON)
    # -----------------------------
    cooldown_minutes = getattr(settings, "RETAKE_COOLDOWN_MINUTES", 30)
    cooldown_total_seconds = cooldown_minutes * 60

    # -----------------------------
    # LOAD ALL PUBLISHED EXAMS (UNCHANGED)
    # -----------------------------
    exams = (
        Exam.objects
        .filter(is_published=True)
        .select_related("track")
        .order_by("level", "title")
    )

    # -----------------------------
    # GROUP BY TRACK
    # -----------------------------
    track_map = {}

    for exam in exams:
        track_name = exam.track.title if exam.track else "General"
        track_map.setdefault(track_name, [])

        last_attempt = (
            attempts.filter(exam=exam)
            .order_by("-started_at")
            .first()
        )

        # -----------------------------
        # EXISTING LOCK LOGIC (UNCHANGED)
        # -----------------------------
        locked, reason = check_exam_lock(user, exam)

        # -----------------------------
        # ➕ ADDITIONAL STRICT LEVEL LOCK
        # (does NOT replace existing logic)
        # -----------------------------
        if not locked and exam.level > 1:
            prev_level_passed = UserExam.objects.filter(
                user=user,
                exam__track=exam.track,
                exam__level=exam.level - 1,
                passed=True
            ).exists()

            if not prev_level_passed:
                locked = True
                reason = f"Pass Level {exam.level - 1} to unlock"

        # -----------------------------
        # ACTION LOGIC (ENHANCED, NOT REMOVED)
        # -----------------------------
        action = "start"
        cooldown_remaining = None
        status = "not_attempted"

        if locked:
            action = "locked"
            status = "locked"

        elif last_attempt:
            if last_attempt.submitted_at is None:
                action = "resume"
                status = "in_progress"

            elif last_attempt.passed is True:
                action = "passed"
                status = "passed"

            elif last_attempt.passed is False:
                status = "failed"

                elapsed = (timezone.now() - last_attempt.submitted_at).total_seconds()
                remaining = max(0, int(cooldown_total_seconds - elapsed))

                if remaining > 0:
                    action = "cooldown"
                    cooldown_remaining = remaining
                else:
                    action = "retake"

        track_map[track_name].append({
            "exam": exam,
            "last_attempt": last_attempt,
            "action": action,
            "status": status,                     # ➕ ADD
            "locked": locked,
            "lock_reason": reason,
            "cooldown_remaining": cooldown_remaining,  # ➕ ADD
        })

    # -----------------------------
    # CONTEXT (UNCHANGED + ADDITIVE)
    # -----------------------------
    context = {
        "total_attempts": attempts.count(),
        "passed_count": passed.count(),
        "failed_count": failed.count(),
        "active_attempt": active_attempt,
        "track_map": track_map,
    }

    return render(request, "quiz/student_dashboard.html", context)






# -------------------------
# Profile / users
# -------------------------
@login_required
def profile(request):
    if request.method == 'POST':
        new_username = request.POST.get('username')
        if new_username:
            request.user.username = new_username
            request.user.save()
            messages.success(request, 'Profile updated.')
    return render(request, 'quiz/profile.html', {'user': request.user})


from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from django.db.models import Q
from django.shortcuts import render


@user_passes_test(lambda u: u.is_staff)
def users_list(request):
    q = (request.GET.get('q') or '').strip()

    users_qs = User.objects.all().order_by('username')

    if q:
        users_qs = users_qs.filter(
            Q(username__icontains=q) |
            Q(email__icontains=q)
        )

    return render(request, 'quiz/users_list.html', {
        'users': users_qs,
    })


























#####################EXAM MANAGEMENT##############################

from django.db import transaction


import math
import random
from django.db.models import Q

def allocate_questions_for_exam(exam, seed=None):
    """
    Enterprise-grade allocation engine.
    - Supports fixed + percentage allocation
    - Deterministic if seed is provided (recommended: user_exam.id)
    - Prevents over-allocation
    - Uses active questions only
    """

    total_needed = int(exam.question_count)
    if total_needed <= 0:
        return []

    rng = random.Random(seed) if seed is not None else random
    allocations = list(exam.allocations.select_related('category').all())

    base_qs = Question.objects.filter(is_active=True)


    selected_qs = []
    selected_ids = set()

    # -------------------------------------------------
    # 0️⃣ Guard: fixed_count overflow
    # -------------------------------------------------
    fixed_total = sum(a.fixed_count or 0 for a in allocations)
    if fixed_total > total_needed:
        raise ValueError(
            f"Fixed allocation ({fixed_total}) exceeds exam.question_count ({total_needed})"
        )

    remaining_needed = total_needed

    # -------------------------------------------------
    # 1️⃣ FIXED COUNT ALLOCATION
    # -------------------------------------------------
    percent_allocs = []
    percent_sum = 0

    for a in allocations:
        if a.fixed_count:
            try:
                cat_ids = a.category.get_descendants_include_self()
            except Exception:
                cat_ids = [a.category.id]

            pool = list(
                base_qs.filter(category_id__in=cat_ids).exclude(id__in=selected_ids)
            )
            rng.shuffle(pool)

            take = min(len(pool), a.fixed_count)
            chosen = pool[:take]

            selected_qs.extend(chosen)
            selected_ids.update(q.id for q in chosen)
            remaining_needed -= take
        else:
            percent_allocs.append(a)
            percent_sum += a.percentage

    # -------------------------------------------------
    # 2️⃣ PERCENTAGE ALLOCATION
    # -------------------------------------------------
    if percent_allocs and remaining_needed > 0 and percent_sum > 0:
        raw = []
        for a in percent_allocs:
            scaled = (a.percentage / percent_sum) * remaining_needed
            raw.append((a, math.floor(scaled), scaled % 1))

        percent_counts = {a.id: cnt for a, cnt, _ in raw}
        allocated = sum(percent_counts.values())
        left = remaining_needed - allocated

        # distribute remainders
        for a, _, _ in sorted(raw, key=lambda x: x[2], reverse=True):
            if left <= 0:
                break
            percent_counts[a.id] += 1
            left -= 1

        for a in percent_allocs:
            cnt = percent_counts.get(a.id, 0)
            if cnt <= 0:
                continue

            try:
                cat_ids = a.category.get_descendants_include_self()
            except Exception:
                cat_ids = [a.category.id]

            pool = list(
                base_qs.filter(category_id__in=cat_ids).exclude(id__in=selected_ids)
            )
            rng.shuffle(pool)

            chosen = pool[:cnt]
            selected_qs.extend(chosen)
            selected_ids.update(q.id for q in chosen)

    # -------------------------------------------------
    # 3️⃣ FALLBACK: legacy category
    # -------------------------------------------------
    if len(selected_qs) < total_needed and exam.category:
        needed = total_needed - len(selected_qs)
        try:
            cat_ids = exam.category.get_descendants_include_self()
        except Exception:
            cat_ids = [exam.category.id]

        pool = list(
            base_qs.filter(category_id__in=cat_ids).exclude(id__in=selected_ids)
        )
        rng.shuffle(pool)
        selected_qs.extend(pool[:needed])
        selected_ids.update(q.id for q in pool[:needed])

    # -------------------------------------------------
    # 4️⃣ GLOBAL FALLBACK
    # -------------------------------------------------
    if len(selected_qs) < total_needed:
        needed = total_needed - len(selected_qs)
        pool = list(base_qs.exclude(id__in=selected_ids))
        rng.shuffle(pool)
        selected_qs.extend(pool[:needed])

    # -------------------------------------------------
    # FINAL SHUFFLE (order is stored anyway)
    # -------------------------------------------------
    rng.shuffle(selected_qs)
    return selected_qs[:total_needed]



@login_required
def exam_list(request):
    exams = (
        Exam.objects
        .filter(is_published=True)
        .select_related('category')
        .prefetch_related('categories')
        .order_by('level', 'title')
    )

    # Build map: exam_id -> active UserExam (or None)
    active_attempts = {
        ue.exam_id: ue
        for ue in UserExam.objects.filter(
            user=request.user,
            submitted_at__isnull=True,
            exam__in=exams
        )
    }

    return render(request, 'quiz/exam_list.html', {
        'exams': exams,
        'active_attempts': active_attempts,
    })








@login_required
def exam_start(request, exam_id):
    exam = get_object_or_404(Exam, pk=exam_id, is_published=True)

    try:
        with transaction.atomic():

            # 🔒 Prevent race condition (double attempts)
            existing = (
                UserExam.objects
                .select_for_update()
                .filter(user=request.user, exam=exam, submitted_at__isnull=True)
                .first()
            )
            if existing:
                return redirect('quiz:exam_take', user_exam_id=existing.id)

            # 2️⃣ Prerequisite exams gating
            prereqs = list(exam.prerequisite_exams.all())
            if prereqs:
                missing = [
                    p for p in prereqs
                    if not UserExam.objects.filter(
                        user=request.user,
                        exam=p,
                        passed=True
                    ).exists()
                ]
                if missing:
                    messages.error(
                        request,
                        "You must pass prerequisite exam(s): " +
                        ", ".join(p.title for p in missing)
                    )
                    return redirect('quiz:student_dashboard')

            # 3️⃣ Level-based gating
            if exam.level and exam.level > 1:
                has_prev_level = UserExam.objects.filter(
                    user=request.user,
                    exam__level=exam.level - 1,
                    passed=True
                ).exists()
                if not has_prev_level:
                    messages.error(
                        request,
                        f"You must pass at least one Level {exam.level - 1} exam to unlock this exam."
                    )
                    return redirect('quiz:student_dashboard')

            # 4️⃣ Create attempt FIRST (for deterministic seed)
            ue = UserExam.objects.create(
                user=request.user,
                exam=exam
            )

            # 5️⃣ Deterministic allocation
            questions = allocate_questions_for_exam(exam, seed=ue.id)
            if not questions:
                raise ValueError("No questions allocated")

            ue.question_order = [q.id for q in questions]
            ue.current_index = 0
            ue.save()

            # 6️⃣ Create answers
            UserAnswer.objects.bulk_create([
                UserAnswer(user_exam=ue, question=q)
                for q in questions
            ])

    except Exception:
        messages.error(
            request,
            "This exam is not properly configured. Please contact support."
        )
        return redirect('quiz:student_dashboard')

    return redirect('quiz:exam_question', user_exam_id=ue.id, index=0)








@login_required
def exam_take(request, user_exam_id):
    ue = get_object_or_404(UserExam, pk=user_exam_id, user=request.user)
    return redirect('quiz:exam_question', user_exam_id=ue.id, index=ue.current_index or 0)


@login_required
def exam_question(request, user_exam_id, index):
    ue = get_object_or_404(UserExam, pk=user_exam_id, user=request.user)
    if ue.submitted_at:
        return redirect('quiz:exam_result', user_exam_id=ue.id)

    remaining = ue.time_remaining()
    if remaining <= 0:
        return redirect('quiz:exam_expired', user_exam_id=ue.id)


    q_ids = ue.question_order or []
    if index < 0 or index >= len(q_ids):
        return redirect('quiz:exam_take', user_exam_id=ue.id)

    q_id = q_ids[index]
    ua = ue.answers.get(question_id=q_id)
    q = ua.question

    choices = list(q.choices.all()) if q.question_type in ('single', 'multi', 'tf', 'dropdown') else []
    if choices:
        random.shuffle(choices)

    ue.current_index = index
    ue.save()
    progress = int(((index + 1) / len(q_ids)) * 100) if q_ids else 0

    return render(request, 'quiz/exam_question.html', {
        'user_exam': ue,
        'ua': ua,
        'question': q,
        'choices': choices,
        'index': index,
        'total': len(q_ids),
        'remaining': remaining,
        'progress': progress,
    })



# -------------------------
# Submit / grade
# -------------------------
@login_required
def exam_submit(request, user_exam_id):
    ue = get_object_or_404(UserExam, pk=user_exam_id, user=request.user)

    # Prevent double submit
    if ue.submitted_at:
        return redirect('quiz:exam_result', user_exam_id=ue.id)

    # Time expired
    if ue.time_remaining() <= 0:
        ue.submitted_at = timezone.now()
        ue.score = 0
        ue.passed = False
        ue.save()
        return redirect('quiz:exam_result', user_exam_id=ue.id)

    if request.method != 'POST':
        return redirect('quiz:exam_question', user_exam_id=ue.id, index=ue.current_index)

    # Canonical question order
    if ue.question_order:
        qids = [int(x) for x in ue.question_order]
    else:
        qids = list(ue.answers.values_list('question_id', flat=True))

    total = 0
    score_acc = 0.0

    for qid in qids:
        ua, _ = UserAnswer.objects.get_or_create(
            user_exam=ue,
            question_id=qid
        )
        q = ua.question
        total += 1

        # ==================================================
        # SINGLE / DROPDOWN  ✅ FIXED (AUTOSAVE SAFE)
        # ==================================================
        if q.question_type in ('single', 'dropdown'):
            choice_id = request.POST.get(f'question_{q.id}')

            if choice_id:
                try:
                    ch = Choice.objects.get(pk=int(choice_id), question=q)
                    ua.choice = ch
                    ua.is_correct = ch.is_correct is True
                    if ua.is_correct:
                        score_acc += 1.0
                except Exception:
                    # fallback to autosaved value
                    if ua.choice and ua.is_correct:
                        score_acc += 1.0
                    else:
                        ua.is_correct = False
            else:
                # fallback to autosaved value
                if ua.choice and ua.is_correct:
                    score_acc += 1.0
                else:
                    ua.is_correct = False

            ua.selections = None
            ua.raw_answer = None
            ua.save()

        # ==================================================
        # TRUE / FALSE  ✅ FIXED
        # ==================================================
        elif q.question_type == 'tf':
            choice_id = request.POST.get(f'question_{q.id}')

            try:
                ch = Choice.objects.get(pk=int(choice_id), question=q)
                ua.choice = ch
                ua.is_correct = ch.is_correct is True
                if ua.is_correct:
                    score_acc += 1.0
            except Exception:
                ua.is_correct = False
                ua.choice = None

            ua.selections = None
            ua.raw_answer = None
            ua.save()

        # ==================================================
        # MULTI SELECT  ✅ FIXED
        # ==================================================
        elif q.question_type == 'multi':
            selections = request.POST.getlist(f'question_{q.id}')

            if selections:
                try:
                    sel_ids = [int(x) for x in selections if x]
                except ValueError:
                    sel_ids = [int(x) for x in selections if str(x).isdigit()]
                ua.selections = sel_ids
            else:
                sel_ids = ua.selections or []

            correct_ids = list(
                q.choices.filter(is_correct=True)
                .values_list('id', flat=True)
            )

            selected_set = set(sel_ids)
            correct_set = set(correct_ids)

            # ✔ Fully correct
            if selected_set == correct_set:
                ua.is_correct = True
                score_acc += 1.0

            # ✘ Fully incorrect
            elif selected_set.isdisjoint(correct_set):
                ua.is_correct = False

            # ◐ Partial
            else:
                ua.is_correct = None
                true_pos = len(selected_set & correct_set)
                false_pos = len(selected_set - correct_set)
                fraction = max(
                    0.0,
                    (true_pos - 0.5 * false_pos) / max(1, len(correct_set))
                )
                score_acc += fraction

            ua.choice = None
            ua.raw_answer = None
            ua.save()

        # ==================================================
        # FILL IN THE BLANK
        # ==================================================
        elif q.question_type == 'fill':
            raw = (request.POST.get(f'question_{q.id}') or '').strip()
            ua.raw_answer = raw

            def norm(s): return ' '.join(s.lower().split())

            if q.correct_text and norm(raw) == norm(q.correct_text):
                ua.is_correct = True
                score_acc += 1.0
            else:
                ua.is_correct = False

            ua.choice = None
            ua.selections = None
            ua.save()

        # ==================================================
        # NUMERIC
        # ==================================================
        elif q.question_type == 'numeric':
            raw = (request.POST.get(f'question_{q.id}') or '').strip()
            ua.raw_answer = raw

            try:
                val = float(raw)
                tol = q.numeric_tolerance or 0.0
                if q.numeric_answer is not None and abs(val - q.numeric_answer) <= tol:
                    ua.is_correct = True
                    score_acc += 1.0
                else:
                    ua.is_correct = False
            except Exception:
                ua.is_correct = False

            ua.choice = None
            ua.selections = None
            ua.save()

        else:
            ua.save()

    # ==================================================
    # FINALIZE RESULT
    # ==================================================
    ue.score = round((score_acc / total) * 100, 2) if total else 0
    ue.submitted_at = timezone.now()

    is_mock = request.session.get(f"mock_exam_{ue.id}", False)
    ue.passed = None if is_mock else ue.score >= (ue.exam.passing_score or 0)

    ue.save()

    return redirect('quiz:exam_result', user_exam_id=ue.id)






# -------------------------
# Result view
# -------------------------



@login_required
def exam_result(request, user_exam_id):
    ue = get_object_or_404(UserExam, pk=user_exam_id, user=request.user)

    # =====================================================
    # HANDLE FEEDBACK SUBMISSION
    # =====================================================
    if request.method == 'POST':
        qid_raw = request.POST.get('question_id')
        comment = (request.POST.get('comment') or '').strip()
        is_incorrect = bool(request.POST.get('is_answer_incorrect'))

        try:
            qid = int(qid_raw)
        except (TypeError, ValueError):
            messages.error(request, "Invalid question reference.")
            return redirect('quiz:exam_result', user_exam_id=ue.id)

        if not ue.answers.filter(question_id=qid).exists():
            messages.error(request, "This question does not belong to your exam.")
            return redirect('quiz:exam_result', user_exam_id=ue.id)

        if not comment and not is_incorrect:
            messages.info(request, "Please enter a comment or mark incorrect.")
            return redirect('quiz:exam_result', user_exam_id=ue.id)

        existing = QuestionFeedback.objects.filter(
            user=request.user,
            user_exam=ue,
            question_id=qid
        ).first()

        if existing:
            messages.info(request, "Feedback already submitted.")
            return redirect('quiz:exam_result', user_exam_id=ue.id)

        QuestionFeedback.objects.create(
            user=request.user,
            user_exam=ue,
            question_id=qid,
            comment=comment,
            is_answer_incorrect=is_incorrect,
        )

        messages.success(request, "Thank you for your feedback!")
        return redirect('quiz:exam_result', user_exam_id=ue.id)

    # =====================================================
    # LOAD ANSWERS
    # =====================================================
    answers = list(
        ue.answers
        .select_related('question', 'choice')
        .prefetch_related('question__choices')
    )

    # =====================================================
    # BUILD ANSWER DISPLAY DATA (CRITICAL FIX)
    # =====================================================
    for ans in answers:
        q = ans.question

        ans.user_answers_display = []
        ans.correct_answers_display = []

        # ---------- SINGLE / DROPDOWN / TRUE-FALSE ----------
        if q.question_type in ('single', 'dropdown', 'tf'):
            if ans.choice:
                ans.user_answers_display = [ans.choice.text]

            correct = q.choices.filter(is_correct=True).first()
            if correct:
                ans.correct_answers_display = [correct.text]

        # ---------- MULTI SELECT ----------
        elif q.question_type == 'multi':
            selected_ids = set(ans.selections or [])
            correct_ids = set(
                q.choices.filter(is_correct=True).values_list('id', flat=True)
            )

            ans.user_answers_display = list(
                q.choices.filter(id__in=selected_ids).values_list('text', flat=True)
            )

            ans.correct_answers_display = list(
                q.choices.filter(is_correct=True).values_list('text', flat=True)
            )

            # ✅ Correctness FIX
            if selected_ids == correct_ids:
                ans.is_correct = True
            elif selected_ids & correct_ids:
                ans.is_correct = None   # partial
            else:
                ans.is_correct = False

        # ---------- FILL IN THE BLANK ----------
        elif q.question_type == 'fill':
            if ans.raw_answer:
                ans.user_answers_display = [ans.raw_answer]
            if q.correct_text:
                ans.correct_answers_display = [q.correct_text]

        # ---------- NUMERIC ----------
        elif q.question_type == 'numeric':
            if ans.raw_answer:
                ans.user_answers_display = [ans.raw_answer]
            if q.numeric_answer is not None:
                ans.correct_answers_display = [str(q.numeric_answer)]

        # ---------- MATCH / ORDER ----------
        else:
            if ans.raw_answer:
                ans.user_answers_display = [ans.raw_answer]

    # =====================================================
    # ACCURACY / BEST SCORE
    # =====================================================
    total = len(answers)
    correct_count = sum(1 for a in answers if a.is_correct is True)

    accuracy = round((correct_count / total) * 100, 2) if total else 0

    best_score = (
        UserExam.objects
        .filter(user=request.user, exam=ue.exam, submitted_at__isnull=False)
        .order_by('-score')
        .values_list('score', flat=True)
        .first()
    ) or ue.score

    # =====================================================
    # RETAKE COOLDOWN LOGIC
    # =====================================================
    cooldown_minutes = getattr(settings, "RETAKE_COOLDOWN_MINUTES", 0)
    cooldown_seconds = 0
    can_retake = True

    if cooldown_minutes and ue.submitted_at:
        total_cd = cooldown_minutes * 60
        elapsed = (timezone.now() - ue.submitted_at).total_seconds()
        remaining = max(0, int(total_cd - elapsed))

        if remaining > 0:
            can_retake = False
            cooldown_seconds = remaining

    # =====================================================
    # FEEDBACK MAPS
    # =====================================================
    feedback_qs = QuestionFeedback.objects.filter(user=request.user, user_exam=ue)
    

    feedback_map = {fb.question_id: fb for fb in feedback_qs}

    for ans in answers:
        ans.has_feedback = ans.question_id in feedback_map


    question_ids = [a.question_id for a in answers]
    other_feedback_qs = (
        QuestionFeedback.objects
        .filter(question_id__in=question_ids)
        .exclude(user=request.user)
        .select_related('user')
        .order_by('-created_at')
    )

    comments_map = {}
    for fb in other_feedback_qs:
        comments_map.setdefault(fb.question_id, []).append(fb)

    # =====================================================
    # RENDER
    # =====================================================
    return render(
        request,
        'quiz/result.html',
        {
            'user_exam': ue,
            'answers': answers,
            'accuracy': accuracy,
            'best_score': best_score,
            'can_retake': can_retake,
            'cooldown_seconds': cooldown_seconds,
            'feedback_map': feedback_map,
            'comments_map': comments_map,
        }
    )






@login_required
def exam_resume(request, exam_id):
    """
    Single entry point for an exam.
    - If user has an active attempt → resume
    - Otherwise → start new attempt
    """
    exam = get_object_or_404(Exam, pk=exam_id, is_published=True)

    active = UserExam.objects.filter(
        user=request.user,
        exam=exam,
        submitted_at__isnull=True
    ).order_by('-started_at').first()

    if active:
        return redirect('quiz:exam_take', user_exam_id=active.id)

    return redirect('quiz:exam_start', exam_id=exam.id)



@login_required
def exam_locked(request, exam_id):
    """
    Shown when user tries to access a locked exam.
    Displays reason instead of silent redirect.
    """
    exam = get_object_or_404(Exam, pk=exam_id)

    reasons = []

    # Prerequisite exams
    prereqs = exam.prerequisite_exams.all()
    if prereqs.exists():
        missing = [
            p.title for p in prereqs
            if not UserExam.objects.filter(
                user=request.user,
                exam=p,
                passed=True
            ).exists()
        ]
        if missing:
            reasons.append(
                "You must pass the following exam(s): " + ", ".join(missing)
            )

    # Level-based lock
    if exam.level and exam.level > 1:
        has_prev_level = UserExam.objects.filter(
            user=request.user,
            exam__level=exam.level - 1,
            passed=True
        ).exists()
        if not has_prev_level:
            reasons.append(
                f"You must pass at least one Level {exam.level - 1} exam."
            )

    return render(request, "quiz/exam_locked.html", {
        "exam": exam,
        "reasons": reasons or ["This exam is currently locked."],
    })


@login_required
def exam_expired(request, user_exam_id):
    """
    Called when exam time expires.
    Safely finalizes attempt if not already submitted.
    """
    ue = get_object_or_404(UserExam, pk=user_exam_id, user=request.user)

    if ue.submitted_at:
        return redirect('quiz:exam_result', user_exam_id=ue.id)

    ue.submitted_at = timezone.now()
    ue.score = ue.score or 0.0
    ue.passed = False
    ue.save()

    return render(request, "quiz/exam_expired.html", {
        "user_exam": ue,
    })


@login_required
def mock_exam_start(request, exam_id):
    """
    Starts a mock exam:
    - No prerequisites
    - No pass/fail impact
    - Does NOT unlock progression
    """

    exam = get_object_or_404(Exam, pk=exam_id, is_published=True)

    try:
        with transaction.atomic():
            ue = UserExam.objects.create(
                user=request.user,
                exam=exam
            )

            # Deterministic allocation
            questions = allocate_questions_for_exam(exam, seed=ue.id)

            if not questions:
                raise ValueError("No questions allocated for mock exam")

            ue.question_order = [q.id for q in questions]
            ue.current_index = 0
            ue.save()

            UserAnswer.objects.bulk_create([
                UserAnswer(user_exam=ue, question=q)
                for q in questions
            ])

        # Mark as mock attempt (session-only flag)
        request.session[f"mock_exam_{ue.id}"] = True

    except Exception:
        messages.error(
            request,
            "Mock exam is not available at the moment."
        )
        return redirect('quiz:student_dashboard')

    return redirect('quiz:exam_question', user_exam_id=ue.id, index=0)


# -------------------------
# Autosave endpoint
# -------------------------
# Autosave endpoint (robust)
@login_required
def autosave(request, user_exam_id):
    """
    Autosave partial answers via AJAX. Only updates fields present in the POST payload.
    - Prevents autosave if attempt already submitted.
    - Persists is_correct for single/dropdown/tf so final grading can rely on it.
    - Uses select_for_update inside a transaction to avoid concurrent write races.
    """
    ue = get_object_or_404(UserExam, pk=user_exam_id, user=request.user)

    # refuse autosave for already-submitted attempts (important to avoid clobbering)
    if ue.submitted_at:
        return JsonResponse({'status': 'attempt_already_submitted'}, status=409)

    if request.method != 'POST':
        return JsonResponse({'status': 'method_not_allowed'}, status=405)

    # Build a map of posted keys -> list(values)
    posted = {}
    for k in request.POST.keys():
        if k == 'csrfmiddlewaretoken':
            continue
        posted[k] = request.POST.getlist(k)

    # Partition keys into question_<qid> and match_<qid>_<i> groups
    question_keys = [k for k in posted.keys() if k.startswith('question_')]
    match_keys = [k for k in posted.keys() if k.startswith('match_')]

    # Process standard question_* keys first
    for qkey in question_keys:
        # parse qid from "question_<qid>"
        try:
            qid = int(qkey.split('_', 1)[1])
        except Exception:
            continue

        # ensure question exists and belongs to this exam
        try:
            q = Question.objects.get(pk=qid)
        except Question.DoesNotExist:
            continue

        # get_or_create the UserAnswer row for this attempt/question
        ua, _ = UserAnswer.objects.get_or_create(user_exam=ue, question=q)

        # Lock the row to avoid concurrent autosave/submit races
        with transaction.atomic():
            ua = UserAnswer.objects.select_for_update().get(pk=ua.pk)

            vals = posted.get(qkey) or []
            if q.question_type in ('single', 'dropdown', 'tf'):
                if vals:
                    val = vals[0]
                    try:
                        submitted_pk = int(str(val).strip())
                    except (ValueError, TypeError):
                        submitted_pk = None

                    if submitted_pk is not None:
                        try:
                            ch = Choice.objects.get(pk=submitted_pk, question=q)
                            ua.choice = ch
                            ua.raw_answer = None
                            ua.selections = None
                            # persist correctness now (safe): final submit can rely on it
                            ua.is_correct = bool(ch.is_correct)
                            ua.save()
                        except Choice.DoesNotExist:
                            # invalid choice id: ignore this autosave for the field
                            pass

            elif q.question_type == 'multi':
                if vals:
                    # convert to ints where possible
                    sel_ids = []
                    for v in vals:
                        try:
                            sel_ids.append(int(str(v).strip()))
                        except Exception:
                            # keep any non-int entries as-is (safer to ignore later)
                            pass
                    ua.selections = sel_ids
                    ua.choice = None
                    ua.raw_answer = None
                    # keep is_correct None (final grading will compute)
                    ua.is_correct = None
                    ua.save()

            elif q.question_type in ('fill', 'numeric', 'order'):
                # for these types we just save the raw_answer
                if vals is not None:
                    raw = vals[0] if vals else ''
                    ua.raw_answer = (raw or '').strip()
                    ua.choice = None
                    ua.selections = None
                    ua.is_correct = None
                    ua.save()

            else:
                # unsupported types handled later (match handled separately)
                pass

    # Now process match_* keys (group by question id)
    if match_keys:
        # build dict: qid -> list of (index, posted_value)
        match_by_q = {}
        for k in match_keys:
            # expected key format: "match_<qid>_<li>"
            parts = k.split('_')
            if len(parts) < 3:
                continue
            try:
                qid = int(parts[1])
                li = int(parts[2])
            except Exception:
                continue
            match_by_q.setdefault(qid, {})[li] = posted.get(k)[0] if posted.get(k) else ''

        for qid, mapping in match_by_q.items():
            try:
                q = Question.objects.get(pk=qid)
            except Question.DoesNotExist:
                continue
            ua, _ = UserAnswer.objects.get_or_create(user_exam=ue, question=q)
            with transaction.atomic():
                ua = UserAnswer.objects.select_for_update().get(pk=ua.pk)
                # existing map or empty
                user_map = ua.selections or {}
                changed = False
                for li, val in mapping.items():
                    if val is None or val == '':
                        if str(li) in user_map:
                            user_map.pop(str(li), None)
                            changed = True
                    else:
                        user_map[str(li)] = val
                        changed = True
                if changed:
                    ua.selections = user_map
                    ua.raw_answer = None
                    ua.choice = None
                    ua.is_correct = None
                    ua.save()

    return JsonResponse({'status': 'ok'})




