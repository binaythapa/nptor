from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.db import transaction

from courses.services.permissions import can_edit_course
from courses.models import Course, CourseSection, Lesson
from courses.forms import *
from django.db.models import Count


# ======================================================
# COURSE BUILDER
# ======================================================
from django.db.models import Prefetch
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseForbidden
from courses.models import Course, Lesson
from courses.services.permissions import can_edit_course


from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db import transaction

from courses.forms import CourseForm, CourseSectionFormSet
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpResponseForbidden
from django.db import transaction




@login_required
def course_builder(request, slug):

    course = get_object_or_404(
        Course,
        slug=slug
    )

    if not can_edit_course(request.user, course):
        return HttpResponseForbidden()

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



@login_required
def toggle_publish_course(request, slug):

    course = get_object_or_404(
        Course,
        slug=slug
    )

    if not can_edit_course(request.user, course):
        return HttpResponseForbidden()

    course.is_published = not course.is_published
    course.save(update_fields=["is_published"])

    return render(
        request,
        "courses/instructor/partials/publish_button.html",
        {"course": course}
    )
@login_required
def instructor_dashboard(request):

    base_queryset = (
        Course.objects
        .select_related("created_by", "organization")
        .annotate(
            total_lessons=Count("sections__lessons", distinct=True),
            total_enrollments=Count("enrollments", distinct=True),
        )
        .order_by("-created_at")
    )

    # --------------------------------
    # Organization courses
    # --------------------------------
    organization_courses = base_queryset.none()

    if hasattr(request, "organization") and request.organization:
        organization_courses = base_queryset.filter(
            organization=request.organization
        )

    # --------------------------------
    # Platform courses
    # --------------------------------
    admin_courses = base_queryset.filter(
        owner_type="platform"
    ) if request.user.is_superuser else base_queryset.none()

    # --------------------------------
    # Personal courses
    # --------------------------------
    my_courses = base_queryset.filter(
        created_by=request.user
    )

    return render(
        request,
        "courses/instructor/dashboard.html",
        {
            "organization_courses": organization_courses,
            "admin_courses": admin_courses,
            "my_courses": my_courses,
        }
    )

@login_required
def course_edit(request, slug):

    course = get_object_or_404(
        Course,
        slug=slug
    )

    if not can_edit_course(request.user, course):
        return HttpResponseForbidden("You are not allowed to edit this course.")

    if request.method == "POST":
        form = CourseForm(request.POST, request.FILES, instance=course)

        formset = CourseSectionFormSet(
            request.POST,
            instance=course,
            queryset=course.sections.order_by("order"),
            prefix="sections"
        )

        if form.is_valid() and formset.is_valid():

            with transaction.atomic():

                course = form.save(commit=False)

                if request.user.is_superuser:
                    pass
                
                elif hasattr(request, "organization") and request.organization:
                    course.organization = request.organization
                    course.owner_type = "organization"

                else:
                    course.organization = None
                    course.owner_type = "platform"

                course.save()
                form.save_m2m()

                sections = formset.save(commit=False)

                for section in sections:
                    section.course = course
                    section.save()

                # Handle deleted forms properly (hard delete)
                for obj in formset.deleted_objects:
                    obj.delete()

            return redirect("courses:course_builder", slug=course.slug)

    else:
        form = CourseForm(instance=course)
        formset = CourseSectionFormSet(
            instance=course,
            queryset=course.sections.order_by("order"),
            prefix="sections"
        )

    return render(
        request,
        "courses/instructor/course_edit.html",
        {
            "form": form,
            "formset": formset,
            "course": course
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

    if not can_edit_course(request.user, course):
        return HttpResponseForbidden("You are not allowed to delete this course.")

    if request.method == "POST":
        course.delete()
        return redirect("courses:instructor_dashboard")

    return render(
        request,
        "courses/instructor/course_confirm_delete.html",
        {"course": course}
    )


# ======================================================
# CREATE COURSE
# ======================================================

@login_required
def course_create(request):

    if request.method == "POST":
        form = CourseForm(request.POST, request.FILES)
        formset = CourseSectionFormSet(request.POST, prefix="sections")

        if form.is_valid() and formset.is_valid():

            with transaction.atomic():

                course = form.save(commit=False)
                course.created_by = request.user

                if request.user.is_superuser:
                    pass               
                elif hasattr(request, "organization") and request.organization:
                    course.organization = request.organization
                    course.owner_type = "organization"

                else:
                    course.organization = None
                    course.owner_type = "platform"

                course.save()
                form.save_m2m()

                sections = formset.save(commit=False)

                for index, section in enumerate(sections, start=1):
                    section.course = course
                    if not section.order:
                        section.order = index
                    section.save()

            return redirect(
                "courses:course_builder",
                slug=course.slug
            )

    else:
        form = CourseForm()
        formset = CourseSectionFormSet(prefix="sections")

    return render(
        request,
        "courses/instructor/course_create.html",
        {
            "form": form,
            "formset": formset
        }
    )


# ======================================================
# EDIT LESSON
# ======================================================

@login_required
def lesson_edit(request, lesson_id):

    lesson = get_object_or_404(
        Lesson.objects.select_related("section__course"),
        id=lesson_id
    )

    course = lesson.section.course

    if not can_edit_course(request.user, course):
        return HttpResponseForbidden()

    if request.method == "POST":
        form = LessonForm(request.POST, request.FILES, instance=lesson)

        if form.is_valid():
            with transaction.atomic():
                form.save()

            return redirect("courses:course_builder", slug=course.slug)

    else:
        form = LessonForm(instance=lesson)

    return render(
        request,
        "courses/instructor/lesson_edit.html",
        {
            "form": form,
            "lesson": lesson,
            "course": course,
        }
    )