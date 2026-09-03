from django.shortcuts import (
    render,
    get_object_or_404,
    redirect,
)
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.db import transaction
from django.db.models import Count, Prefetch
from django.contrib import messages

from courses.services.course_approval import (
    submit_course_for_review,
)

from courses.models import (
    Course,
    CourseSection,
    Lesson,
)

from courses.forms import (
    CourseForm,
    CourseSectionFormSet,
    LessonForm,
)

from courses.services.permissions import (
    can_edit_course,
    can_view_instructor_dashboard,
)

from courses.services.course_approval import (
    submit_course_for_review,
    publish_course,
    unpublish_course,
)


# ======================================================
# COURSE BUILDER
# ======================================================

@login_required
def course_builder(request, slug):

    course = get_object_or_404(
        Course,
        slug=slug
    )

    # --------------------------------------------------
    # PERMISSION
    # --------------------------------------------------

    if not can_edit_course(
        request.user,
        course
    ):
        return HttpResponseForbidden(
            "You are not allowed to edit this course."
        )

    # --------------------------------------------------
    # SECTIONS + LESSONS
    # --------------------------------------------------

    sections = (
        course.sections
        .prefetch_related(
            Prefetch(
                "lessons",
                queryset=Lesson.objects.order_by("order")
            )
        )
        .order_by("order")
    )

    return render(
        request,
        "courses/instructor/course_builder.html",
        {
            "course": course,
            "sections": sections,
        }
    )


# ======================================================
# SUBMIT COURSE FOR REVIEW
# ======================================================

@login_required
def submit_course_for_review_view(request, slug):
    """
    Instructor submits a course for administrator review.

    Allowed:

        DRAFT
        CHANGES_REQUIRED
        REJECTED

    Result:

        PENDING_REVIEW
    """

    # --------------------------------------------------
    # POST ONLY
    # --------------------------------------------------

    if request.method != "POST":

        return HttpResponseForbidden(
            "Invalid request method."
        )

    # --------------------------------------------------
    # LOAD COURSE
    # --------------------------------------------------

    course = get_object_or_404(
        Course,
        slug=slug
    )

    # --------------------------------------------------
    # SUBMIT
    # --------------------------------------------------

    try:

        submit_course_for_review(
            course=course,
            user=request.user,
        )

    except PermissionError as exc:

        return HttpResponseForbidden(
            str(exc)
        )

    except ValueError as exc:

        messages.error(
            request,
            str(exc)
        )

        return redirect(
            "courses:course_builder",
            slug=course.slug
        )

    # --------------------------------------------------
    # SUCCESS
    # --------------------------------------------------

    messages.success(
        request,
        (
            f'"{course.title}" has been submitted '
            "for administrator review."
        )
    )

    return redirect(
        "courses:course_builder",
        slug=course.slug
    )


# ======================================================
# PUBLISH / UNPUBLISH COURSE
# ======================================================
# ======================================================
# PUBLISH / UNPUBLISH COURSE
# ======================================================

@login_required
def toggle_publish_course(request, slug):
    """
    Allow an authorized course developer/instructor
    to publish or unpublish an approved course.

    Rules:

    APPROVED + unpublished
        -> Publish

    APPROVED + published
        -> Unpublish

    Any other approval state
        -> Publishing is not allowed
    """

    # --------------------------------------------------
    # POST ONLY
    # --------------------------------------------------

    if request.method != "POST":
        return HttpResponseForbidden(
            "POST request required."
        )

    # --------------------------------------------------
    # LOAD COURSE
    # --------------------------------------------------

    course = get_object_or_404(
        Course,
        slug=slug,
    )

    # --------------------------------------------------
    # PERMISSION
    # --------------------------------------------------

    if not can_edit_course(
        request.user,
        course,
    ):
        return HttpResponseForbidden(
            "You are not allowed to modify this course."
        )

    # --------------------------------------------------
    # APPROVAL CHECK
    # --------------------------------------------------

    if not course.is_approved():
        messages.error(
            request,
            "Only an approved course can be published."
        )

        return redirect(
            "courses:course_builder",
            slug=course.slug,
        )

    # --------------------------------------------------
    # PUBLISH / UNPUBLISH
    # --------------------------------------------------

    try:

        if course.is_published:

            unpublish_course(
                course=course,
                user=request.user,
            )

            messages.success(
                request,
                f'"{course.title}" has been unpublished.'
            )

        else:

            publish_course(
                course=course,
                user=request.user,
            )

            messages.success(
                request,
                f'"{course.title}" has been published.'
            )

    except PermissionError as exc:

        messages.error(
            request,
            str(exc),
        )

    except ValueError as exc:

        messages.error(
            request,
            str(exc),
        )

    # --------------------------------------------------
    # RETURN TO BUILDER
    # --------------------------------------------------

    return redirect(
        "courses:course_builder",
        slug=course.slug,
    )
