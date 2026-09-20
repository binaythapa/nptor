from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.views.decorators.http import require_GET


_PRACTICE_SESSION_KEYS = (
    "p_seen",
    "p_qid",
    "p_filters",
    "p_total",
    "p_anon_count",
    "course_practice_initialized",
    "course_practice_count",
    "course_practice_lesson_id",
)


@require_GET
@login_required
def restart_course_practice(request, course_slug, lesson_id):
    """Start a clean practice attempt for a specific course lesson."""
    for key in _PRACTICE_SESSION_KEYS:
        request.session.pop(key, None)

    query = urlencode({
        "course": course_slug,
        "lesson": lesson_id,
    })
    return redirect(f"/quiz/practice/?{query}")
