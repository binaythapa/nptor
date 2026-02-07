import math
import random
import logging
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import login, authenticate, get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView,
)
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Avg, Count, Q, Sum
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.dateformat import DateFormat
from django.utils.formats import get_format
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import CreateView, DetailView, TemplateView, UpdateView

# Project-specific imports
from courses.models import Course, Lesson
from courses.services.progress import get_next_lesson
from courses.services.quiz_completion import *
from quiz.forms import *
from quiz.models import (
    Exam,
    ExamTrack,
    UserExam,
    ExamSubscription,
    ExamTrackSubscription,
    Coupon,
)
from quiz.services.access import can_access_exam
from quiz.services.answer_persistence import autosave_answers
from quiz.services.grading import grade_exam
from quiz.services.pricing import apply_coupon
from quiz.services.subscription import has_valid_subscription
from quiz.utils import get_leaf_category_name

# Re-assign User in case a custom user model is used (overrides the imported User if needed)
User = get_user_model()

# Logger
logger = logging.getLogger(__name__)


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