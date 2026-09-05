from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from quiz.models import LearningActivityDismissal


@login_required
@require_POST
def remove_learning_activity(request, resource_type, resource_id):
    """Hide one learning resource from this student's Learning Activity list."""
    valid_types = {
        LearningActivityDismissal.RESOURCE_COURSE,
        LearningActivityDismissal.RESOURCE_EXAM,
        LearningActivityDismissal.RESOURCE_TRACK,
    }
    if resource_type not in valid_types:
        messages.error(request, "Invalid learning activity resource.")
        return redirect("quiz:learning_hub")

    LearningActivityDismissal.objects.get_or_create(
        user=request.user,
        resource_type=resource_type,
        resource_id=resource_id,
    )
    messages.success(request, "The selected item was removed from Learning Activity.")
    return redirect("quiz:learning_hub")
