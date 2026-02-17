import logging

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import JsonResponse, HttpResponse
from django.utils import timezone

from courses.models import (
    Course,
    CourseSection,
    Lesson,
    LessonProgress,
    CourseEnrollment,
    CourseSubscription
)

from quiz.models import Exam
from quiz.services.access import user_has_course_access

from courses.services.progress import (
    get_course_progress,
    get_next_lesson,
    is_lesson_unlocked,
    get_resume_lesson,
)

from courses.services.certificates import issue_certificate_if_eligible
from courses.services.certificate_pdf import generate_certificate_pdf
from courses.utils import youtube_embed_url


logger = logging.getLogger(__name__)



@login_required
def course_list(request):
    courses = Course.objects.filter(is_published=True)
    return render(request, "courses/instructor/course_list.html", {"courses": courses})






@login_required
def course_detail(request, slug):

    course = get_object_or_404(
        Course,
        slug=slug,
        is_deleted=False
    )

    # ------------------------------------------------
    # Check if user is course owner / admin
    # ------------------------------------------------
    is_owner = False

    if request.user.is_superuser:
        is_owner = True

    elif course.created_by == request.user:
        is_owner = True

    elif (
        hasattr(request.user, "organization")
        and request.user.organization
        and course.organization == request.user.organization
    ):
        is_owner = True

    # ------------------------------------------------
    # Access Control
    # ------------------------------------------------
    if not course.is_published and not is_owner:
        raise Http404("Course not available")

    # ------------------------------------------------
    # Enrollment Logic
    # ------------------------------------------------

    # If instructor → treat as enrolled automatically
    if is_owner:
        is_enrolled = True
    else:
        is_enrolled = CourseEnrollment.objects.filter(
            user=request.user,
            course=course,
            is_active=True
        ).exists()

    # ------------------------------------------------
    # Progress Logic
    # ------------------------------------------------

    completed = total = progress = 0

    if is_enrolled:
        completed, total, progress = get_course_progress(request.user, course)

    return render(request, "courses/student/course_detail.html", {
        "course": course,
        "is_enrolled": is_enrolled,
        "completed": completed,
        "total": total,
        "progress": progress,
        "is_owner": is_owner,
    })




##########################################################




from courses.models import (
    Course,
    CourseSection,
    Lesson,
    LessonProgress,
    CourseEnrollment,
    CourseCertificate,
)

from courses.services.progress import (
    get_course_progress,
    is_lesson_unlocked,
    get_resume_lesson,
)




# -------------------------------------------------
# YouTube embed helper (SINGLE SOURCE OF TRUTH)
# -------------------------------------------------
from urllib.parse import urlparse, parse_qs

def youtube_embed(url):
    if not url:
        return None

    from urllib.parse import urlparse, parse_qs
    parsed = urlparse(url)

    if "youtu.be" in parsed.netloc:
        video_id = parsed.path.strip("/")
        return f"https://www.youtube-nocookie.com/embed/{video_id}"

    if "youtube.com" in parsed.netloc:
        if parsed.path == "/watch":
            qs = parse_qs(parsed.query)
            video_id = qs.get("v", [None])[0]
            if video_id:
                return f"https://www.youtube-nocookie.com/embed/{video_id}"

        if parsed.path.startswith("/shorts/"):
            video_id = parsed.path.split("/shorts/")[-1]
            return f"https://www.youtube-nocookie.com/embed/{video_id}"

    return None



