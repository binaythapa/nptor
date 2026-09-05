from copy import deepcopy
import re


DEFAULT_RENDER_CONFIG = {
    "font_name": "Helvetica",
    "font_size": 10,
    "heading_size": 12,
    "margin": 48,
    "accent_color": "#111827",
    "section_gap": 8,
}

ALLOWED_FONTS = {"Helvetica", "Helvetica-Bold", "Times-Roman", "Times-Bold", "Courier"}
HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


def get_template_snapshot(template):
    """Return a detached template snapshot suitable for versioned rendering."""
    return {
        "slug": template.slug,
        "name": template.name,
        "config": deepcopy(template.config or {}),
    }


def get_render_config(template_snapshot):
    """Return a bounded, renderer-safe configuration from a frozen template snapshot."""
    raw = deepcopy((template_snapshot or {}).get("config") or {})
    config = deepcopy(DEFAULT_RENDER_CONFIG)

    if raw.get("font_name") in ALLOWED_FONTS:
        config["font_name"] = raw["font_name"]
    if isinstance(raw.get("font_size"), (int, float)) and 8 <= raw["font_size"] <= 14:
        config["font_size"] = int(raw["font_size"])
    if isinstance(raw.get("heading_size"), (int, float)) and 10 <= raw["heading_size"] <= 18:
        config["heading_size"] = int(raw["heading_size"])
    if isinstance(raw.get("margin"), (int, float)) and 30 <= raw["margin"] <= 80:
        config["margin"] = int(raw["margin"])
    if isinstance(raw.get("section_gap"), (int, float)) and 2 <= raw["section_gap"] <= 24:
        config["section_gap"] = int(raw["section_gap"])
    if isinstance(raw.get("accent_color"), str) and HEX_COLOR_RE.fullmatch(raw["accent_color"]):
        config["accent_color"] = raw["accent_color"].lower()

    return config


def render_cv(cv_version):
    """Return the immutable payload stored on a CV version."""
    return deepcopy(cv_version.snapshot or {})
