import logging

from datetime import timedelta

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
    CourseCertificate,
)


from organizations.models import ResourceAccess


from subscriptions.models import (
    Subscription,
    SubscriptionEntitlement,
    SubscriptionPlan,
)


from subscriptions.services import AccessService


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
# ============================================================
# COURSE DETAIL / PREVIEW
# ============================================================

@login_required
def course_detail(request, slug):
    """
    Course detail / preview page.

    ACCESS RULES
    ------------

    1. Course developer/owner:
       Can preview the course at ANY development stage.

    2. Staff / superuser:
       Can preview any course.

    3. Normal users:
       Can only view courses that are:
           - approved
           - published
           - public

    IMPORTANT:
    This does NOT change public_courses().
    The public catalog and course player remain protected.
    """

    # --------------------------------------------------------
    # GET COURSE
    # --------------------------------------------------------

    course = get_object_or_404(
        Course.objects.select_related(
            "created_by",
            "organization",
        ),
        slug=slug,
    )

    # --------------------------------------------------------
    # COURSE DEVELOPER
    # --------------------------------------------------------

    is_course_owner = (
        course.created_by_id == request.user.id
    )

    # --------------------------------------------------------
    # ADMIN
    # --------------------------------------------------------

    is_admin = (
        request.user.is_staff
        or request.user.is_superuser
    )

    # --------------------------------------------------------
    # PUBLIC STATUS
    # --------------------------------------------------------

    is_publicly_available = (
        course.approval_status == Course.APPROVAL_APPROVED
        and course.is_published
        and course.is_public
    )

    # --------------------------------------------------------
    # ACCESS CONTROL
    # --------------------------------------------------------

    if not (
        is_course_owner
        or is_admin
        or is_publicly_available
    ):
        # Deliberately return 404 so private courses
        # are not exposed to unauthorized users.
        from django.http import Http404

        raise Http404("Course not found.")

    # --------------------------------------------------------
    # PREVIEW MODE
    # --------------------------------------------------------

    is_preview = (
        is_course_owner
        or is_admin
    ) and not is_publicly_available

    # --------------------------------------------------------
    # ENROLLMENT
    # --------------------------------------------------------

    is_enrolled = CourseEnrollment.objects.filter(
        user=request.user,
        course=course,
        is_active=True,
    ).exists()

    # --------------------------------------------------------
    # PROGRESS
    # --------------------------------------------------------

    completed, total, progress = get_course_progress(
        request.user,
        course,
    )

    # --------------------------------------------------------
    # RENDER
    # --------------------------------------------------------

    return render(
        request,
        "courses/student/course_detail.html",
        {
            "course": course,

            "is_enrolled": is_enrolled,

            "completed": completed,
            "total": total,
            "progress": progress,

            # Access information
            "is_course_owner": is_course_owner,
            "is_admin": is_admin,
            "is_publicly_available": is_publicly_available,

            # True when developer/admin is looking at
            # a course that isn't publicly available yet.
            "is_preview": is_preview,
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
# ============================================================
# COURSE LEARN / PREVIEW
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

    NORMAL MODE
    -----------
    Only approved + published + public courses.

    PREVIEW MODE
    ------------
    Course owner/developer or staff/superuser can preview
    a course before publication.

    Preview mode:
        - Can access draft courses
        - Can access unpublished courses
        - Can access private courses
        - Can open any lesson
        - Does NOT create lesson progress
        - Does NOT issue certificates
        - Does NOT update video progress
    """

    # --------------------------------------------------------
    # CLEAR COURSE EXAM CONTEXT
    # --------------------------------------------------------

    request.session.pop(
        "course_exam_context",
        None,
    )

    # --------------------------------------------------------
    # GET COURSE
    # --------------------------------------------------------

    course = get_object_or_404(
        Course.objects.select_related(
            "created_by",
            "organization",
        ),
        slug=slug,
    )

    # --------------------------------------------------------
    # USER PERMISSIONS
    # --------------------------------------------------------

    is_course_owner = (
        course.created_by_id == request.user.id
    )

    is_admin = (
        request.user.is_staff
        or request.user.is_superuser
    )

    # --------------------------------------------------------
    # PUBLIC STATUS
    # --------------------------------------------------------

    is_publicly_available = (
        course.approval_status
        == Course.APPROVAL_APPROVED
        and course.is_published
        and course.is_public
    )

    # --------------------------------------------------------
    # PREVIEW MODE
    # --------------------------------------------------------

    preview_requested = (
        request.GET.get("preview") == "1"
    )

    is_preview = (
        preview_requested
        and (
            is_course_owner
            or is_admin
        )
    )

    # --------------------------------------------------------
    # ACCESS CONTROL
    # --------------------------------------------------------

    if is_preview:
        # Developer/admin preview is allowed.
        pass

    elif not is_publicly_available:
        # Normal student access.
        from django.http import Http404

        raise Http404(
            "Course not found."
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

    elif is_preview:

        # ----------------------------------------------------
        # PREVIEW:
        # Open the first lesson instead of depending on
        # student progress/resume state.
        # ----------------------------------------------------

        lesson = (
            Lesson.objects
            .filter(
                section__course=course
            )
            .select_related("section")
            .order_by(
                "section__order",
                "order",
            )
            .first()
        )

        # ----------------------------------------------------
        # No lessons yet
        # ----------------------------------------------------

        if not lesson:

            return render(
                request,
                "courses/student/course_player.html",
                {
                    "course": course,
                    "sections": sections,
                    "lesson": None,
                    "lesson_progress": None,
                    "next_lesson": None,
                    "completed": 0,
                    "total": 0,
                    "progress": 0,
                    "completed_lesson_ids": set(),
                    "certificate": None,
                    "show_celebration": False,
                    "video_embed_url": None,
                    "is_preview": True,
                    "is_course_owner": is_course_owner,
                    "is_admin": is_admin,
                    "is_publicly_available": (
                        is_publicly_available
                    ),
                },
            )

    else:

        # ----------------------------------------------------
        # NORMAL STUDENT MODE:
        # Resume previous lesson.
        # ----------------------------------------------------

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
    #
    # Preview users can open ANY lesson.
    # Students still follow normal sequential locking.
    # --------------------------------------------------------

    if not is_preview:

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
    #
    # IMPORTANT:
    # Preview must not create student progress.
    # --------------------------------------------------------

    if is_preview:

        lesson_progress = None

    else:

        lesson_progress, _ = (
            LessonProgress.objects.get_or_create(
                user=request.user,
                lesson=lesson,
            )
        )

    # --------------------------------------------------------
    # COURSE PROGRESS
    # --------------------------------------------------------

    if is_preview:

        # Preview should not display the developer's
        # personal learning progress.

        total = (
            Lesson.objects
            .filter(
                section__course=course
            )
            .count()
        )

        completed = 0
        progress = 0

    else:

        completed, total, progress = (
            get_course_progress(
                request.user,
                course,
            )
        )

    # --------------------------------------------------------
    # CERTIFICATE
    # --------------------------------------------------------
    #
    # Never issue a certificate during preview.
    # --------------------------------------------------------

    if is_preview:

        certificate = None
        certificate_created = False

    else:

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
        not is_preview
        and progress >= 100
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

    if is_preview:

        completed_lesson_ids = set()

    else:

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

    if (
        lesson
        and lesson.lesson_type == "video"
    ):

        video_embed_url = youtube_embed(
            lesson.video_url
        )

    # --------------------------------------------------------
    # NEXT LESSON
    # --------------------------------------------------------

    if lesson:

        next_lesson = get_next_lesson(
            lesson
        )

    else:

        next_lesson = None

    # --------------------------------------------------------
    # TESTIMONIAL
    # --------------------------------------------------------

    from pages.services.testimonials import (
        get_testimonial_context,
    )

    if is_preview:

        testimonial_context = {}

    else:

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

            "completed_lesson_ids": (
                completed_lesson_ids
            ),

            "certificate": certificate,
            "show_celebration": (
                show_celebration
            ),

            "video_embed_url": (
                video_embed_url
            ),

            # ------------------------------------------------
            # PREVIEW CONTEXT
            # ------------------------------------------------

            "is_preview": is_preview,
            "is_course_owner": (
                is_course_owner
            ),
            "is_admin": is_admin,
            "is_publicly_available": (
                is_publicly_available
            ),

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
# ============================================================
# ENROLL COURSE
# ============================================================

@login_required
def enroll_course(
    request,
    course_id,
):
    """
    Enroll a user in a publicly available course after
    verifying actual ResourceAccess.

    Enrollment and access are intentionally separate:

        ResourceAccess = permission
        CourseEnrollment = learning relationship
    """

    course = get_object_or_404(
        public_courses(),
        id=course_id,
    )

    # --------------------------------------------------------
    # CHECK RESOURCE ACCESS
    # --------------------------------------------------------

    has_access = AccessService.has_access(
        user=request.user,
        resource_type=ResourceAccess.RESOURCE_COURSE,
        resource=course,
    )

    # --------------------------------------------------------
    # FREE PUBLIC COURSE
    # --------------------------------------------------------

    if not has_access:

        has_active_plans = (
            course.subscription_plans
            .filter(is_active=True)
            .exists()
        )

        # A public course with no active plans is free.
        if not has_active_plans:

            has_access = True

        else:

            return HttpResponseForbidden(
                "You do not have access to this course."
            )

    # --------------------------------------------------------
    # ENROLLMENT
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
    Create a user subscription for a course.

    New architecture:

        SubscriptionPlan
              ↓
        Subscription
              ↓
        SubscriptionEntitlement
              ↓
        ResourceAccess

    The course must be publicly available.

    If multiple active plans exist for the course, the request
    must provide:

        plan_id=<id>
    """

    # --------------------------------------------------------
    # COURSE
    # --------------------------------------------------------

    course = get_object_or_404(
        public_courses(),
        id=course_id,
    )

    # --------------------------------------------------------
    # AVAILABLE PLANS
    # --------------------------------------------------------

    plans = (
        course.subscription_plans
        .filter(is_active=True)
        .order_by("price", "id")
    )

    # --------------------------------------------------------
    # FREE COURSE
    # --------------------------------------------------------

    if not plans.exists():

        CourseEnrollment.objects.get_or_create(
            user=request.user,
            course=course,
        )

        return redirect(
            "courses:course_detail",
            slug=course.slug,
        )

    # --------------------------------------------------------
    # SELECT PLAN
    # --------------------------------------------------------

    plan_id = request.POST.get("plan_id")

    if plan_id:

        plan = get_object_or_404(
            SubscriptionPlan,
            id=plan_id,
            is_active=True,
        )

        if not plans.filter(
            id=plan.id
        ).exists():

            return HttpResponseForbidden(
                "Selected subscription plan is not available "
                "for this course."
            )

    else:

        # If there is exactly one plan, use it.
        if plans.count() == 1:

            plan = plans.first()

        else:

            return HttpResponse(
                "Please select a subscription plan.",
                status=400,
            )

    # --------------------------------------------------------
    # CALCULATE EXPIRATION
    # --------------------------------------------------------

    starts_at = timezone.now()

    expires_at = None

    if plan.duration_days is not None:

        expires_at = (
            starts_at
            + timezone.timedelta(
                days=plan.duration_days
            )
        )

    # --------------------------------------------------------
    # CREATE SUBSCRIPTION
    # --------------------------------------------------------

    subscription = Subscription.objects.create(
        plan=plan,
        user=request.user,
        starts_at=starts_at,
        expires_at=expires_at,
        amount=plan.price,
        currency=plan.currency,
        payment_status=(
            "not_required"
            if plan.price == 0
            else "pending"
        ),
        subscribed_by_admin=False,
    )

    # --------------------------------------------------------
    # CREATE ENTITLEMENT
    # --------------------------------------------------------

    entitlement = SubscriptionEntitlement.objects.create(
        subscription=subscription,
        resource_type=(
            SubscriptionEntitlement.RESOURCE_COURSE
        ),
        course=course,
        is_active=True,
    )

    # --------------------------------------------------------
    # GRANT ACTUAL USER ACCESS
    # --------------------------------------------------------

    AccessService.grant_from_entitlement(
        user=request.user,
        entitlement=entitlement,
        source=ResourceAccess.SOURCE_INDIVIDUAL,
    )

    # --------------------------------------------------------
    # ENROLL
    # --------------------------------------------------------

    CourseEnrollment.objects.get_or_create(
        user=request.user,
        course=course,
    )

    return redirect(
        "courses:course_detail",
        slug=course.slug,
    )