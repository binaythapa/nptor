import logging

from django.shortcuts import (
    render,
    get_object_or_404,
    redirect,
)
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import (
    JsonResponse,
    HttpResponse,
    HttpResponseForbidden,
)
from django.utils import timezone

from courses.models import (
    Course,
    CourseSection,
    Lesson,
    LessonProgress,
    CourseEnrollment,
    CourseSubscription,
    CourseCertificate,
)

from quiz.models import Exam
from quiz.services.access import user_has_course_access

from courses.services.progress import (
    get_course_progress,
    get_next_lesson,
    is_lesson_unlocked,
    get_resume_lesson,
)

from courses.services.certificates import (
    issue_certificate_if_eligible,
)

from courses.services.certificate_pdf import (
    generate_certificate_pdf,
)

from courses.utils import youtube_embed_url


logger = logging.getLogger(__name__)


# ============================================================
# PUBLIC COURSE QUERYSET
# ============================================================

def public_courses():
    """
    Return only courses that are officially available
    on the public website.

    A course must satisfy ALL THREE conditions:

        1. approval_status = APPROVED
        2. is_published = True
        3. is_public = True

    This is the final public security gate.
    """

    return Course.objects.filter(
        approval_status=Course.APPROVAL_APPROVED,
        is_published=True,
        is_public=True,
    )


# ============================================================
# COURSE LIST
# ============================================================

@login_required
def course_list(request):
    """
    Display publicly available courses.

    Unapproved, unpublished, private, draft, pending,
    rejected and changes-required courses are excluded.
    """

    courses = public_courses()

    return render(
        request,
        "courses/student/course_list.html",
        {
            "courses": courses,
        },
    )


# ============================================================
# COURSE DETAIL
# ============================================================

@login_required
def course_detail(request, slug):
    """
    Display a publicly available course.

    Direct URL access is also protected by the same
    approval/publish/public rules.
    """

    course = get_object_or_404(
        public_courses(),
        slug=slug,
    )

    is_enrolled = CourseEnrollment.objects.filter(
        user=request.user,
        course=course,
        is_active=True,
    ).exists()

    completed, total, progress = get_course_progress(
        request.user,
        course,
    )

    return render(
        request,
        "courses/student/course_detail.html",
        {
            "course": course,
            "is_enrolled": is_enrolled,
            "completed": completed,
            "total": total,
            "progress": progress,
        },
    )


# ============================================================
# YOUTUBE EMBED HELPER
# ============================================================

def youtube_embed(url):
    """
    Convert supported YouTube URLs into an embedded URL.
    """

    if not url:
        return None

    from urllib.parse import (
        urlparse,
        parse_qs,
    )

    parsed = urlparse(url)

    # --------------------------------------------------------
    # youtu.be/<id>
    # --------------------------------------------------------

    if "youtu.be" in parsed.netloc:

        video_id = parsed.path.strip("/")

        if video_id:
            return (
                "https://www.youtube-nocookie.com/"
                f"embed/{video_id}"
            )

    # --------------------------------------------------------
    # youtube.com
    # --------------------------------------------------------

    if "youtube.com" in parsed.netloc:

        # /watch?v=<id>
        if parsed.path == "/watch":

            qs = parse_qs(parsed.query)

            video_id = qs.get(
                "v",
                [None],
            )[0]

            if video_id:
                return (
                    "https://www.youtube-nocookie.com/"
                    f"embed/{video_id}"
                )

        # /shorts/<id>
        if parsed.path.startswith("/shorts/"):

            video_id = parsed.path.split(
                "/shorts/"
            )[-1]

            if video_id:
                return (
                    "https://www.youtube-nocookie.com/"
                    f"embed/{video_id}"
                )

    return None


# ============================================================
# COURSE LEARN
# ============================================================