# -------------------------------------------------
# COURSE LEARN
# -------------------------------------------------
@login_required
@ensure_csrf_cookie
def course_learn(request, slug, lesson_id=None):

    # clear course exam context once user is back
    request.session.pop("course_exam_context", None)

    # -------------------------------------------------
    # 1️⃣ Course (remove is_published=True)
    # -------------------------------------------------
    course = get_object_or_404(
        Course,
        slug=slug,
        is_deleted=False
    )

    # -------------------------------------------------
    # 2️⃣ Owner / Admin Check
    # -------------------------------------------------
    is_owner = False

    if request.user.is_superuser:
        is_owner = True

    elif course.created_by == request.user:
        is_owner = True

    elif (
        hasattr(request.user, "organization")
        and request.user.organization
        and course.organization == request.user.organization
    ):
        is_owner = True

    # -------------------------------------------------
    # 3️⃣ Access Control
    # -------------------------------------------------
    if not course.is_published and not is_owner:
        raise Http404("Course not available")

    # -------------------------------------------------
    # 4️⃣ Enrollment Logic
    # -------------------------------------------------
    if is_owner:
        is_enrolled = True
    else:
        is_enrolled = CourseEnrollment.objects.filter(
            user=request.user,
            course=course,
            is_active=True
        ).exists()

    if not is_enrolled:
        return redirect("courses:course_detail", slug=slug)

    # -------------------------------------------------
    # 5️⃣ Curriculum
    # -------------------------------------------------
    sections = course.sections.filter(
        is_deleted=False
    ).prefetch_related("lessons")

    # -------------------------------------------------
    # 6️⃣ Lesson Selection
    # -------------------------------------------------
    if lesson_id:
        lesson = get_object_or_404(
            Lesson,
            id=lesson_id,
            section__course=course
        )
    else:
        lesson = get_resume_lesson(request.user, course)
        if not lesson:
            return redirect("courses:course_detail", slug=slug)

    # -------------------------------------------------
    # 7️⃣ Sequential Lock
    # -------------------------------------------------
    if not is_lesson_unlocked(request.user, lesson):
        return redirect("courses:course_learn", slug=slug)

    # -------------------------------------------------
    # 8️⃣ Progress Row
    # -------------------------------------------------
    lesson_progress, _ = LessonProgress.objects.get_or_create(
        user=request.user,
        lesson=lesson
    )

    # -------------------------------------------------
    # 9️⃣ Course Progress
    # -------------------------------------------------
    completed, total, progress = get_course_progress(
        request.user,
        course
    )

    # -------------------------------------------------
    # 🔟 Certificate
    # -------------------------------------------------
    certificate = issue_certificate_if_eligible(
        request.user,
        course,
        progress
    )

    # -------------------------------------------------
    # 1️⃣1️⃣ Celebration (once)
    # -------------------------------------------------
    celebration_key = f"celebrated_course_{course.id}"
    show_celebration = False

    if progress >= 100 and certificate and not request.session.get(celebration_key):
        show_celebration = True
        request.session[celebration_key] = True

    # -------------------------------------------------
    # 1️⃣2️⃣ Completed lessons
    # -------------------------------------------------
    completed_lesson_ids = set(
        LessonProgress.objects.filter(
            user=request.user,
            lesson__section__course=course,
            completed=True
        ).values_list("lesson_id", flat=True)
    )

    # -------------------------------------------------
    # 1️⃣3️⃣ Video embed
    # -------------------------------------------------
    video_embed_url = None
    if lesson.lesson_type == "video":
        video_embed_url = youtube_embed(lesson.video_url)

    # -------------------------------------------------
    # 1️⃣4️⃣ Next lesson
    # -------------------------------------------------
    next_lesson = get_next_lesson(lesson)

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
            "is_owner": is_owner,
        }
    )


# -------------------------------------------------
# MARK ARTICLE COMPLETED
# -------------------------------------------------
@login_required
@require_POST
def mark_lesson_completed(request, slug, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)

    if lesson.section.course.slug != slug:
        return redirect("courses:course_learn", slug=slug)

    lp, _ = LessonProgress.objects.get_or_create(
        user=request.user,
        lesson=lesson
    )

    lp.completed = True
    lp.completed_at = timezone.now()
    lp.save()

    return redirect("courses:course_learn", slug=slug)




# -------------------------------------------------
# CERTIFICATE DOWNLOAD
# -------------------------------------------------
@login_required
def download_certificate_pdf(request, slug):
    course = get_object_or_404(Course, slug=slug)
    certificate = get_object_or_404(
        CourseCertificate,
        user=request.user,
        course=course
    )

    pdf_bytes = generate_certificate_pdf(
        request.user,
        course,
        certificate
    )

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="{course.slug}-certificate.pdf"'
    )
    return response



@login_required
@require_POST
def track_video_progress(request):
    try:
        lesson_id = request.POST.get("lesson_id")
        watched = request.POST.get("watched", "0")
        duration = request.POST.get("duration", "0")

        if not lesson_id:
            return JsonResponse(
                {"error": "lesson_id missing"},
                status=400
            )

        try:
            watched = int(watched)
            duration = int(duration)
        except ValueError:
            return JsonResponse(
                {"error": "Invalid watched or duration"},
                status=400
            )

        lesson = get_object_or_404(Lesson, id=lesson_id)

        lp, _ = LessonProgress.objects.get_or_create(
            user=request.user,
            lesson=lesson
        )

        lp.video_seconds_watched = max(
            lp.video_seconds_watched or 0,
            watched
        )
        lp.video_duration = max(
            lp.video_duration or 0,
            duration
        )

        if lp.can_mark_complete():
            lp.mark_completed()

        lp.save()

        return JsonResponse({"completed": lp.completed})

    except Exception:
        logger.exception("TRACK VIDEO PROGRESS FAILED")
        return JsonResponse(
            {"error": "Internal server error"},
            status=500
        )



@login_required
def enroll_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    # Check access
    has_access = (
        StudentCourseSubscription.objects.filter(
            user=request.user, course=course, is_active=True
        ).exists()
        or
        CourseAssignment.objects.filter(
            student=request.user, course=course
        ).exists()
    )

    if not has_access:
        return HttpResponseForbidden()

    CourseEnrollment.objects.get_or_create(
        user=request.user,
        course=course
    )

    return redirect("course_detail", course_id=course.id)






@login_required
@require_POST
def subscribe_course(request, course_id):
    course = get_object_or_404(
        Course,
        id=course_id,
        is_published=True
    )

    # Create or reactivate subscription
    sub, created = CourseSubscription.objects.get_or_create(
        user=request.user,
        course=course,
        defaults={
            "is_active": True,
            "source": "quiz",   # important
        }
    )

    if not created and not sub.is_active:
        sub.is_active = True
        sub.save(update_fields=["is_active"])

    return redirect("quiz:exam_list")