# ======================================================
# INSTRUCTOR DASHBOARD
# ======================================================

@login_required
def instructor_dashboard(request):

    # --------------------------------------------------
    # ORGANIZATION VISIBILITY
    # --------------------------------------------------

    organization = getattr(
        request,
        "organization",
        None,
    )

    if organization and not can_view_instructor_dashboard(
        request.user,
        organization,
    ):
        return HttpResponseForbidden(
            "You are not allowed to view organization instructor data."
        )

    base_queryset = (
        Course.objects
        .select_related(
            "created_by",
            "organization",
            "reviewed_by",
        )
        .annotate(
            total_lessons=Count(
                "sections__lessons",
                distinct=True
            ),
            total_enrollments=Count(
                "enrollments",
                distinct=True
            ),
        )
        .order_by(
            "-created_at"
        )
    )

    # --------------------------------------------------
    # ORGANIZATION COURSES
    # --------------------------------------------------

    organization_courses = (
        base_queryset.none()
    )

    if organization:

        organization_courses = (
            base_queryset.filter(
                organization=organization
            )
        )

    # --------------------------------------------------
    # PLATFORM COURSES
    # --------------------------------------------------

    if request.user.is_superuser:

        admin_courses = (
            base_queryset.filter(
                owner_type=Course.OWNER_PLATFORM
            )
        )

    else:

        admin_courses = (
            base_queryset.none()
        )

    # --------------------------------------------------
    # PERSONAL COURSES
    # --------------------------------------------------

    my_courses = (
        base_queryset.filter(
            created_by=request.user
        )
    )

    # --------------------------------------------------
    # PENDING REVIEW COUNT
    # --------------------------------------------------

    pending_review_count = 0

    if request.user.is_superuser:

        pending_review_count = (
            Course.objects.filter(
                approval_status=(
                    Course.APPROVAL_PENDING
                )
            ).count()
        )

    # --------------------------------------------------
    # RESPONSE
    # --------------------------------------------------

    return render(
        request,
        "courses/instructor/dashboard.html",
        {
            "organization_courses":
                organization_courses,

            "admin_courses":
                admin_courses,

            "my_courses":
                my_courses,

            "pending_review_count":
                pending_review_count,
        }
    )


# ======================================================
# EDIT COURSE
# ======================================================

@login_required
def course_edit(request, slug):

    course = get_object_or_404(
        Course,
        slug=slug
    )

    # --------------------------------------------------
    # PERMISSION
    # --------------------------------------------------

    if not can_edit_course(
        request.user,
        course
    ):

        return HttpResponseForbidden(
            "You are not allowed to edit this course."
        )

    # --------------------------------------------------
    # POST
    # --------------------------------------------------

    if request.method == "POST":

        form = CourseForm(
            request.POST,
            request.FILES,
            instance=course
        )

        formset = CourseSectionFormSet(
            request.POST,
            instance=course,
            queryset=course.sections.order_by("order"),
            prefix="sections"
        )

        if (
            form.is_valid()
            and formset.is_valid()
        ):

            with transaction.atomic():

                course = form.save(
                    commit=False
                )

                # --------------------------------------
                # OWNERSHIP
                # --------------------------------------

                if request.user.is_superuser:

                    pass

                elif (
                    hasattr(
                        request,
                        "organization"
                    )
                    and request.organization
                ):

                    course.organization = (
                        request.organization
                    )

                    course.owner_type = (
                        Course.OWNER_ORGANIZATION
                    )

                else:

                    course.organization = None

                    course.owner_type = (
                        Course.OWNER_PLATFORM
                    )

                # --------------------------------------
                # SAVE COURSE
                # --------------------------------------

                course.save()

                form.save_m2m()

                # --------------------------------------
                # SAVE SECTIONS
                # --------------------------------------

                sections = (
                    formset.save(
                        commit=False
                    )
                )

                for section in sections:

                    section.course = course

                    section.save()

                # --------------------------------------
                # DELETE REMOVED SECTIONS
                # --------------------------------------

                for obj in (
                    formset.deleted_objects
                ):

                    obj.delete()

            return redirect(
                "courses:course_builder",
                slug=course.slug
            )

    # --------------------------------------------------
    # GET
    # --------------------------------------------------

    else:

        form = CourseForm(
            instance=course
        )

        formset = CourseSectionFormSet(
            instance=course,
            queryset=course.sections.order_by("order"),
            prefix="sections"
        )

    # --------------------------------------------------
    # RESPONSE
    # --------------------------------------------------

    return render(
        request,
        "courses/instructor/course_edit.html",
        {
            "form": form,
            "formset": formset,
            "course": course,
        }
    )


