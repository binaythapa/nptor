from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib import messages

from quiz.models import Question, Exam, ExamTrack, StudyPlan
from pages.models import Testimonial, Feedback
from courses.models import Course
from .forms import TestimonialForm

User = get_user_model()

# Keep homepage payloads bounded regardless of catalogue size.
HOMEPAGE_LIMIT = 6


def home(request):
    """Render the public homepage or route authenticated users to their dashboard."""
    if request.user.is_authenticated:
        return redirect("quiz:dashboard")

    total_questions = Question.objects.active().count()
    total_exams = Exam.objects.filter(is_published=True).count()
    total_tracks = ExamTrack.objects.filter(is_active=True).count()
    total_students = User.objects.count()
    total_study_plans = StudyPlan.objects.count()

    context = {
        "testimonials": Testimonial.objects.filter(
            is_approved=True,
            is_featured=True,
        ).order_by("-created_at")[:6],
        "total_questions": total_questions,
        "total_exams": total_exams,
        "total_tracks": total_tracks,
        "total_students": total_students,
        "total_study_plans": total_study_plans,
        "courses": Course.objects.filter(
            is_published=True,
            is_public=True,
        ).order_by("-created_at")[:HOMEPAGE_LIMIT],
        "exam_tracks": ExamTrack.objects.filter(
            is_active=True,
        ).order_by("-created_at")[:HOMEPAGE_LIMIT],
        "latest_exams": Exam.objects.filter(
            is_published=True,
        ).select_related("organization").order_by("-created_at")[:HOMEPAGE_LIMIT],
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
    if request.method == "POST":
        Feedback.objects.create(
            user=request.user,
            email=request.user.email,
            message=request.POST.get("message"),
        )
        return render(request, "pages/feedback.html", {"success": True})

    return render(request, "pages/feedback.html")


@login_required
def submit_testimonial(request):
    if request.method == "POST":
        form = TestimonialForm(request.POST)
        if form.is_valid():
            testimonial = form.save(commit=False)
            testimonial.user = request.user
            testimonial.name = request.user.get_full_name() or request.user.username
            testimonial.is_approved = False
            testimonial.save()
            messages.success(
                request,
                "Thank you! Your testimonial has been submitted for review.",
            )
            return redirect(request.POST.get("next") or "/")

        return redirect(request.POST.get("next") or "/")

    return redirect("/")
