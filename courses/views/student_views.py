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
# COURSE DETAIL / PREVIEW
# ============================================================

@login_required
def course_detail(request, slug):
    """
    Course detail / preview page.

    Course owners/admins may preview private courses. An assigned
    organization student may access an organization-assigned course
    without purchasing a student subscription.
    """

    course = get_object_or_404(
        Course.objects.select_related(
            "created_by",
            "organization",
        ),
        slug=slug,
    )

    is_course_owner = course.created_by_id == request.user.id
    is_admin = request.user.is_staff or request.user.is_superuser

    is_publicly_available = (
        course.approval_status == Course.APPROVAL_APPROVED
        and course.is_published
        and course.is_public
    )

    has_course_access = AccessService.has_course_access(
        request.user,
        course,
    )

    if not (
        is_course_owner
        or is_admin
        or is_publicly_available
        or has_course_access
    ):
        from django.http import Http404
        raise Http404("Course not found.")

    is_preview = (
        is_course_owner
        or is_admin
    ) and not is_publicly_available

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
            "is_course_owner": is_course_owner,
            "is_admin": is_admin,
            "is_publicly_available": is_publicly_available,
            "is_preview": is_preview,
        },
    )


# ============================================================
# YOUTUBE EMBED HELPER
# ============================================================

def youtube_embed(url):
    """Convert supported YouTube URLs into an embedded URL."""
    if not url:
        return None

    from urllib.parse import urlparse, parse_qs

    parsed = urlparse(url)

    if "youtu.be" in parsed.netloc:
        video_id = parsed.path.strip("/")
        if video_id:
            return f"https://www.youtube-nocookie.com/embed/{video_id}"

    if "youtube.com" in parsed.netloc:
        if parsed.path == "/watch":
            qs = parse_qs(parsed.query)
            video_id = qs.get("v", [None])[0]
            if video_id:
                return f"https://www.youtube-nocookie.com/embed/{video_id}"

        if parsed.path.startswith("/shorts/"):
            video_id = parsed.path.split("/shorts/")[-1]
            if video_id:
                return f"https://www.youtube-nocookie.com/embed/{video_id}"

    return None


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

    Normal public learners and students with organization assignment access
    can use the player. Course owners/admins can preview private courses.
    """

    request.session.pop("course_exam_context", None)

    course = get_object_or_404(
        Course.objects.select_related(
            "created_by",
            "organization",
        ),
        slug=slug,
    )

    is_course_owner = course.created_by_id == request.user.id
    is_admin = request.user.is_staff or request.user.is_superuser

    is_publicly_available = (
        course.approval_status == Course.APPROVAL_APPROVED
        and course.is_published
        and course.is_public
    )

    preview_requested = request.GET.get("preview") == "1"
    is_preview = (
        preview_requested
        and (is_course_owner or is_admin)
    )

    # The wrapper already checks access, but the view must also allow the
    # assigned organization learner through its own legacy security gate.
    has_course_access = AccessService.has_course_access(
        request.user,
        course,
    )

    if not (
        is_preview
        or is_publicly_available
        or has_course_access
    ):
        from django.http import Http404
        raise Http404("Course not found.")

    sections = (
        course.sections
        .prefetch_related("lessons")
        .order_by("order")
    )

    if lesson_id:
        lesson = get_object_or_404(
            Lesson,
            id=lesson_id,
            section__course=course,
        )
    elif is_preview:
        lesson = (
            Lesson.objects
            .filter(section__course=course)
            .select_related("section")
            .order_by("section__order", "order")
            .first()
        )

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
                    "is_publicly_available": is_publicly_available,
                },
            )
    else:
        lesson = get_resume_lesson(request.user, course)
        if not lesson:
            return redirect("courses:course_detail", slug=slug)

    if not is_preview:
        if not is_lesson_unlocked(request.user, lesson):
            return redirect("courses:course_learn", slug=slug)

    if is_preview:
        lesson_progress = None
    else:
        lesson_progress, _ = LessonProgress.objects.get_or_create(
            user=request.user,
            lesson=lesson,
        )

    if is_preview:
        total = Lesson.objects.filter(section__course=course).count()
        completed = 0
        progress = 0
    else:
        completed, total, progress = get_course_progress(
            request.user,
            course,
        )

    if is_preview:
        certificate = None
        certificate_created = False
    else:
        certificate, certificate_created = issue_certificate_if_eligible(
            request.user,
            course,
            progress,
        )

    celebration_key = f"celebrated_course_{course.id}"
    show_celebration = False

    if (
        not is_preview
        and progress >= 100
        and certificate
        and not request.session.get(celebration_key)
    ):
        show_celebration = True
        request.session[celebration_key] = True

    if is_preview:
        completed_lesson_ids = set()
    else:
        completed_lesson_ids = set(
            LessonProgress.objects.filter(
                user=request.user,
                lesson__section__course=course,
                completed=True,
            ).values_list("lesson_id", flat=True)
        )

    video_embed_url = None
    if lesson and lesson.lesson_type == "video":
        video_embed_url = youtube_embed(lesson.video_url)

    next_lesson = get_next_lesson(lesson) if lesson else None

    from pages.services.testimonials import get_testimonial_context

    if is_preview:
        testimonial_context = {}
    else:
        testimonial_context = get_testimonial_context(
            request.user,
            course=course,
            trigger=certificate_created,
        )

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
            "is_preview": is_preview,
            "is_course_owner": is_course_owner,
            "is_admin": is_admin,
            "is_publicly_available": is_publicly_available,
            **testimonial_context,
        },
    )


# ============================================================
# MARK LESSON COMPLETED
# ============================================================

@login_required
@require_POST
def mark_lesson_completed(request, slug, lesson_id):
    """Mark a lesson as completed."""
    lesson = get_object_or_404(Lesson, id=lesson_id)

    if lesson.section.course.slug != slug:
        return redirect("courses:course_learn", slug=slug)

    course = get_object_or_404(public_courses(), slug=slug)

    if lesson.section.course_id != course.id:
        return HttpResponseForbidden("Invalid course lesson.")

    lp, _ = LessonProgress.objects.get_or_create(
        user=request.user,
        lesson=lesson,
    )
    lp.completed = True
    lp.completed_at = timezone.now()
    lp.save()

    return redirect("courses:course_learn", slug=slug)


# ============================================================
# CERTIFICATE DOWNLOAD
# ============================================================

@login_required
def download_certificate_pdf(request, slug):
    """Download a certificate for a publicly available course."""
    course = get_object_or_404(public_courses(), slug=slug)
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

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="{course.slug}-certificate.pdf"'
    )
    return response


# ============================================================
# VIDEO PROGRESS
# ============================================================

@login_required
@require_POST
def track_video_progress(request):
    try:
        lesson_id = request.POST.get("lesson_id")
        watched = request.POST.get("watched", "0")
        duration = request.POST.get("duration", "0")

        if not lesson_id:
            return JsonResponse({"error": "lesson_id missing"}, status=400)

        try:
            watched = int(watched)
            duration = int(duration)
        except ValueError:
            return JsonResponse(
                {"error": "Invalid watched or duration"},
                status=400,
            )

        lesson = get_object_or_404(Lesson, id=lesson_id)
        course = lesson.section.course

        if not public_courses().filter(id=course.id).exists():
            return JsonResponse(
                {"error": "Course is not available."},
                status=403,
            )

        lp, _ = LessonProgress.objects.get_or_create(
            user=request.user,
            lesson=lesson,
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

        return JsonResponse({"completed": lp.completed})

    except Exception:
        logger.exception("TRACK VIDEO PROGRESS FAILED")
        return JsonResponse(
            {"error": "Internal server error"},
            status=500,
        )


# ============================================================
# ENROLL COURSE
# ============================================================

@login_required
def enroll_course(request, course_id):
    """
    Enroll a user in a publicly available course after verifying actual
    ResourceAccess. Enrollment and access remain separate concerns.
    """
    course = get_object_or_404(public_courses(), id=course_id)

    has_access = AccessService.has_access(
        user=request.user,
        resource_type=ResourceAccess.RESOURCE_COURSE,
        resource=course,
    )

    if not has_access:
        has_active_plans = course.subscription_plans.filter(
            is_active=True
        ).exists()

        if not has_active_plans:
            has_access = True
        else:
            return HttpResponseForbidden(
                "You do not have access to this course."
            )

    CourseEnrollment.objects.get_or_create(
        user=request.user,
        course=course,
    )

    return redirect("courses:course_detail", slug=course.slug)


# ============================================================
# SUBSCRIBE COURSE
# ============================================================

@login_required
@require_POST
def subscribe_course(request, course_id):
    """Create a user subscription for a publicly available course."""
    course = get_object_or_404(public_courses(), id=course_id)

    plans = (
        course.subscription_plans
        .filter(is_active=True)
        .order_by("price", "id")
    )

    if not plans.exists():
        CourseEnrollment.objects.get_or_create(
            user=request.user,
            course=course,
        )
        return redirect("courses:course_detail", slug=course.slug)

    plan_id = request.POST.get("plan_id")

    if plan_id:
        plan = get_object_or_404(
            SubscriptionPlan,
            id=plan_id,
            is_active=True,
        )
        if not plans.filter(id=plan.id).exists():
            return HttpResponseForbidden(
                "Selected subscription plan is not available for this course."
            )
    else:
        if plans.count() == 1:
            plan = plans.first()
        else:
            return HttpResponse(
                "Please select a subscription plan.",
                status=400,
            )

    starts_at = timezone.now()
    expires_at = None

    if plan.duration_days is not None:
        expires_at = starts_at + timezone.timedelta(
            days=plan.duration_days
        )

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

    entitlement = SubscriptionEntitlement.objects.create(
        subscription=subscription,
        resource_type=SubscriptionEntitlement.RESOURCE_COURSE,
        course=course,
        is_active=True,
    )

    AccessService.grant_from_entitlement(
        user=request.user,
        entitlement=entitlement,
        source=ResourceAccess.SOURCE_INDIVIDUAL,
    )

    CourseEnrollment.objects.get_or_create(
        user=request.user,
        course=course,
    )

    return redirect("courses:course_detail", slug=course.slug)
