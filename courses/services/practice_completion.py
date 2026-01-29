from courses.models import LessonProgress

def track_practice_completion(request, lesson):
    key = f"practice_seen_lesson_{lesson.id}"
    seen = request.session.get(key, 0) + 1
    request.session[key] = seen

    # Threshold reached
    if lesson.practice_threshold and seen >= lesson.practice_threshold:
        lp, _ = LessonProgress.objects.get_or_create(
            user=request.user,
            lesson=lesson
        )
        lp.mark_completed()
        request.session[f"practice_done_{lesson.id}"] = True

    return seen
