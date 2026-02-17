from django.http import JsonResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.db import models, transaction
from django.db.models import Max
import json

from courses.models import Course, CourseSection, Lesson
from courses.services.permissions import can_edit_course


from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponseForbidden, HttpResponseBadRequest
from django.db import transaction


# -------------------------------------------------
# EDIT LESSON (HTMX INLINE TITLE UPDATE)
# -------------------------------------------------
@login_required
@require_POST
def edit_lesson(request):

    lesson_id = request.POST.get("lesson_id")
    title = request.POST.get("title", "").strip()

    if not lesson_id:
        return HttpResponseBadRequest("Invalid request.")

    lesson = get_object_or_404(
        Lesson.objects.select_related("section__course"),
        id=lesson_id,
        is_deleted=False
    )

    course = lesson.section.course

    # 🔐 STRICT ACCESS CONTROL
    if request.user.is_superuser:
        pass

    elif course.created_by == request.user:
        pass

    elif (
        hasattr(request.user, "organization")
        and request.user.organization
        and course.organization == request.user.organization
    ):
        pass

    else:
        return HttpResponseForbidden("You are not allowed to edit this lesson.")

    # 🛑 Validate title
    if not title:
        return HttpResponseBadRequest("Lesson title cannot be empty.")

    # 💾 Atomic save
    with transaction.atomic():
        lesson.title = title
        lesson.save(update_fields=["title"])

    # 🔄 Refresh lesson list
    lessons = (
        lesson.section.lessons
        .filter(is_deleted=False)
        .order_by("order")
    )

    return render(
        request,
        "courses/instructor/partials/lesson_list.html",
        {
            "lessons": lessons,
            "section": lesson.section
        }
    )

from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponseForbidden, HttpResponseBadRequest
from django.db import transaction
from django.db.models import Max


# -------------------------------------------------
# CREATE SECTION (HTMX)
# -------------------------------------------------
@login_required
@require_POST
def create_section(request):

    course_id = request.POST.get("course_id")
    title = request.POST.get("title", "").strip()

    if not course_id:
        return HttpResponseBadRequest("Invalid course.")

    if not title:
        return HttpResponseBadRequest("Section title cannot be empty.")

    course = get_object_or_404(
        Course.objects.select_related("created_by", "organization"),
        id=course_id,
        is_deleted=False
    )

    # 🔐 STRICT ACCESS CONTROL
    if not can_edit_course(request.user, course):
        return HttpResponseForbidden("You are not allowed to edit this course.")

    # 🛡 Atomic to prevent duplicate order issues
    with transaction.atomic():

        max_order = (
            CourseSection.objects
            .filter(course=course, is_deleted=False)
            .aggregate(Max("order"))["order__max"] or 0
        )

        CourseSection.objects.create(
            course=course,
            title=title,
            order=max_order + 1
        )

    # 🔄 Refresh sections
    sections = (
        course.sections
        .filter(is_deleted=False)
        .prefetch_related("lessons")
        .order_by("order")
    )

    return render(
        request,
        "courses/instructor/partials/section_list.html",
        {"sections": sections}
    )

# -------------------------------------------------
# DELETE SECTION (SOFT DELETE)
# -------------------------------------------------
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponseForbidden
from django.db import transaction
from django.db.models import F


# -------------------------------------------------
# DELETE SECTION (HTMX)
# -------------------------------------------------
@login_required
@require_POST
def delete_section(request, section_id):

    section = get_object_or_404(
        CourseSection.objects.select_related("course"),
        id=section_id,
        is_deleted=False
    )

    # 🔐 STRICT PERMISSION CHECK
    if not can_edit_course(request.user, section.course):
        return HttpResponseForbidden("You are not allowed to edit this course.")

    with transaction.atomic():

        # 1️⃣ Soft delete
        section.is_deleted = True
        section.save(update_fields=["is_deleted"])

        # 2️⃣ Reorder safely (no collision)
        remaining = (
            CourseSection.objects
            .filter(course=section.course, is_deleted=False)
            .order_by("order")
        )

        # Step A: Move to temp space to avoid unique conflict
        for sec in remaining:
            sec.order = sec.order + 1000
            sec.save(update_fields=["order"])

        # Step B: Assign clean sequential order
        for index, sec in enumerate(remaining, start=1):
            sec.order = index
            sec.save(update_fields=["order"])

    # 3️⃣ Reload sections
    updated_sections = (
        section.course.sections
        .filter(is_deleted=False)
        .prefetch_related("lessons")
        .order_by("order")
    )

    return render(
        request,
        "courses/instructor/partials/section_list.html",
        {"sections": updated_sections}
    )


