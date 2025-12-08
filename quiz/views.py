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
from django.urls import reverse_lazy
from .forms import EmailOrUsernameLoginForm  # ensure this exists in quiz/forms.py

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


class CustomerRegisterView(CreateView):
    template_name = 'registration/customerregister.html'
    form_class = CustomerRegisterForm
    success_url = reverse_lazy('quiz:dashboard')

    def form_valid(self, form):
        email = form.cleaned_data.get('email')
        password = form.cleaned_data.get('password')

        try:
            # Create User with email as username
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password
            )

            # Link Client to User
            client = form.save(commit=False)
            client.user = user
            client.save()

            # Send Welcome Email
            send_mail(
                subject="Welcome to nptor.com – Your Learning Journey Starts Now!",
                message=f"""
Hello Learner,

Thank you for joining nptor.com – Nepal's trusted online education platform!

Your account has been created successfully with:
Email: {email}

You can now:
• Access hundreds of video courses
• Join live classes & workshops
• Download study materials
• Track your progress and earn certificates

Login here: http://127.0.0.1:8000/quiz/login/

We're thrilled to have you in our learning community!

Happy Learning!  
Team nptor.com
""",
                from_email='tbinay5@gmail.com',
                recipient_list=[email],
                fail_silently=False,
            )

            # Auto-login
            user = authenticate(username=email, password=password)
            if user:
                login(self.request, user)
                messages.success(self.request, f"Welcome, {email}! You're now logged in.")
            else:
                messages.warning(self.request, "Account created! Please log in.")

            return super().form_valid(form)

        except IntegrityError:   # ← Now recognized because of the import above
            messages.error(
                self.request,
                "This email is already registered. Please log in instead."
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
from django.db.models import Q

@staff_member_required
def admin_dashboard(request):
    from django.db.models import Avg
    exams_count = Exam.objects.count()
    published_count = Exam.objects.filter(is_published=True).count()
    total_users = User.objects.count()
    total_attempts = UserExam.objects.count()
    pending_attempts = UserExam.objects.filter(submitted_at__isnull=True).count()
    avg = UserExam.objects.filter(submitted_at__isnull=False).aggregate(avg_score=Avg('score'))['avg_score'] or 0.0

    # read filter query
    q = (request.GET.get('q') or '').strip()

    # base queryset for recent attempts (apply filter if provided)
    recent_qs = UserExam.objects.select_related('user', 'exam').order_by('-started_at')
    if q:
        recent_qs = recent_qs.filter(
            Q(user__username__icontains=q) | Q(exam__title__icontains=q)
        )

    # paginated recent attempts: show first page server-side
    page_size = 8
    paginator = Paginator(recent_qs, page_size)
    recent_page = paginator.get_page(1)
    recent_attempts = recent_page.object_list

    context = {
        'exams_count': exams_count,
        'published_count': published_count,
        'total_users': total_users,
        'total_attempts': total_attempts,
        'pending_attempts': pending_attempts,
        'avg_score': round(avg, 2),
        'recent_attempts': recent_attempts,
        'recent_has_next': recent_page.has_next(),
        'recent_next_page': recent_page.next_page_number() if recent_page.has_next() else None,
        'recent_page_size': page_size,
        'filter_q': q,            # pass current filter to template
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
@login_required
def student_dashboard(request):
    """
    Student-facing dashboard: shows available exams, active attempt, and past results.
    Adds `exam_items` to indicate locked/unlocked exams for the UI.
    """
    exams = Exam.objects.filter(is_published=True).order_by('title')

    active_attempt = UserExam.objects.filter(user=request.user, submitted_at__isnull=True).order_by('-started_at').first()

    recent_attempts = UserExam.objects.filter(user=request.user, submitted_at__isnull=False).select_related('exam').order_by('-submitted_at')[:8]

    attempted_count = UserExam.objects.filter(user=request.user, submitted_at__isnull=False).count()
    from django.db.models import Max
    best_score_val = UserExam.objects.filter(user=request.user, submitted_at__isnull=False).aggregate(best=Max('score'))['best'] or 0.0

    # Build exam_items to show locked/unlocked state
    exam_items = []
    for e in exams:
        locked = False
        reason = None

        # 1) explicit prerequisites (if exam has M2M 'prerequisite_exams')
        prereqs = list(getattr(e, 'prerequisite_exams', []).all()) if hasattr(e, 'prerequisite_exams') else []
        if prereqs:
            missing = [p for p in prereqs if not _user_passed_exam(request.user, p)]
            if missing:
                locked = True
                reason = 'Pass: ' + ', '.join([m.title for m in missing])

        # 2) level-based gating (if exam has integer 'level' attribute)
        elif getattr(e, 'level', None) and e.level > 1:
            prev_level = e.level - 1
            passed_prev = UserExam.objects.filter(user=request.user, exam__level=prev_level, passed=True).exists()
            if not passed_prev:
                locked = True
                reason = f'Pass at least one Level {prev_level} exam to unlock'

        exam_items.append({'exam': e, 'locked': locked, 'reason': reason})

    context = {
        'exams': exams,
        'active_attempt': active_attempt,
        'recent_attempts': recent_attempts,
        'attempted_count': attempted_count,
        'best_score': round(best_score_val, 2),
        'exam_items': exam_items,
    }
    return render(request, 'quiz/student_dashboard.html', context)


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


@user_passes_test(lambda u: u.is_staff)
def users_list(request):
    users = User.objects.all().order_by('username')
    return render(request, 'quiz/users_list.html', {'users': users})


# -------------------------
# Allocation / selection of questions
# -------------------------
def allocate_questions_for_exam(exam):
    """
    Select questions for `exam` according to ExamCategoryAllocation rows.
    Returns a list of Question objects with length up to exam.question_count (tries to reach exact).
    """
    total_needed = int(exam.question_count)
    allocations = list(exam.allocations.select_related('category').all())

    # No allocations -> fallback to M2M categories, legacy category, or global
    if not allocations:
        m2m_cats = list(exam.categories.all()) if hasattr(exam, 'categories') else []
        if m2m_cats:
            qs = Question.objects.filter(category__in=m2m_cats)
            pool = list(qs)
            random.shuffle(pool)
            return pool[:total_needed]
        elif getattr(exam, 'category', None):
            pool = list(Question.objects.filter(category=exam.category))
            random.shuffle(pool)
            return pool[:total_needed]
        else:
            pool = list(Question.objects.all())
            random.shuffle(pool)
            return pool[:total_needed]

    selected_qs = []
    remaining_needed = total_needed
    percent_allocs = []
    percent_sum = 0

    # 1) fixed_count allocations
    for a in allocations:
        if a.fixed_count:
            cat = a.category
            try:
                cat_ids = cat.get_descendants_include_self()
            except Exception:
                cat_ids = [cat.id]
            pool = list(Question.objects.filter(category_id__in=cat_ids))
            random.shuffle(pool)
            take = min(len(pool), a.fixed_count)
            selected_qs.extend(pool[:take])
            remaining_needed -= take
        else:
            percent_allocs.append(a)
            percent_sum += a.percentage

    # 2) percentage-based allocations from remaining
    percent_counts = {}
    if percent_allocs and remaining_needed > 0 and percent_sum > 0:
        raw = []
        for a in percent_allocs:
            scaled_fraction = (a.percentage / percent_sum) * remaining_needed
            count_floor = math.floor(scaled_fraction)
            remainder = scaled_fraction - count_floor
            raw.append((a, count_floor, remainder))
        for a, cnt, rem in raw:
            percent_counts[a.id] = cnt
        allocated = sum(percent_counts.values())
        left = remaining_needed - allocated
        raw_sorted = sorted(raw, key=lambda x: x[2], reverse=True)
        i = 0
        while left > 0 and i < len(raw_sorted):
            a, cnt, rem = raw_sorted[i]
            percent_counts[a.id] += 1
            left -= 1
            i += 1

        already_selected_ids = {q.id for q in selected_qs}
        for a in percent_allocs:
            cnt = percent_counts.get(a.id, 0)
            if cnt <= 0:
                continue
            try:
                cat_ids = a.category.get_descendants_include_self()
            except Exception:
                cat_ids = [a.category.id]
            pool = list(Question.objects.filter(category_id__in=cat_ids).exclude(id__in=already_selected_ids))
            random.shuffle(pool)
            take = min(len(pool), cnt)
            chosen = pool[:take]
            selected_qs.extend(chosen)
            already_selected_ids.update({q.id for q in chosen})

    # 3) try exam.category subtree
    if len(selected_qs) < total_needed and getattr(exam, 'category', None):
        needed = total_needed - len(selected_qs)
        try:
            cat_ids = exam.category.get_descendants_include_self()
        except Exception:
            cat_ids = [exam.category.id]
        pool = list(Question.objects.filter(category_id__in=cat_ids).exclude(id__in={q.id for q in selected_qs}))
        random.shuffle(pool)
        take = min(len(pool), needed)
        selected_qs.extend(pool[:take])

    # 4) global pool fallback
    if len(selected_qs) < total_needed:
        needed = total_needed - len(selected_qs)
        pool = list(Question.objects.exclude(id__in={q.id for q in selected_qs}))
        random.shuffle(pool)
        take = min(len(pool), needed)
        selected_qs.extend(pool[:take])

    # Trim/shuffle final list
    if len(selected_qs) > total_needed:
        random.shuffle(selected_qs)
        selected_qs = selected_qs[:total_needed]
    else:
        random.shuffle(selected_qs)

    return selected_qs



# -------------------------
# Registration + exam flows
# -------------------------
def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('quiz:exam_list')
    else:
        form = UserCreationForm()
    return render(request, 'quiz/register.html', {'form': form})


@login_required
def exam_list(request):
    exams = Exam.objects.filter(is_published=True)
    return render(request, 'quiz/exam_list.html', {'exams': exams})


@login_required
def exam_start(request, exam_id):
    exam = get_object_or_404(Exam, pk=exam_id, is_published=True)

    # If an active attempt already exists, continue it
    existing = UserExam.objects.filter(user=request.user, exam=exam, submitted_at__isnull=True).first()
    if existing:
        return redirect('quiz:exam_take', user_exam_id=existing.id)

    # GATING: prerequisite exams (M2M) if present
    prereqs_qs = getattr(exam, 'prerequisite_exams', None)
    prereqs = list(prereqs_qs.all()) if prereqs_qs is not None else []
    if prereqs:
        missing = [p for p in prereqs if not _user_passed_exam(request.user, p)]
        if missing:
            messages.error(request, 'You must pass prerequisite exam(s): ' + ', '.join([m.title for m in missing]))
            return redirect('quiz:student_dashboard')

    # Level-based gating fallback
    elif getattr(exam, 'level', None) and exam.level > 1:
        if not UserExam.objects.filter(user=request.user, exam__level=exam.level-1, passed=True).exists():
            messages.error(request, f'You must pass at least one Level {exam.level-1} exam to unlock this exam.')
            return redirect('quiz:student_dashboard')

    # Create attempt after gating checks passed
    ue = UserExam.objects.create(user=request.user, exam=exam)
    qs = allocate_questions_for_exam(exam)
    ue.question_order = [q.id for q in qs]
    ue.save()

    for q in qs:
        UserAnswer.objects.create(user_exam=ue, question=q)

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
        return redirect('quiz:exam_submit', user_exam_id=ue.id)

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
# Autosave endpoint
# -------------------------
@login_required
def autosave(request, user_exam_id):
    """
    Autosave partial answers via AJAX. Accepts form POST
    and stores best-effort values to UserAnswer rows.
    """
    ue = get_object_or_404(UserExam, pk=user_exam_id, user=request.user)
    if request.method != 'POST':
        return JsonResponse({'status': 'method_not_allowed'}, status=405)

    data = request.POST
    posted = {}
    for key in data.keys():
        # use getlist from QueryDict to capture multiple checkbox values
        posted.setdefault(key, data.getlist(key))

    for ua in ue.answers.select_related('question'):
        q = ua.question
        qkey = f'question_{q.id}'

        # SINGLE / DROPDOWN / TF
        if q.question_type in ('single', 'dropdown', 'tf'):
            vals = posted.get(qkey)
            if vals:
                val = vals[0] if isinstance(vals, (list, tuple)) else vals
                try:
                    ch = Choice.objects.get(pk=int(val), question=q)
                    ua.choice = ch
                    ua.raw_answer = None
                    ua.selections = None
                    ua.is_correct = None
                    ua.save()
                except Exception:
                    # invalid id: ignore autosave
                    pass

        # MULTI
        elif q.question_type == 'multi':
            vals = posted.get(qkey)
            if vals:
                try:
                    sel_ids = [int(x) for x in vals if x]
                except Exception:
                    sel_ids = vals
                ua.selections = sel_ids
                ua.choice = None
                ua.raw_answer = None
                ua.is_correct = None
                ua.save()

        # FILL / NUMERIC / ORDER
        elif q.question_type in ('fill', 'numeric', 'order'):
            vals = posted.get(qkey)
            if vals is not None:
                raw = vals[0] if isinstance(vals, (list, tuple)) else vals
                ua.raw_answer = raw
                ua.choice = None
                ua.selections = None
                ua.is_correct = None
                ua.save()

        # MATCH
        elif q.question_type == 'match':
            pairs = q.matching_pairs or []
            user_map = ua.selections or {}
            changed = False
            for i in range(len(pairs)):
                k = f'match_{q.id}_{i}'
                if k in posted:
                    vlist = posted.get(k)
                    val = vlist[0] if isinstance(vlist, (list, tuple)) else vlist
                    if val is None or val == '':
                        if str(i) in user_map:
                            user_map.pop(str(i), None)
                            changed = True
                    else:
                        user_map[str(i)] = val
                        changed = True
            if changed:
                ua.selections = user_map
                ua.raw_answer = None
                ua.choice = None
                ua.is_correct = None
                ua.save()
        else:
            # other question types - ignore autosave
            pass

    return JsonResponse({'status': 'ok'})


# -------------------------
# Submit / grade
# -------------------------
@login_required
def exam_submit(request, user_exam_id):
    ue = get_object_or_404(UserExam, pk=user_exam_id, user=request.user)
    if ue.submitted_at:
        return redirect('quiz:exam_result', user_exam_id=ue.id)

    # if time expired
    if ue.time_remaining() <= 0:
        ue.submitted_at = timezone.now()
        ue.score = 0
        ue.passed = False
        ue.save()
        return redirect('quiz:exam_result', user_exam_id=ue.id)

    if request.method != 'POST':
        return redirect('quiz:exam_question', user_exam_id=ue.id, index=ue.current_index)

    total = 0
    score_acc = 0.0

    for ua in ue.answers.select_related('question'):
        q = ua.question
        total += 1

        # SINGLE / DROPDOWN / TF
        if q.question_type in ('single', 'dropdown', 'tf'):
            choice_id = request.POST.get(f'question_{q.id}')
            if choice_id:
                try:
                    ch = Choice.objects.get(pk=int(choice_id), question=q)
                    ua.choice = ch
                    ua.is_correct = ch.is_correct
                    if ua.is_correct:
                        score_acc += 1.0
                except Choice.DoesNotExist:
                    # invalid id: fall back to autosaved choice if present
                    if ua.choice and ua.choice.question_id == q.id:
                        if ua.is_correct:
                            score_acc += 1.0
                    else:
                        ua.choice = None
                        ua.is_correct = False
            else:
                # no posted value: preserve autosaved value if exists
                if ua.choice:
                    if ua.is_correct:
                        score_acc += 1.0
                else:
                    ua.is_correct = False
            ua.selections = None
            ua.raw_answer = None
            ua.save()

        # MULTI
        elif q.question_type == 'multi':
            selections = request.POST.getlist(f'question_{q.id}')
            if selections:
                sel_ids = [int(x) for x in selections if x]
                ua.selections = sel_ids
            else:
                sel_ids = ua.selections or []

            correct_ids = [c.id for c in q.choices.filter(is_correct=True)]
            if not correct_ids:
                fraction = 0.0
            else:
                true_pos = len(set(sel_ids) & set(correct_ids))
                false_pos = len(set(sel_ids) - set(correct_ids))
                fraction = max(0.0, (true_pos - 0.5 * false_pos) / len(correct_ids))
            score_acc += fraction

            ua.choice = None
            ua.is_correct = None
            ua.raw_answer = None
            ua.save()

        # FILL
        elif q.question_type == 'fill':
            raw = request.POST.get(f'question_{q.id}')
            if raw is None:
                raw = ua.raw_answer or ''
            raw = (raw or '').strip()
            ua.raw_answer = raw

            def norm(s): return ' '.join(s.lower().split())
            if q.correct_text:
                ua.is_correct = norm(raw) == norm(q.correct_text)
                if ua.is_correct:
                    score_acc += 1.0
            else:
                ua.is_correct = False
            ua.selections = None
            ua.choice = None
            ua.save()

        # NUMERIC
        elif q.question_type == 'numeric':
            raw = request.POST.get(f'question_{q.id}')
            if raw is None:
                raw = ua.raw_answer or ''
            raw = (raw or '').strip()
            ua.raw_answer = raw
            try:
                v = float(raw)
                if q.numeric_answer is not None:
                    tol = q.numeric_tolerance or 0.0
                    if abs(v - float(q.numeric_answer)) <= float(tol):
                        ua.is_correct = True
                        score_acc += 1.0
                    else:
                        ua.is_correct = False
                else:
                    ua.is_correct = False
            except Exception:
                ua.is_correct = False
            ua.selections = None
            ua.choice = None
            ua.save()

        # MATCH
        elif q.question_type == 'match':
            pairs = q.matching_pairs or []
            user_map = {}
            true_pos = 0
            false_pos = 0
            for li, pair in enumerate(pairs):
                key = f'match_{q.id}_{li}'
                val = request.POST.get(key)
                if val is not None:
                    if val:
                        user_map[str(li)] = val
                        if str(val) == str(pair.get('right')):
                            true_pos += 1
                        else:
                            false_pos += 1
                    else:
                        false_pos += 1
                else:
                    # fallback to autosaved selection
                    saved_map = ua.selections or {}
                    if str(li) in saved_map:
                        v = saved_map[str(li)]
                        user_map[str(li)] = v
                        if str(v) == str(pair.get('right')):
                            true_pos += 1
                        else:
                            false_pos += 1
                    else:
                        false_pos += 1
            denom = len(pairs) if pairs else 1
            fraction = max(0.0, (true_pos - 0.5 * false_pos) / denom)
            score_acc += fraction

            ua.selections = user_map
            ua.choice = None
            ua.raw_answer = None
            ua.is_correct = None
            ua.save()

        # ORDER
        elif q.question_type == 'order':
            raw = request.POST.get(f'question_{q.id}')
            if raw is None:
                raw = ua.raw_answer or ''
            raw = (raw or '').strip()
            ua.raw_answer = raw
            try:
                user_order = [x.strip() for x in raw.split(',') if x.strip()]
                canonical = q.ordering_items or []
                correct_positions = 0
                denom = max(1, len(canonical))
                for i, val in enumerate(user_order):
                    if i < len(canonical) and canonical[i].strip().lower() == val.strip().lower():
                        correct_positions += 1
                fraction = correct_positions / denom
                score_acc += fraction
            except Exception:
                pass
            ua.selections = None
            ua.choice = None
            ua.save()

        else:
            # fallback: preserve existing saved state
            if ua.is_correct:
                score_acc += 1.0
            ua.save()

    # finalize
    ue.score = (score_acc / total) * 100 if total else 0
    ue.submitted_at = timezone.now()
    try:
        ue.passed = (ue.score >= (ue.exam.passing_score or 0))
    except Exception:
        ue.passed = False
    ue.save()

    return redirect('quiz:exam_result', user_exam_id=ue.id)


# -------------------------
# Result view
# -------------------------
@login_required
def exam_result(request, user_exam_id):
    ue = get_object_or_404(UserExam, pk=user_exam_id, user=request.user)
    answers = ue.answers.select_related('question', 'choice')
    return render(request, 'quiz/result.html', {'user_exam': ue, 'answers': answers})
