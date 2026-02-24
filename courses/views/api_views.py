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

@login_required
@require_POST
def edit_lesson(request):

    lesson_id = request.POST.get("lesson_id")
    title = request.POST.get("title", "").strip()

    if not lesson_id:
        return HttpResponseBadRequest("Invalid request.")

    lesson = get_object_or_404(
        Lesson.objects.select_related("section__course"),
        id=lesson_id
    )

    if not can_edit_course(request.user, lesson.section.course):
        return HttpResponseForbidden("You are not allowed to edit this lesson.")

    if not title:
        return HttpResponseBadRequest("Lesson title cannot be empty.")

    with transaction.atomic():
        lesson.title = title
        lesson.save(update_fields=["title"])

    lessons = (
        lesson.section.lessons
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
        id=course_id
    )

    if not can_edit_course(request.user, course):
        return HttpResponseForbidden("You are not allowed to edit this course.")

    with transaction.atomic():
        max_order = (
            CourseSection.objects
            .filter(course=course)
            .aggregate(Max("order"))["order__max"] or 0
        )

        CourseSection.objects.create(
            course=course,
            title=title,
            order=max_order + 1
        )

    sections = (
        course.sections
        .prefetch_related("lessons")
        .order_by("order")
    )

    return render(
        request,
        "courses/instructor/partials/section_list.html",
        {"sections": sections}
    )



from django.db import transaction

@login_required
@require_POST
def delete_section(request, section_id):

    section = get_object_or_404(
        CourseSection.objects.select_related("course"),
        id=section_id
    )

    if not can_edit_course(request.user, section.course):
        return HttpResponseForbidden()

    with transaction.atomic():

        course = section.course

        # 1️⃣ Delete first
        section.delete()

        # 2️⃣ Reorder safely (collision-proof)
        remaining = (
            CourseSection.objects
            .filter(course=course)
            .order_by("order")
        )

        # Move to safe temporary range
        for sec in remaining:
            sec.order += 1000
            sec.save(update_fields=["order"])

        # Assign clean sequence
        for index, sec in enumerate(remaining, start=1):
            sec.order = index
            sec.save(update_fields=["order"])

    updated_sections = (
        course.sections
        .prefetch_related("lessons")
        .order_by("order")
    )

    return render(
        request,
        "courses/instructor/partials/section_list.html",
        {"sections": updated_sections}
    )








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
        id=section_id
    )

    if not can_edit_course(request.user, section.course):
        return HttpResponseForbidden("You are not allowed to edit this course.")

    with transaction.atomic():
        max_order = (
            Lesson.objects
            .filter(section=section)
            .aggregate(Max("order"))["order__max"] or 0
        )

        Lesson.objects.create(
            section=section,
            title=title,
            lesson_type=lesson_type,
            order=max_order + 1
        )

    lessons = section.lessons.order_by("order")

    return render(
        request,
        "courses/instructor/partials/lesson_list.html",
        {
            "lessons": lessons,
            "section": section
        }
    )







from django.db import transaction

@login_required
@require_POST
def delete_lesson(request, lesson_id):

    lesson = get_object_or_404(
        Lesson.objects.select_related("section__course"),
        id=lesson_id
    )

    if not can_edit_course(request.user, lesson.section.course):
        return HttpResponseForbidden()

    with transaction.atomic():

        section = lesson.section

        # 1️⃣ Delete lesson first
        lesson.delete()

        # 2️⃣ Reorder safely
        remaining = (
            Lesson.objects
            .filter(section=section)
            .order_by("order")
        )

        # Move to safe temporary range
        for l in remaining:
            l.order += 1000
            l.save(update_fields=["order"])

        # Reindex cleanly
        for index, l in enumerate(remaining, start=1):
            l.order = index
            l.save(update_fields=["order"])

    updated_lessons = section.lessons.order_by("order")

    return render(
        request,
        "courses/instructor/partials/lesson_list.html",
        {
            "section": section,
            "lessons": updated_lessons
        }
    )







@login_required
@require_POST
def update_order(request):

    try:
        data = json.loads(request.body)
        items = data.get("items", [])

        with transaction.atomic():

            # Step 1️⃣ Move everything temporarily
            for item in items:

                if item["type"] == "section":
                    obj = CourseSection.objects.select_for_update().get(id=item["id"])

                    if not can_edit_course(request.user, obj.course):
                        return HttpResponseForbidden()

                elif item["type"] == "lesson":
                    obj = Lesson.objects.select_for_update().get(id=item["id"])

                    if not can_edit_course(request.user, obj.section.course):
                        return HttpResponseForbidden()

                obj.order += 1000
                obj.save(update_fields=["order"])

            # Step 2️⃣ Apply final order
            for item in items:

                if item["type"] == "section":
                    obj = CourseSection.objects.get(id=item["id"])
                else:
                    obj = Lesson.objects.get(id=item["id"])

                obj.order = item["order"]
                obj.save(update_fields=["order"])

        return JsonResponse({"success": True})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)