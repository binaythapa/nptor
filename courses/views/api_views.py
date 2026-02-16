from django.http import JsonResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.db import models, transaction
from django.db.models import Max
import json

from courses.models import Course, CourseSection, Lesson
from courses.services.permissions import can_edit_course


# -------------------------------------------------
# EDIT LESSON
# -------------------------------------------------
@login_required
@require_POST
def edit_lesson(request):
    lesson_id = request.POST.get("lesson_id")
    title = request.POST.get("title")

    lesson = get_object_or_404(Lesson, id=lesson_id)

    if not can_edit_course(request.user, lesson.section.course):
        return HttpResponseForbidden()

    lesson.title = title
    lesson.save(update_fields=["title"])

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


# -------------------------------------------------
# CREATE SECTION
# -------------------------------------------------
@login_required
@require_POST
def create_section(request):

    course_id = request.POST.get("course_id")
    title = request.POST.get("title")

    course = get_object_or_404(Course, id=course_id)

    if not can_edit_course(request.user, course):
        return HttpResponseForbidden()

    max_order = CourseSection.objects.filter(
        course=course,
        is_deleted=False
    ).aggregate(models.Max("order"))["order__max"] or 0

    CourseSection.objects.create(
        course=course,
        title=title,
        order=max_order + 1
    )

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
@login_required
@require_POST
def delete_section(request, section_id):

    section = get_object_or_404(CourseSection, id=section_id)

    if not can_edit_course(request.user, section.course):
        return HttpResponseForbidden()

    section.is_deleted = True
    section.save(update_fields=["is_deleted"])

    remaining = (
        section.course.sections
        .filter(is_deleted=False)
        .order_by("order")
    )

    for index, sec in enumerate(remaining, start=1):
        sec.order = index
        sec.save(update_fields=["order"])

    return render(
        request,
        "courses/instructor/partials/section_list.html",
        {"sections": remaining}
    )


# -------------------------------------------------
# CREATE LESSON
# -------------------------------------------------
@login_required
@require_POST
def create_lesson(request):
    section_id = request.POST.get("section_id")
    title = request.POST.get("title")
    lesson_type = request.POST.get("lesson_type")

    if not section_id or not title or not lesson_type:
        return HttpResponseBadRequest("Missing required fields")

    section = get_object_or_404(CourseSection, id=section_id)

    if not can_edit_course(request.user, section.course):
        return HttpResponseForbidden()

    max_order = Lesson.objects.filter(
        section=section,
        is_deleted=False
    ).aggregate(
        Max("order")
    )["order__max"] or 0

    Lesson.objects.create(
        section=section,
        title=title,
        lesson_type=lesson_type,
        order=max_order + 1
    )

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
@login_required
@require_POST
def delete_lesson(request, lesson_id):

    lesson = get_object_or_404(Lesson, id=lesson_id)

    if not can_edit_course(request.user, lesson.section.course):
        return HttpResponseForbidden()

    section = lesson.section

    lesson.delete()

    return render(
        request,
        "courses/instructor/partials/lesson_list.html",
        {
            "section": section
        }
    )



# -------------------------------------------------
# UPDATE ORDER (Drag & Drop)
# -------------------------------------------------
@login_required
@require_POST
def update_order(request):
    try:
        data = json.loads(request.body)
        items = data.get("items", [])

        with transaction.atomic():
            for item in items:
                item_type = item.get("type")
                item_id = item.get("id")
                order = item.get("order")

                if item_type == "section":
                    obj = CourseSection.objects.get(id=item_id)

                    if not can_edit_course(request.user, obj.course):
                        return HttpResponseForbidden()

                    obj.order = order
                    obj.save(update_fields=["order"])

                elif item_type == "lesson":
                    obj = Lesson.objects.get(id=item_id)

                    if not can_edit_course(request.user, obj.section.course):
                        return HttpResponseForbidden()

                    obj.order = order
                    obj.save(update_fields=["order"])

        return JsonResponse({"success": True})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)
