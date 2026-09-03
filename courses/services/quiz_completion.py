from courses.models import Course, Lesson, LessonProgress
from subscriptions.services.access_service import AccessService
from subscriptions.services.plan_service import get_plan_for_course


def _user_can_access_course(user, course):
    """Mirror the course learning authorization boundary."""
    if not (
        course.approval_status == Course.APPROVAL_APPROVED
        and course.is_published
        and course.is_public
    ):
        return False

    plan = get_plan_for_course(course, None)
    if plan is None or plan.price <= 0:
        return True

    return AccessService.has_access(
        student=user,
        resource_type=AccessService.RESOURCE_COURSE,
        resource=course,
    )


def handle_course_quiz_completion(request, user_exam, context):
    """
    Mark a course quiz lesson complete only when the attempt is
    genuinely associated with that lesson and the user can access
    its course.

    The session context is treated as untrusted input: callers must
    not be able to use an otherwise-valid exam attempt to complete
    an unrelated or inaccessible course lesson.
    """
    lesson_id = context.get("lesson_id")
    course_slug = context.get("course_slug")

    if not lesson_id or not course_slug:
        return

    try:
        lesson = (
            Lesson.objects
            .select_related("section__course")
            .get(
                id=lesson_id,
                lesson_type=Lesson.TYPE_QUIZ,
            )
        )
    except Lesson.DoesNotExist:
        return

    course = lesson.section.course

    if course.slug != course_slug:
        return

    if not lesson.exam_id or user_exam.exam_id != lesson.exam_id:
        return

    if not _user_can_access_course(request.user, course):
        return

    progress, _ = LessonProgress.objects.get_or_create(
        user=request.user,
        lesson=lesson,
    )

    if progress.completed:
        return

    mode = lesson.quiz_completion_mode

    completed = False
    if mode == "attempt":
        completed = True
    elif mode == "pass":
        completed = user_exam.passed is True
    elif mode == "score":
        completed = (
            user_exam.score is not None
            and user_exam.score >= lesson.quiz_min_score
        )

    if completed:
        progress.mark_completed()