# ======================================================
# DELETE COURSE
# ======================================================

@login_required
def course_delete(request, slug):

    course = get_object_or_404(
        Course,
        slug=slug
    )

    # --------------------------------------------------
    # PERMISSION
    # --------------------------------------------------

    if not can_edit_course(
        request.user,
        course
    ):

        return HttpResponseForbidden(
            "You are not allowed to delete this course."
        )

    # --------------------------------------------------
    # DELETE
    # --------------------------------------------------

    if request.method == "POST":

        course.delete()

        messages.success(
            request,
            "Course deleted successfully."
        )

        return redirect(
            "courses:instructor_dashboard"
        )

    # --------------------------------------------------
    # CONFIRMATION
    # --------------------------------------------------

    return render(
        request,
        "courses/instructor/course_confirm_delete.html",
        {
            "course": course
        }
    )


# ======================================================
# CREATE COURSE
# ======================================================

@login_required
def course_create(request):

    # --------------------------------------------------
    # POST
    # --------------------------------------------------

    if request.method == "POST":

        form = CourseForm(
            request.POST,
            request.FILES
        )

        formset = CourseSectionFormSet(
            request.POST,
            prefix="sections"
        )

        if (
            form.is_valid()
            and formset.is_valid()
        ):

            with transaction.atomic():

                # --------------------------------------
                # COURSE
                # --------------------------------------

                course = form.save(
                    commit=False
                )

                course.created_by = (
                    request.user
                )

                # --------------------------------------
                # OWNER
                # --------------------------------------

                if request.user.is_superuser:

                    course.owner_type = (
                        Course.OWNER_PLATFORM
                    )

                elif (
                    hasattr(
                        request,
                        "organization"
                    )
                    and request.organization
                ):

                    course.organization = (
                        request.organization
                    )

                    course.owner_type = (
                        Course.OWNER_ORGANIZATION
                    )

                else:

                    course.organization = None

                    course.owner_type = (
                        Course.OWNER_PLATFORM
                    )

                # --------------------------------------
                # NEW COURSE MUST START AS DRAFT
                # --------------------------------------

                course.approval_status = (
                    Course.APPROVAL_DRAFT
                )

                course.is_published = False

                # Important:
                # Normal users should not create
                # publicly visible courses directly.

                if not request.user.is_superuser:

                    course.is_public = False

                course.save()

                form.save_m2m()

                # --------------------------------------
                # SECTIONS
                # --------------------------------------

                sections = (
                    formset.save(
                        commit=False
                    )
                )

                for index, section in enumerate(
                    sections,
                    start=1
                ):

                    section.course = course

                    if not section.order:

                        section.order = index

                    section.save()

            return redirect(
                "courses:course_builder",
                slug=course.slug
            )

    # --------------------------------------------------
    # GET
    # --------------------------------------------------

    else:

        form = CourseForm()

        formset = CourseSectionFormSet(
            prefix="sections"
        )

    # --------------------------------------------------
    # RESPONSE
    # --------------------------------------------------

    return render(
        request,
        "courses/instructor/course_create.html",
        {
            "form": form,
            "formset": formset,
        }
    )


# ======================================================
# EDIT LESSON
# ======================================================

