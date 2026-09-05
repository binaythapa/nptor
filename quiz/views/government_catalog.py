from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from courses.models import Course
from quiz.models import (
    Country,
    GovernmentBody,
    GovernmentExamProgram,
    GovernmentExamStage,
    GovernmentExamVersion,
    GovernmentJob,
    Exam,
)


@login_required
def government_catalog(request):
    countries = (
        Country.objects.filter(is_active=True)
        .prefetch_related("government_bodies")
        .order_by("name")
    )
    return render(
        request,
        "quiz/student/government_catalog.html",
        {"countries": countries},
    )


@login_required
def government_country(request, country_slug):
    country = get_object_or_404(Country, slug=country_slug, is_active=True)
    bodies = (
        GovernmentBody.objects.filter(country=country, is_active=True)
        .prefetch_related("exam_programs")
        .order_by("name")
    )
    programs = GovernmentExamProgram.objects.filter(
        country=country,
        is_active=True,
        government_body__is_active=True,
    ).select_related("government_body").order_by("name")
    return render(
        request,
        "quiz/student/government_country.html",
        {"country": country, "bodies": bodies, "programs": programs},
    )


@login_required
def government_body(request, country_slug, body_slug):
    country = get_object_or_404(Country, slug=country_slug, is_active=True)
    body = get_object_or_404(
        GovernmentBody,
        country=country,
        slug=body_slug,
        is_active=True,
    )
    jobs = GovernmentJob.objects.filter(
        government_body=body,
        country=country,
        is_active=True,
    ).order_by("name")
    programs = GovernmentExamProgram.objects.filter(
        country=country,
        government_body=body,
        is_active=True,
    ).order_by("name")
    return render(
        request,
        "quiz/student/government_body.html",
        {"country": country, "body": body, "jobs": jobs, "programs": programs},
    )


@login_required
def government_program(request, country_slug, body_slug, program_slug):
    country = get_object_or_404(Country, slug=country_slug, is_active=True)
    body = get_object_or_404(
        GovernmentBody,
        country=country,
        slug=body_slug,
        is_active=True,
    )
    program = get_object_or_404(
        GovernmentExamProgram.objects.select_related("content_vertical"),
        country=country,
        government_body=body,
        slug=program_slug,
        is_active=True,
    )

    jobs = program.jobs.filter(is_active=True).order_by("name")
    versions = GovernmentExamVersion.objects.filter(
        program=program,
        status=GovernmentExamVersion.ACTIVE,
    ).order_by("-effective_from", "-created_at")
    stages = GovernmentExamStage.objects.filter(
        version__program=program,
        version__status=GovernmentExamVersion.ACTIVE,
        is_active=True,
    ).select_related("version", "exam").order_by("version", "order")
    exams = (
        Exam.objects.filter(
            government_stages__version__program=program,
            government_stages__version__status=GovernmentExamVersion.ACTIVE,
            government_stages__is_active=True,
            is_published=True,
        )
        .distinct()
        .order_by("title")
    )
    courses = (
        program.courses.filter(
            is_public=True,
            is_published=True,
            approval_status=Course.APPROVAL_APPROVED,
        )
        .distinct()
        .order_by("title")
    )

    return render(
        request,
        "quiz/student/government_program.html",
        {
            "country": country,
            "body": body,
            "program": program,
            "jobs": jobs,
            "versions": versions,
            "stages": stages,
            "exams": exams,
            "courses": courses,
        },
    )
