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

@login_required
def toggle_publish_course(request, slug):
    """
    Legacy instructor publish endpoint.

    Publishing is now controlled exclusively by
    platform administrators.

    Instructors can create, edit and submit courses
    for review, but cannot publish or unpublish them.
    """

    # --------------------------------------------------------
    # COURSE
    # --------------------------------------------------------

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
            "You are not allowed to modify this course."
        )

    # --------------------------------------------------------
    # BLOCK INSTRUCTOR PUBLISHING
    # --------------------------------------------------------

    return HttpResponseForbidden(
        "Course publishing is controlled by "
        "platform administrators."
    )

# ======================================================
# INSTRUCTOR DASHBOARD
# ======================================================

@login_required
def instructor_dashboard(request):

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

    if (
        hasattr(request, "organization")
        and request.organization
    ):

        organization_courses = (
            base_queryset.filter(
                organization=request.organization
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