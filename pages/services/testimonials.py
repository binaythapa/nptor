from pages.models import Testimonial


def get_testimonial_context(user, *,
                            exam_track=None,
                            course=None,
                            study_plan=None,
                            trigger=False):
    """
    Returns context dict for testimonial popup.

    trigger = True only when completion event just happened
    """

    context = {
        "show_testimonial_popup": False,
        "testimonial_exam_track": None,
        "testimonial_course": None,
        "testimonial_study_plan": None,
    }

    if not trigger:
        return context

    # Exam track
    if exam_track:
        exists = Testimonial.objects.filter(
            user=user,
            exam_track=exam_track
        ).exists()

        if not exists:
            context["show_testimonial_popup"] = True
            context["testimonial_exam_track"] = exam_track
            return context

    # Course
    if course:
        exists = Testimonial.objects.filter(
            user=user,
            course=course
        ).exists()

        if not exists:
            context["show_testimonial_popup"] = True
            context["testimonial_course"] = course
            return context

    # Study Plan
    if study_plan:
        exists = Testimonial.objects.filter(
            user=user,
            study_plan=study_plan
        ).exists()

        if not exists:
            context["show_testimonial_popup"] = True
            context["testimonial_study_plan"] = study_plan
            return context

    return context