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