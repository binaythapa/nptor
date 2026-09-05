from copy import deepcopy


def get_template_snapshot(template):
    """Return a detached template snapshot suitable for versioned rendering."""
    return {
        "slug": template.slug,
        "name": template.name,
        "config": deepcopy(template.config or {}),
    }


def render_cv(cv_version):
    """Return the immutable payload stored on a CV version."""
    return deepcopy(cv_version.snapshot or {})