@login_required
def lesson_edit(request, lesson_id):

    lesson = get_object_or_404(
        Lesson.objects.select_related(
            "section__course"
        ),
        id=lesson_id
    )

    course = lesson.section.course

    # --------------------------------------------------
    # PERMISSION
    # --------------------------------------------------

    if not can_edit_course(
        request.user,
        course
    ):

        return HttpResponseForbidden(
            "You are not allowed to edit this course."
        )

    # --------------------------------------------------
    # POST
    # --------------------------------------------------

    if request.method == "POST":

        form = LessonForm(
            request.POST,
            request.FILES,
            instance=lesson
        )

        if form.is_valid():

            with transaction.atomic():

                form.save()

            return redirect(
                "courses:course_builder",
                slug=course.slug
            )

    # --------------------------------------------------
    # GET
    # --------------------------------------------------

    else:

        form = LessonForm(
            instance=lesson
        )

    # --------------------------------------------------
    # RESPONSE
    # --------------------------------------------------

    return render(
        request,
        "courses/instructor/lesson_edit.html",
        {
            "form": form,
            "lesson": lesson,
            "course": course,
        }
    )



# ============================================================
# SUBMIT / RESUBMIT COURSE FOR REVIEW
# ============================================================

@login_required
def submit_course_for_review_view(request, slug):
    """
    Submit or resubmit a course for administrator review.

    Allowed states:

        DRAFT
        CHANGES_REQUIRED
        REJECTED

    Result:

        PENDING
    """

    if request.method != "POST":
        return HttpResponseForbidden(
            "POST request required."
        )

    course = get_object_or_404(
        Course,
        slug=slug,
    )

    # --------------------------------------------------------
    # COURSE EDIT PERMISSION
    # --------------------------------------------------------

    if not can_edit_course(
        request.user,
        course,
    ):
        return HttpResponseForbidden(
            "You are not allowed to submit this course."
        )

    # --------------------------------------------------------
    # SUBMIT
    # --------------------------------------------------------

    try:

        submit_course_for_review(
            course=course,
            user=request.user,
        )

    except PermissionError as exc:

        messages.error(
            request,
            str(exc),
        )

        return redirect(
            "courses:course_builder",
            slug=course.slug,
        )

    except ValueError as exc:

        messages.error(
            request,
            str(exc),
        )

        return redirect(
            "courses:course_builder",
            slug=course.slug,
        )

    # --------------------------------------------------------
    # SUCCESS
    # --------------------------------------------------------

    messages.success(
        request,
        f'"{course.title}" has been submitted for administrator review.',
    )

    return redirect(
        "courses:course_builder",
        slug=course.slug,
    )



# ============================================================
# UPDATE COURSE BUILDER ORDER
# ============================================================

import json

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import (
    JsonResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
)
from django.views.decorators.http import require_POST

from courses.models import Course, CourseSection, Lesson
from courses.services.permissions import can_edit_course


