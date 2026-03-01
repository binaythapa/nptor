from django.shortcuts import render
from django.contrib.auth.decorators import login_required

def home(request):
    if request.user.is_authenticated:
        return redirect("quiz:dashboard")

    return render(request, "pages/home.html")


    return render(request, "pages/home.html")

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