def can_edit_course(user, course):
    if user.is_superuser:
        return True

    if course.created_by == user:
        return True

    if course.organization and hasattr(user, "organization"):
        return course.organization == user.organization

    return False