@login_required
@require_POST
def update_order(request, slug):
    """
    Update section and lesson ordering.

    Sections can only be reordered within the course.

    Lessons can only be reordered within their existing section.
    Moving a lesson between sections is intentionally NOT allowed.
    """

    # ---------------------------------------------------------
    # LOAD COURSE
    # ---------------------------------------------------------

    course = Course.objects.filter(
        slug=slug
    ).first()

    if not course:
        return JsonResponse(
            {
                "success": False,
                "error": "Course not found."
            },
            status=404
        )

    # ---------------------------------------------------------
    # PERMISSION
    # ---------------------------------------------------------

    if not can_edit_course(
        request.user,
        course
    ):
        return JsonResponse(
            {
                "success": False,
                "error": "You are not allowed to edit this course."
            },
            status=403
        )

    # ---------------------------------------------------------
    # PARSE JSON
    # ---------------------------------------------------------

    try:
        data = json.loads(
            request.body.decode("utf-8")
        )

    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse(
            {
                "success": False,
                "error": "Invalid JSON request."
            },
            status=400
        )

    sections_order = data.get(
        "sections",
        []
    )

    lessons_order = data.get(
        "lessons",
        {}
    )

    if not isinstance(
        sections_order,
        list
    ):
        return JsonResponse(
            {
                "success": False,
                "error": "Invalid sections data."
            },
            status=400
        )

    if not isinstance(
        lessons_order,
        dict
    ):
        return JsonResponse(
            {
                "success": False,
                "error": "Invalid lessons data."
            },
            status=400
        )

    # ---------------------------------------------------------
    # VALIDATE SECTION IDs
    # ---------------------------------------------------------

    course_sections = {
        str(section.id): section
        for section in CourseSection.objects.filter(
            course=course
        )
    }

    submitted_section_ids = [
        str(section_id)
        for section_id in sections_order
    ]

    # No duplicates
    if len(submitted_section_ids) != len(
        set(submitted_section_ids)
    ):
        return JsonResponse(
            {
                "success": False,
                "error": "Duplicate section detected."
            },
            status=400
        )

    # All submitted sections must belong to course
    for section_id in submitted_section_ids:

        if section_id not in course_sections:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Invalid section for this course."
                },
                status=400
            )

    # ---------------------------------------------------------
    # VALIDATE SECTION COMPLETENESS
    # ---------------------------------------------------------

    existing_section_ids = set(
        course_sections.keys()
    )

    submitted_section_id_set = set(
        submitted_section_ids
    )

    if existing_section_ids != submitted_section_id_set:
        return JsonResponse(
            {
                "success": False,
                "error": "Section ordering is incomplete."
            },
            status=400
        )

    # ---------------------------------------------------------
    # VALIDATE LESSONS
    # ---------------------------------------------------------

    course_lessons = {
        str(lesson.id): lesson
        for lesson in Lesson.objects.filter(
            section__course=course
        ).select_related("section")
    }

    for section_id, lesson_ids in lessons_order.items():

        section_id = str(section_id)

        if section_id not in course_sections:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Invalid section in lesson ordering."
                },
                status=400
            )

        if not isinstance(
            lesson_ids,
            list
        ):
            return JsonResponse(
                {
                    "success": False,
                    "error": "Invalid lesson ordering."
                },
                status=400
            )

        submitted_lesson_ids = [
            str(lesson_id)
            for lesson_id in lesson_ids
        ]

        if len(submitted_lesson_ids) != len(
            set(submitted_lesson_ids)
        ):
            return JsonResponse(
                {
                    "success": False,
                    "error": "Duplicate lesson detected."
                },
                status=400
            )

        # Make sure every lesson belongs to this section
        for lesson_id in submitted_lesson_ids:

            lesson = course_lessons.get(
                lesson_id
            )

            if not lesson:
                return JsonResponse(
                    {
                        "success": False,
                        "error": "Invalid lesson."
                    },
                    status=400
                )

            if str(lesson.section_id) != section_id:
                return JsonResponse(
                    {
                        "success": False,
                        "error": (
                            "Lessons cannot be moved "
                            "between sections."
                        )
                    },
                    status=400
                )

    # ---------------------------------------------------------
    # TRANSACTION
    # ---------------------------------------------------------

    try:

        with transaction.atomic():

            # =================================================
            # 1. TEMPORARY SECTION ORDER
            # =================================================

            # Negative values prevent collisions with
            # existing positive order values.

            for index, section_id in enumerate(
                submitted_section_ids,
                start=1
            ):

                section = course_sections[
                    section_id
                ]

                section.order = -index

                section.save(
                    update_fields=["order"]
                )

            # =================================================
            # 2. FINAL SECTION ORDER
            # =================================================

            for index, section_id in enumerate(
                submitted_section_ids,
                start=1
            ):

                section = course_sections[
                    section_id
                ]

                section.order = index

                section.save(
                    update_fields=["order"]
                )

            # =================================================
            # 3. TEMPORARY LESSON ORDER
            # =================================================

            for section_id, lesson_ids in lessons_order.items():

                for index, lesson_id in enumerate(
                    lesson_ids,
                    start=1
                ):

                    lesson = course_lessons[
                        str(lesson_id)
                    ]

                    lesson.order = -index

                    lesson.save(
                        update_fields=["order"]
                    )

            # =================================================
            # 4. FINAL LESSON ORDER
            # =================================================

            for section_id, lesson_ids in lessons_order.items():

                for index, lesson_id in enumerate(
                    lesson_ids,
                    start=1
                ):

                    lesson = course_lessons[
                        str(lesson_id)
                    ]

                    lesson.order = index

                    lesson.save(
                        update_fields=["order"]
                    )

    except Exception:
        return JsonResponse(
            {
                "success": False,
                "error": "Unable to save the new order."
            },
            status=500
        )

    # ---------------------------------------------------------
    # SUCCESS
    # ---------------------------------------------------------

    return JsonResponse(
        {
            "success": True,
            "message": "Order saved successfully."
        }
    )
