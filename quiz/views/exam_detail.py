from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


@login_required
def exam_detail(request, exam_id):
    """Reject standalone student exam pages; exams are entered via courses/tracks."""
    return redirect("quiz:exam_list")
