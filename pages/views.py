from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from django.shortcuts import render, redirect
from pages.models import Testimonial


from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model

from quiz.models import Question, Exam, ExamTrack, StudyPlan
from pages.models import Testimonial

User = get_user_model()


from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model

from quiz.models import Question, Exam, ExamTrack, StudyPlan
from pages.models import Testimonial

User = get_user_model()

from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model

from quiz.models import Question, Exam, ExamTrack, StudyPlan
from pages.models import Testimonial
from courses.models import Course


User = get_user_model()
from django.shortcuts import render, redirect
from django.contrib.auth.models import User

from quiz.models import Question, Exam, ExamTrack
from courses.models import Course
from pages.models import Testimonial



def home(request):

    # =========================================
    # REDIRECT AUTHENTICATED USERS
    # =========================================

    if request.user.is_authenticated:
        return redirect("quiz:dashboard")

    # =========================================
    # PLATFORM STATS
    # =========================================

    total_questions = Question.objects.active().filter(
        organization__isnull=True
    ).count()

    # ✅ ONLY NORMAL EXAMS
    total_exams = Exam.objects.filter(
        is_published=True,
        organization__isnull=True,
        exam_type=Exam.ExamType.NORMAL
    ).count()

    total_tracks = ExamTrack.objects.filter(
        is_active=True,
        organization__isnull=True
    ).count()

    total_students = User.objects.count()

    total_study_plans = StudyPlan.objects.count()

    # =========================================
    # COURSES
    # =========================================

    courses = Course.objects.filter(
        is_published=True,
        is_public=True,
        organization__isnull=True
    ).order_by("-created_at")

    # =========================================
    # TESTIMONIALS
    # =========================================

    testimonials = Testimonial.objects.filter(
        is_approved=True,
        is_featured=True
    ).order_by("-created_at")[:6]

    # =========================================
    # POPULAR EXAM TRACKS
    # =========================================

    exam_tracks = ExamTrack.objects.filter(
        is_active=True,
        organization__isnull=True
    ).order_by("-created_at")

    # =========================================
    # LATEST MOCK EXAMS
    # ✅ ONLY NORMAL EXAMS
    # =========================================

    latest_exams = Exam.objects.filter(
        is_published=True,
        organization__isnull=True,
        exam_type=Exam.ExamType.NORMAL
    ).select_related(
        "track",
        "organization",
        "category"
    ).prefetch_related(
        "categories"
    ).order_by("-created_at")

    # =========================================
    # CONTEXT
    # =========================================

    context = {
        "testimonials": testimonials,

        # Stats
        "total_questions": total_questions,
        "total_exams": total_exams,
        "total_tracks": total_tracks,
        "total_students": total_students,
        "total_study_plans": total_study_plans,

        # Dynamic Sections
        "courses": courses,
        "exam_tracks": exam_tracks,
        "latest_exams": latest_exams,
    }

    return render(request, "pages/home.html", context)




def about(request):
    return render(request, "pages/about.html")

def privacy(request):
    return render(request, "pages/privacy.html")

def terms(request):
    return render(request, "pages/terms.html")

def contact(request):
    return render(request, "pages/contact.html")

@login_required
def feedback(request):
    return render(request, "pages/feedback.html")


from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .models import Feedback

@login_required
def feedback(request):
    if request.method == "POST":
        Feedback.objects.create(
            user=request.user,
            email=request.user.email,
            message=request.POST.get("message"),
        )
        return render(request, "pages/feedback.html", {"success": True})

    return render(request, "pages/feedback.html")




from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import TestimonialForm

from django.contrib import messages
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from .forms import TestimonialForm


@login_required
def submit_testimonial(request):

    if request.method == "POST":

        form = TestimonialForm(request.POST)

        if form.is_valid():
            testimonial = form.save(commit=False)

            testimonial.user = request.user
            testimonial.name = (
                request.user.get_full_name()
                or request.user.username
            )

            testimonial.is_approved = False  # Admin approval required
            testimonial.save()

            messages.success(
                request,
                "Thank you! Your testimonial has been submitted for review."
            )

            # 🔥 Redirect back to the page where popup was shown
            next_url = request.POST.get("next")

            if next_url:
                return redirect(next_url)

            # Safe fallback
            return redirect("/")

        # If form invalid → return back to same page
        next_url = request.POST.get("next")
        return redirect(next_url or "/")

    # If someone directly opens URL (GET request)
    return redirect("/")