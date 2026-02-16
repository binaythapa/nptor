from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.db import transaction

from courses.services.permissions import can_edit_course
from courses.models import Course, CourseSection, Lesson
from courses.forms import *


# ======================================================
# COURSE BUILDER
# ======================================================
from django.db.models import Prefetch
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseForbidden
from courses.models import Course, Lesson
from courses.services.permissions import can_edit_course


@login_required
def course_builder(request, slug):

    course = get_object_or_404(
        Course,
        slug=slug,
        is_deleted=False
    )

    if not can_edit_course(request.user, course):
        return HttpResponseForbidden()

    sections = (
        course.sections
        .filter(is_deleted=False)
        .prefetch_related(
            Prefetch(
                "lessons",
                queryset=Lesson.objects.filter(is_deleted=False).order_by("order")
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
# PUBLISH COURSE
# ======================================================

@login_required
def publish_course(request, slug):

    course = get_object_or_404(
        Course,
        slug=slug,
        is_deleted=False
    )

    if not can_edit_course(request.user, course):
        return HttpResponseForbidden()

    course.is_published = True
    course.save(update_fields=["is_published"])

    return redirect("courses:course_builder", slug=course.slug)


# ======================================================
# INSTRUCTOR DASHBOARD
# ======================================================

@login_required
def instructor_dashboard(request):

    if request.user.is_superuser:
        courses = Course.objects.filter(is_deleted=False)

    elif hasattr(request.user, "organization") and request.user.organization:
        courses = Course.objects.filter(
            organization=request.user.organization,
            is_deleted=False
        )

    else:
        courses = Course.objects.filter(
            created_by=request.user,
            is_deleted=False
        )

    return render(
        request,
        "courses/instructor/dashboard.html",
        {"courses": courses}
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

            course = form.save(commit=False)
            course.created_by = request.user

            if hasattr(request.user, "organization") and request.user.organization:
                course.organization = request.user.organization
                course.owner_type = "organization"
            else:
                course.organization = None
                course.owner_type = "platform"

            course.save()
            form.save_m2m()

            sections = formset.save(commit=False)

            for index, section in enumerate(sections, start=1):
                section.course = course
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
# EDIT COURSE
# ======================================================

@login_required
def course_edit(request, slug):

    course = get_object_or_404(
        Course,
        slug=slug,
        is_deleted=False
    )

    if not can_edit_course(request.user, course):
        return HttpResponseForbidden()

    if request.method == "POST":
        form = CourseForm(request.POST, request.FILES, instance=course)
        formset = CourseSectionFormSet(
            request.POST,
            instance=course,
            prefix="sections"
        )

        if form.is_valid() and formset.is_valid():

            with transaction.atomic():

                course = form.save(commit=False)

                if hasattr(request.user, "organization") and request.user.organization:
                    course.organization = request.user.organization
                    course.owner_type = "organization"
                else:
                    course.organization = None
                    course.owner_type = "platform"

                course.save()
                form.save_m2m()

                sections = formset.save(commit=False)

                # 🔥 SOFT DELETE instead of hard delete
                for obj in formset.deleted_objects:
                    obj.is_deleted = True
                    obj.save(update_fields=["is_deleted"])

                for index, section in enumerate(sections, start=1):
                    section.course = course
                    section.order = index
                    section.save()

            return redirect(
                "courses:course_builder",
                slug=course.slug
            )

    else:
        form = CourseForm(instance=course)
        formset = CourseSectionFormSet(
            instance=course,
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
# DELETE COURSE (SOFT)
# ======================================================

@login_required
def course_delete(request, slug):

    course = get_object_or_404(
        Course,
        slug=slug,
        is_deleted=False
    )

    if not can_edit_course(request.user, course):
        return HttpResponseForbidden()

    if request.method == "POST":
        course.is_deleted = True
        course.save(update_fields=["is_deleted"])

        return redirect("courses:instructor_dashboard")

    return render(
        request,
        "courses/instructor/course_confirm_delete.html",
        {"course": course}
    )


@login_required
def lesson_edit(request, lesson_id):

    lesson = get_object_or_404(Lesson, id=lesson_id)

    if not can_edit_course(request.user, lesson.section.course):
        return HttpResponseForbidden()

    if request.method == "POST":
        form = LessonForm(request.POST, request.FILES, instance=lesson)
        if form.is_valid():
            form.save()
            return redirect(
                "courses:course_builder",
                slug=lesson.section.course.slug
            )
    else:
        form = LessonForm(instance=lesson)

    return render(
        request,
        "courses/instructor/lesson_edit.html",
        {
            "form": form,
            "lesson": lesson
        }
    )
