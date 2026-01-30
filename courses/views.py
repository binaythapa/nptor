from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from .models import Course, CourseSection, Lesson, LessonProgress, CourseEnrollment
from quiz.models import Exam

from quiz.services.access import user_has_course_access
from courses.services.progress import *
from courses.services.certificates import issue_certificate_if_eligible
from courses.services.certificate_pdf import generate_certificate_pdf
from courses.services.progress import get_next_lesson
from courses.utils import youtube_embed_url
from courses.models import LessonProgress
from django.views.decorators.csrf import ensure_csrf_cookie


@login_required
def course_list(request):
    courses = Course.objects.filter(is_published=True)
    return render(request, "courses/course_list.html", {"courses": courses})

@login_required
def course_detail(request, slug):
    course = get_object_or_404(Course, slug=slug, is_published=True)

    is_enrolled = CourseEnrollment.objects.filter(
        user=request.user,
        course=course,
        is_active=True
    ).exists()

    completed, total, progress = get_course_progress(request.user, course)

    return render(request, "courses/course_detail.html", {
        "course": course,
        "is_enrolled": is_enrolled,
        "completed": completed,
        "total": total,
        "progress": progress,
    })



##########################################################


from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponse
from django.utils import timezone

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

from courses.services.certificates import issue_certificate_if_eligible
from courses.services.certificate_pdf import generate_certificate_pdf


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

    # 1️⃣ Course
    course = get_object_or_404(Course, slug=slug, is_published=True)
   

    # 2️⃣ Curriculum
    sections = course.sections.prefetch_related("lessons")

    

    # 3️⃣ Lesson selection
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

    # 4️⃣ Sequential lock
    if not is_lesson_unlocked(request.user, lesson):
        return redirect("courses:course_learn", slug=slug)

    # 5️⃣ Progress row
    lesson_progress, _ = LessonProgress.objects.get_or_create(
        user=request.user,
        lesson=lesson
    )

    # 6️⃣ Course progress
    completed, total, progress = get_course_progress(
        request.user,
        course
    )

    # 7️⃣ Certificate
    certificate = issue_certificate_if_eligible(
        request.user,
        course,
        progress
    )

    # 8️⃣ Celebration (once)
    celebration_key = f"celebrated_course_{course.id}"
    show_celebration = False
    if progress == 100 and certificate and not request.session.get(celebration_key):
        show_celebration = True
        request.session[celebration_key] = True

    # 9️⃣ Completed lessons
    completed_lesson_ids = set(
        LessonProgress.objects.filter(
            user=request.user,
            lesson__section__course=course,
            completed=True
        ).values_list("lesson_id", flat=True)
    )

    # 🔟 Video embed
    video_embed_url = None
    if lesson.lesson_type == "video":
        video_embed_url = youtube_embed(lesson.video_url)

    # ✅ correct
    next_lesson = get_next_lesson(lesson)

    return render(
        request,
        "courses/course_player.html",
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
    print("🔥 track_video_progress HIT")

    lesson_id = request.POST.get("lesson_id")
    watched = int(request.POST.get("watched", 0))
    duration = int(request.POST.get("duration", 0))

    print("DATA:", lesson_id, watched, duration)

    lp, _ = LessonProgress.objects.get_or_create(
        user=request.user,
        lesson_id=lesson_id
    )

    lp.video_seconds_watched = max(lp.video_seconds_watched, watched)
    lp.video_duration = max(lp.video_duration, duration)

    if lp.can_mark_complete():
        lp.mark_completed()

    lp.save()

    return JsonResponse({"completed": lp.completed})