@login_required
@ensure_csrf_cookie
def course_learn(
    request,
    slug,
    lesson_id=None,
):
    """
    Course learning/player page.

    Only an approved, published and public course
    can be accessed.
    """

    # --------------------------------------------------------
    # CLEAR COURSE EXAM CONTEXT
    # --------------------------------------------------------

    request.session.pop(
        "course_exam_context",
        None,
    )

    # --------------------------------------------------------
    # COURSE SECURITY CHECK
    # --------------------------------------------------------

    course = get_object_or_404(
        public_courses(),
        slug=slug,
    )

    # --------------------------------------------------------
    # CURRICULUM
    # --------------------------------------------------------

    sections = (
        course.sections
        .prefetch_related("lessons")
        .order_by("order")
    )

    # --------------------------------------------------------
    # LESSON SELECTION
    # --------------------------------------------------------

    if lesson_id:

        lesson = get_object_or_404(
            Lesson,
            id=lesson_id,
            section__course=course,
        )

    else:

        lesson = get_resume_lesson(
            request.user,
            course,
        )

        if not lesson:

            return redirect(
                "courses:course_detail",
                slug=slug,
            )

    # --------------------------------------------------------
    # SEQUENTIAL LOCK
    # --------------------------------------------------------

    if not is_lesson_unlocked(
        request.user,
        lesson,
    ):

        return redirect(
            "courses:course_learn",
            slug=slug,
        )

    # --------------------------------------------------------
    # LESSON PROGRESS
    # --------------------------------------------------------

    lesson_progress, _ = (
        LessonProgress.objects.get_or_create(
            user=request.user,
            lesson=lesson,
        )
    )

    # --------------------------------------------------------
    # COURSE PROGRESS
    # --------------------------------------------------------

    completed, total, progress = (
        get_course_progress(
            request.user,
            course,
        )
    )

    # --------------------------------------------------------
    # CERTIFICATE
    # --------------------------------------------------------

    certificate, certificate_created = (
        issue_certificate_if_eligible(
            request.user,
            course,
            progress,
        )
    )

    # --------------------------------------------------------
    # CELEBRATION
    # --------------------------------------------------------

    celebration_key = (
        f"celebrated_course_{course.id}"
    )

    show_celebration = False

    if (
        progress >= 100
        and certificate
        and not request.session.get(
            celebration_key
        )
    ):

        show_celebration = True

        request.session[
            celebration_key
        ] = True

    # --------------------------------------------------------
    # COMPLETED LESSONS
    # --------------------------------------------------------

    completed_lesson_ids = set(
        LessonProgress.objects.filter(
            user=request.user,
            lesson__section__course=course,
            completed=True,
        ).values_list(
            "lesson_id",
            flat=True,
        )
    )

    # --------------------------------------------------------
    # VIDEO
    # --------------------------------------------------------

    video_embed_url = None

    if lesson.lesson_type == "video":

        video_embed_url = youtube_embed(
            lesson.video_url
        )

    # --------------------------------------------------------
    # NEXT LESSON
    # --------------------------------------------------------

    next_lesson = get_next_lesson(
        lesson
    )

    # --------------------------------------------------------
    # TESTIMONIAL
    # --------------------------------------------------------

    from pages.services.testimonials import (
        get_testimonial_context,
    )

    testimonial_context = (
        get_testimonial_context(
            request.user,
            course=course,
            trigger=certificate_created,
        )
    )

    # --------------------------------------------------------
    # RENDER
    # --------------------------------------------------------

    return render(
        request,
        "courses/student/course_player.html",
        {
            "course": course,
            "sections": sections,
            "lesson": lesson,
            "lesson_progress": lesson_progress,
            "next_lesson": next_lesson,
            "completed": completed,
            "total": total,
            "progress": progress,
            "completed_lesson_ids": completed_lesson_ids,
            "certificate": certificate,
            "show_celebration": show_celebration,
            "video_embed_url": video_embed_url,
            **testimonial_context,
        },
    )


# ============================================================
# MARK LESSON COMPLETED
# ============================================================

@login_required
@require_POST
def mark_lesson_completed(
    request,
    slug,
    lesson_id,
):
    """
    Mark a lesson as completed.

    The lesson must belong to the requested course.
    """

    lesson = get_object_or_404(
        Lesson,
        id=lesson_id,
    )

    if lesson.section.course.slug != slug:

        return redirect(
            "courses:course_learn",
            slug=slug,
        )

    # --------------------------------------------------------
    # Make sure the course is publicly available
    # --------------------------------------------------------

    course = get_object_or_404(
        public_courses(),
        slug=slug,
    )

    # --------------------------------------------------------
    # Verify lesson belongs to this course
    # --------------------------------------------------------

    if lesson.section.course_id != course.id:

        return HttpResponseForbidden(
            "Invalid course lesson."
        )

    # --------------------------------------------------------
    # Progress
    # --------------------------------------------------------

    lp, _ = LessonProgress.objects.get_or_create(
        user=request.user,
        lesson=lesson,
    )

    lp.completed = True
    lp.completed_at = timezone.now()

    lp.save()

    return redirect(
        "courses:course_learn",
        slug=slug,
    )


