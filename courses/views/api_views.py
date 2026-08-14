import json

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Max
from django.http import (
    HttpResponseBadRequest,
    HttpResponseForbidden,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from courses.models import (
    Course,
    CourseSection,
    Lesson,
)

from courses.services.permissions import (
    can_edit_course,
)


# ============================================================
# EDIT LESSON
# ============================================================

@login_required
@require_POST
def edit_lesson(request):

    lesson_id = request.POST.get("lesson_id")
    title = request.POST.get("title", "").strip()

    if not lesson_id:
        return HttpResponseBadRequest(
            "Invalid request."
        )

    if not title:
        return HttpResponseBadRequest(
            "Lesson title cannot be empty."
        )

    lesson = get_object_or_404(
        Lesson.objects.select_related(
            "section__course"
        ),
        id=lesson_id,
    )

    course = lesson.section.course

    if not can_edit_course(
        request.user,
        course,
    ):
        return HttpResponseForbidden(
            "You are not allowed to edit this lesson."
        )

    with transaction.atomic():

        lesson.title = title

        lesson.save(
            update_fields=["title"]
        )

    lessons = (
        lesson.section.lessons
        .order_by("order")
    )

    return render(
        request,
        "courses/instructor/partials/lesson_list.html",
        {
            "lessons": lessons,
            "section": lesson.section,
        },
    )


# ============================================================
# CREATE SECTION
# ============================================================

@login_required
@require_POST
def create_section(request):

    course_id = request.POST.get(
        "course_id"
    )

    title = request.POST.get(
        "title",
        "",
    ).strip()

    if not course_id:
        return HttpResponseBadRequest(
            "Invalid course."
        )

    if not title:
        return HttpResponseBadRequest(
            "Section title cannot be empty."
        )

    course = get_object_or_404(
        Course.objects.select_related(
            "created_by",
            "organization",
        ),
        id=course_id,
    )

    if not can_edit_course(
        request.user,
        course,
    ):
        return HttpResponseForbidden(
            "You are not allowed to edit this course."
        )

    with transaction.atomic():

        max_order = (
            CourseSection.objects
            .filter(course=course)
            .aggregate(
                max_order=Max("order")
            )["max_order"]
            or 0
        )

        CourseSection.objects.create(
            course=course,
            title=title,
            order=max_order + 1,
        )

    sections = (
        course.sections
        .prefetch_related("lessons")
        .order_by("order")
    )

    return render(
        request,
        "courses/instructor/partials/section_list.html",
        {
            "sections": sections,
            "course": course,
        },
    )



  


# ============================================================
# DELETE SECTION
# ============================================================

@login_required
@require_POST
def delete_section(
    request,
    section_id,
):

    section = get_object_or_404(
        CourseSection.objects.select_related(
            "course"
        ),
        id=section_id,
    )

    course = section.course

    if not can_edit_course(
        request.user,
        course,
    ):
        return HttpResponseForbidden(
            "You are not allowed to edit this course."
        )

    with transaction.atomic():

        section.delete()

        remaining = list(
            CourseSection.objects
            .filter(course=course)
            .order_by("order")
        )

        # Temporary values prevent unique-order collisions.
        for index, sec in enumerate(
            remaining,
            start=1,
        ):
            sec.order = 1000 + index

            sec.save(
                update_fields=["order"]
            )

        # Final order.
        for index, sec in enumerate(
            remaining,
            start=1,
        ):
            sec.order = index

            sec.save(
                update_fields=["order"]
            )

    updated_sections = (
        course.sections
        .prefetch_related("lessons")
        .order_by("order")
    )

    return render(
        request,
        "courses/instructor/partials/section_list.html",
        {
            "sections": updated_sections,
        },
    )


# ============================================================
# CREATE LESSON
# ============================================================

@login_required
@require_POST
def create_lesson(request):

    section_id = request.POST.get("section_id")
    title = request.POST.get("title", "").strip()

    if not section_id:
        return HttpResponseBadRequest(
            "Section is required."
        )

    if not title:
        return HttpResponseBadRequest(
            "Lesson title is required."
        )

    section = get_object_or_404(
        CourseSection.objects.select_related("course"),
        id=section_id,
    )

    course = section.course

    if not can_edit_course(
        request.user,
        course,
    ):
        return HttpResponseForbidden(
            "You are not allowed to edit this course."
        )

    try:

        with transaction.atomic():

            max_order = (
                Lesson.objects
                .filter(section=section)
                .aggregate(
                    max_order=Max("order")
                )["max_order"]
                or 0
            )

            lesson = Lesson(
                section=section,
                title=title,
                lesson_type=Lesson.TYPE_ARTICLE,
                order=max_order + 1,
            )

            lesson.save()

    except Exception as exc:

        return HttpResponseBadRequest(
            str(exc)
        )

    lessons = (
        section.lessons
        .order_by("order")
    )

    return render(
        request,
        "courses/instructor/partials/lesson_list.html",
        {
            "lessons": lessons,
            "section": section,
        },
    )

# ============================================================
# DELETE LESSON
# ============================================================

@login_required
@require_POST
def delete_lesson(
    request,
    lesson_id,
):

    lesson = get_object_or_404(
        Lesson.objects.select_related(
            "section__course"
        ),
        id=lesson_id,
    )

    section = lesson.section

    course = section.course

    if not can_edit_course(
        request.user,
        course,
    ):
        return HttpResponseForbidden(
            "You are not allowed to edit this lesson."
        )

    with transaction.atomic():

        lesson.delete()

        remaining = list(
            Lesson.objects
            .filter(section=section)
            .order_by("order")
        )

        # Temporary values.
        for index, item in enumerate(
            remaining,
            start=1,
        ):
            item.order = 1000 + index

            item.save(
                update_fields=["order"]
            )

        # Final order.
        for index, item in enumerate(
            remaining,
            start=1,
        ):
            item.order = index

            item.save(
                update_fields=["order"]
            )

    updated_lessons = (
        section.lessons
        .order_by("order")
    )

    return render(
        request,
        "courses/instructor/partials/lesson_list.html",
        {
            "section": section,
            "lessons": updated_lessons,
        },
    )


# ============================================================
# UPDATE SECTION / LESSON ORDER
# ============================================================

@login_required
@require_POST
def update_order(request):

    try:

        data = json.loads(
            request.body
        )

        items = data.get(
            "items",
            [],
        )

        if not isinstance(items, list):
            return HttpResponseBadRequest(
                "Invalid items."
            )

        with transaction.atomic():

            objects = []

            # ------------------------------------------------
            # Validate everything first
            # ------------------------------------------------

            for item in items:

                item_type = item.get(
                    "type"
                )

                item_id = item.get(
                    "id"
                )

                if item_type == "section":

                    obj = (
                        CourseSection.objects
                        .select_for_update()
                        .select_related("course")
                        .get(id=item_id)
                    )

                    course = obj.course

                elif item_type == "lesson":

                    obj = (
                        Lesson.objects
                        .select_for_update()
                        .select_related(
                            "section__course"
                        )
                        .get(id=item_id)
                    )

                    course = obj.section.course

                else:

                    raise ValueError(
                        "Invalid item type."
                    )

                if not can_edit_course(
                    request.user,
                    course,
                ):
                    return HttpResponseForbidden(
                        "You are not allowed to reorder this course."
                    )

                objects.append(
                    (
                        item,
                        obj,
                    )
                )

            # ------------------------------------------------
            # Temporary order
            # ------------------------------------------------

            for index, (
                item,
                obj,
            ) in enumerate(
                objects,
                start=1,
            ):

                obj.order = 1000 + index

                obj.save(
                    update_fields=["order"]
                )

            # ------------------------------------------------
            # Final order
            # ------------------------------------------------

            for item, obj in objects:

                new_order = item.get(
                    "order"
                )

                if new_order is None:
                    raise ValueError(
                        "Missing order."
                    )

                obj.order = int(
                    new_order
                )

                obj.save(
                    update_fields=["order"]
                )

        return JsonResponse(
            {
                "success": True,
            }
        )

    except (
        CourseSection.DoesNotExist,
        Lesson.DoesNotExist,
    ):

        return JsonResponse(
            {
                "error": "Object not found."
            },
            status=404,
        )

    except (
        ValueError,
        TypeError,
        json.JSONDecodeError,
    ) as exc:

        return JsonResponse(
            {
                "error": str(exc),
            },
            status=400,
        )

    except Exception as exc:

        return JsonResponse(
            {
                "error": str(exc),
            },
            status=400,
        )