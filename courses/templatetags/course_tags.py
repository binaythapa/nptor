from django import template

from courses.views.student_enrollment import is_course_free


register = template.Library()


@register.simple_tag
def course_is_free(course):
    return is_course_free(course)