# ============================================================
# CERTIFICATE DOWNLOAD
# ============================================================

@login_required
def download_certificate_pdf(
    request,
    slug,
):
    """
    Download a certificate for a publicly available course.
    """

    course = get_object_or_404(
        public_courses(),
        slug=slug,
    )

    certificate = get_object_or_404(
        CourseCertificate,
        user=request.user,
        course=course,
    )

    pdf_bytes = generate_certificate_pdf(
        request.user,
        course,
        certificate,
    )

    response = HttpResponse(
        pdf_bytes,
        content_type="application/pdf",
    )

    response[
        "Content-Disposition"
    ] = (
        f'attachment; '
        f'filename="{course.slug}-certificate.pdf"'
    )

    return response


# ============================================================
# VIDEO PROGRESS
# ============================================================

@login_required
@require_POST
def track_video_progress(request):

    try:

        lesson_id = request.POST.get(
            "lesson_id"
        )

        watched = request.POST.get(
            "watched",
            "0",
        )

        duration = request.POST.get(
            "duration",
            "0",
        )

        if not lesson_id:

            return JsonResponse(
                {
                    "error": "lesson_id missing"
                },
                status=400,
            )

        # ----------------------------------------------------
        # Convert values
        # ----------------------------------------------------

        try:

            watched = int(watched)
            duration = int(duration)

        except ValueError:

            return JsonResponse(
                {
                    "error": (
                        "Invalid watched or duration"
                    )
                },
                status=400,
            )

        # ----------------------------------------------------
        # Lesson
        # ----------------------------------------------------

        lesson = get_object_or_404(
            Lesson,
            id=lesson_id,
        )

        course = lesson.section.course

        # ----------------------------------------------------
        # Course security
        # ----------------------------------------------------

        if not public_courses().filter(
            id=course.id
        ).exists():

            return JsonResponse(
                {
                    "error": (
                        "Course is not available."
                    )
                },
                status=403,
            )

        # ----------------------------------------------------
        # Progress
        # ----------------------------------------------------

        lp, _ = (
            LessonProgress.objects.get_or_create(
                user=request.user,
                lesson=lesson,
            )
        )

        lp.video_seconds_watched = max(
            lp.video_seconds_watched or 0,
            watched,
        )

        lp.video_duration = max(
            lp.video_duration or 0,
            duration,
        )

        if lp.can_mark_complete():
            lp.mark_completed()

        lp.save()

        return JsonResponse(
            {
                "completed": lp.completed
            }
        )

    except Exception:

        logger.exception(
            "TRACK VIDEO PROGRESS FAILED"
        )

        return JsonResponse(
            {
                "error": "Internal server error"
            },
            status=500,
        )


# ============================================================
# ENROLL COURSE
# ============================================================

@login_required
def enroll_course(
    request,
    course_id,
):
    """
    Enroll a user in a publicly available course
    after access has been granted.
    """

    course = get_object_or_404(
        public_courses(),
        id=course_id,
    )

    # --------------------------------------------------------
    # Check access
    # --------------------------------------------------------

    has_access = (
        CourseSubscription.objects.filter(
            user=request.user,
            course=course,
            is_active=True,
        ).exists()
    )

    if not has_access:

        return HttpResponseForbidden(
            "You do not have access to this course."
        )

    # --------------------------------------------------------
    # Enrollment
    # --------------------------------------------------------

    CourseEnrollment.objects.get_or_create(
        user=request.user,
        course=course,
    )

    return redirect(
        "courses:course_detail",
        slug=course.slug,
    )


# ============================================================
# SUBSCRIBE COURSE
# ============================================================

@login_required
@require_POST
def subscribe_course(
    request,
    course_id,
):
    """
    Subscribe to a publicly available course.

    Only approved + published + public courses
    can be subscribed to.
    """

    course = get_object_or_404(
        public_courses(),
        id=course_id,
    )

    # --------------------------------------------------------
    # Create or reactivate subscription
    # --------------------------------------------------------

    sub, created = (
        CourseSubscription.objects.get_or_create(
            user=request.user,
            course=course,
            defaults={
                "is_active": True,
                "source": "quiz",
            },
        )
    )

    if not created and not sub.is_active:

        sub.is_active = True

        sub.save(
            update_fields=[
                "is_active"
            ]
        )

    return redirect(
        "quiz:exam_list"
    )