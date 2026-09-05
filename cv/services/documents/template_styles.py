"""Presentation metadata used by the CV template chooser and renderers."""

TEMPLATE_STYLE_SUMMARY = {
    "ats-classic": {"layout": "single_column", "header_style": "left", "section_style": "uppercase_rule", "density": "comfortable"},
    "modern-professional": {"layout": "sidebar", "header_style": "left", "section_style": "uppercase_rule", "density": "comfortable"},
    "executive": {"layout": "single_column", "header_style": "centered", "section_style": "title_case", "density": "comfortable"},
    "technical": {"layout": "sidebar", "header_style": "compact", "section_style": "minimal", "density": "compact"},
    "fresher": {"layout": "single_column", "header_style": "centered", "section_style": "uppercase_rule", "density": "comfortable"},
    "academic": {"layout": "single_column", "header_style": "left", "section_style": "title_case", "density": "comfortable"},
    "government": {"layout": "single_column", "header_style": "left", "section_style": "title_case", "density": "comfortable"},
    "minimal": {"layout": "single_column", "header_style": "compact", "section_style": "minimal", "density": "compact"},
}


def get_template_style(slug):
    """Return presentation metadata without exposing mutable template configuration."""
    return dict(TEMPLATE_STYLE_SUMMARY.get(slug, TEMPLATE_STYLE_SUMMARY["ats-classic"]))
