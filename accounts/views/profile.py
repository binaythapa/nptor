from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from organizations.models import OrganizationAccountRequest, OrganizationMember, OrganizationStudent


@login_required
def profile(request):
    if request.method == "POST":
        new_username = request.POST.get("username")
        if new_username:
            request.user.username = new_username
            request.user.save()
            messages.success(request, "Profile updated.")

    memberships = list(
        OrganizationMember.objects
        .filter(user=request.user)
        .select_related("organization")
        .order_by("organization__name")
    )
    student_profiles = {
        student.organization_id: student
        for student in OrganizationStudent.objects
        .filter(user=request.user)
        .select_related("organization")
    }
    for membership in memberships:
        membership.student_profile = student_profiles.get(membership.organization_id)

    organization_request = OrganizationAccountRequest.objects.filter(
        user=request.user
    ).order_by("-created_at").first()

    return render(
        request,
        "quiz/student/profile.html",
        {
            "user": request.user,
            "memberships": memberships,
            "organization_request": organization_request,
        },
    )