# -------------------------------------------------
# CREATE LESSON
# -------------------------------------------------
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponseBadRequest, HttpResponseForbidden
from django.db import transaction
from django.db.models import Max


# -------------------------------------------------
# CREATE LESSON (HTMX SAFE)
# -------------------------------------------------
@login_required
@require_POST
def create_lesson(request):

    section_id = request.POST.get("section_id")
    title = request.POST.get("title")
    lesson_type = request.POST.get("lesson_type")

    if not section_id or not title or not lesson_type:
        return HttpResponseBadRequest("Missing required fields")

    section = get_object_or_404(
        CourseSection.objects.select_related("course"),
        id=section_id,
        is_deleted=False
    )

    # 🔐 Strict permission
    if not can_edit_course(request.user, section.course):
        return HttpResponseForbidden("You are not allowed to edit this course.")

    with transaction.atomic():

        # 🔒 Lock existing lessons in this section
        existing_lessons = (
            Lesson.objects
            .select_for_update()
            .filter(section=section, is_deleted=False)
        )

        max_order = existing_lessons.aggregate(
            Max("order")
        )["order__max"] or 0

        Lesson.objects.create(
            section=section,
            title=title,
            lesson_type=lesson_type,
            order=max_order + 1
        )

    # Reload clean list
    lessons = (
        section.lessons
        .filter(is_deleted=False)
        .order_by("order")
    )

    return render(
        request,
        "courses/instructor/partials/lesson_list.html",
        {
            "lessons": lessons,
            "section": section
        }
    )


# -------------------------------------------------
# DELETE LESSON (SOFT DELETE)
# -------------------------------------------------
from django.db import transaction

@login_required
@require_POST
def delete_lesson(request, lesson_id):

    lesson = get_object_or_404(
        Lesson.objects.select_related("section__course"),
        id=lesson_id,
        is_deleted=False
    )

    if not can_edit_course(request.user, lesson.section.course):
        return HttpResponseForbidden("Not allowed")

    section = lesson.section

    with transaction.atomic():

        # 🔒 lock all lessons in section
        lessons = (
            Lesson.objects
            .select_for_update()
            .filter(section=section, is_deleted=False)
            .order_by("order")
        )

        # Soft delete
        lesson.is_deleted = True
        lesson.save(update_fields=["is_deleted"])

        # Reindex remaining
        remaining = lessons.exclude(id=lesson.id)

        for index, l in enumerate(remaining, start=1):
            if l.order != index:
                l.order = index
                l.save(update_fields=["order"])

    updated_lessons = (
        section.lessons
        .filter(is_deleted=False)
        .order_by("order")
    )

    return render(
        request,
        "courses/instructor/partials/lesson_list.html",
        {
            "section": section,
            "lessons": updated_lessons
        }
    )


import json
from django.db import transaction
from django.http import JsonResponse, HttpResponseForbidden

@login_required
@require_POST
def update_order(request):

    try:
        data = json.loads(request.body)
        items = data.get("items", [])

        with transaction.atomic():

            # Step 1️⃣ Move everything to safe temporary space
            for item in items:

                if item["type"] == "section":
                    obj = CourseSection.objects.select_for_update().get(
                        id=item["id"]
                    )

                    if not can_edit_course(request.user, obj.course):
                        return HttpResponseForbidden()

                    obj.order += 1000
                    obj.save(update_fields=["order"])

                elif item["type"] == "lesson":
                    obj = Lesson.objects.select_for_update().get(
                        id=item["id"]
                    )

                    if not can_edit_course(request.user, obj.section.course):
                        return HttpResponseForbidden()

                    obj.order += 1000
                    obj.save(update_fields=["order"])

            # Step 2️⃣ Apply final clean order
            for item in items:

                if item["type"] == "section":
                    obj = CourseSection.objects.get(id=item["id"])
                    obj.order = item["order"]
                    obj.save(update_fields=["order"])

                elif item["type"] == "lesson":
                    obj = Lesson.objects.get(id=item["id"])
                    obj.order = item["order"]
                    obj.save(update_fields=["order"])

        return JsonResponse({"success": True})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)
