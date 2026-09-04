from functools import wraps

from django.core.exceptions import PermissionDenied
from django.http import Http404

from courses.models import Course, Lesson
from courses.services.permissions import can_preview_course
from subscriptions.services.access_service import AccessService
from subscriptions.services.plan_service import get_plan_for_course


def _course_requires_paid_access(course):
    plan = get_plan_for_course(course, None)
    return plan is not None and plan.price > 0


def _user_has_course_access(user, course):
    if not _course_requires_paid_access(course):
        return True

    return AccessService.has_access(
        student=user,
        resource_type=AccessService.RESOURCE_COURSE,
        resource=course,
    )


def course_detail_access_required(view_func):
    """Allow public courses or authorized course previews only."""

    @wraps(view_func)
    def _wrapped(request, slug, *args, **kwargs):
        course = Course.objects.filter(slug=slug).first()
        if course is None:
            raise Http404("Course not found.")

        is_publicly_available = (
            course.approval_status == Course.APPROVAL_APPROVED
            and course.is_published
            and course.is_public
        )

        if is_publicly_available or can_preview_course(request.user, course):
            return view_func(request, slug, *args, **kwargs)

        raise Http404("Course not found.")

    return _wrapped


def course_learning_access_required(view_func):
    """Enforce access to course learning content, including public previews."""

    @wraps(view_func)
    def _wrapped(request, slug, *args, **kwargs):
        course = Course.objects.filter(slug=slug).first()
        if course is None:
            raise Http404("Course not found.")

        is_publicly_available = (
            course.approval_status == Course.APPROVAL_APPROVED
            and course.is_published
            and course.is_public
        )
        preview_requested = request.GET.get("preview") == "1"

        if preview_requested:
            if can_preview_course(request.user, course):
                return view_func(request, slug, *args, **kwargs)
            if is_publicly_available:
                from courses.views.free_preview import course_free_preview
                return course_free_preview(request, slug, *args, **kwargs)

        if not is_publicly_available:
            raise Http404("Course not found.")

        if not _user_has_course_access(request.user, course):
            raise Http404("Course not found.")

        return view_func(request, slug, *args, **kwargs)

    return _wrapped


def course_entitlement_required(view_func):
    """Require actual access for non-preview course operations."""

    @wraps(view_func)
    def _wrapped(request, slug, *args, **kwargs):
        course = Course.objects.filter(slug=slug).first()
        if course is None:
            raise Http404("Course not found.")

        if not (
            course.approval_status == Course.APPROVAL_APPROVED
            and course.is_published
            and course.is_public
        ):
            raise Http404("Course not found.")

        if not _user_has_course_access(request.user, course):
            raise PermissionDenied("You do not have access to this course.")

        return view_func(request, slug, *args, **kwargs)

    return _wrapped


def lesson_course_access_required(view_func):
    """Require actual access to the course containing a lesson."""

    @wraps(view_func)
    def _wrapped(request, slug, lesson_id, *args, **kwargs):
        lesson = Lesson.objects.select_related("section__course").filter(
            id=lesson_id
        ).first()

        if lesson is None or lesson.section.course.slug != slug:
            raise Http404("Lesson not found.")

        course = lesson.section.course

        if not (
            course.approval_status == Course.APPROVAL_APPROVED
            and course.is_published
            and course.is_public
        ):
            raise Http404("Course not found.")

        if not _user_has_course_access(request.user, course):
            raise PermissionDenied("You do not have access to this course.")

        return view_func(request, slug, lesson_id, *args, **kwargs)

    return _wrapped


def video_progress_access_required(view_func):
    """Require course access before recording video progress."""

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        lesson_id = request.POST.get("lesson_id")

        try:
            lesson_id = int(lesson_id)
        except (TypeError, ValueError):
            return view_func(request, *args, **kwargs)

        lesson = Lesson.objects.select_related("section__course").filter(
            id=lesson_id
        ).first()

        if lesson is None:
            return view_func(request, *args, **kwargs)

        course = lesson.section.course

        if not (
            course.approval_status == Course.APPROVAL_APPROVED
            and course.is_published
            and course.is_public
        ):
            return view_func(request, *args, **kwargs)

        if not _user_has_course_access(request.user, course):
            raise PermissionDenied("You do not have access to this course.")

        return view_func(request, *args, **kwargs)

    return _wrapped
