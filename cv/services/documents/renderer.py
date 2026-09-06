from copy import deepcopy
import re


DEFAULT_RENDER_CONFIG = {
    "font_name": "Helvetica",
    "font_size": 10,
    "heading_size": 12,
    "margin": 48,
    "accent_color": "#111827",
    "section_gap": 8,
    "layout": "single_column",
    "header_style": "left",
    "section_style": "uppercase_rule",
    "density": "comfortable",
    "design_style": "modern_header",
}

ALLOWED_FONTS = {"Helvetica", "Helvetica-Bold", "Times-Roman", "Times-Bold", "Courier"}
ALLOWED_LAYOUTS = {"single_column", "sidebar"}
ALLOWED_HEADER_STYLES = {"left", "centered", "compact"}
ALLOWED_SECTION_STYLES = {"uppercase_rule", "title_case", "minimal"}
ALLOWED_DENSITIES = {"comfortable", "compact"}
ALLOWED_DESIGN_STYLES = {"modern_header", "split_label", "elegant"}
HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")

RENDER_SECTIONS = (
    ("summary", "Professional Summary", "text", "summary"),
    ("experiences", "Experience", "items", "experiences"),
    ("educations", "Education", "items", "educations"),
    ("skills", "Skills", "items", "skills"),
    ("projects", "Projects", "items", "projects"),
    ("certifications", "Certifications", "items", "certifications"),
    ("achievements", "Achievements", "items", "achievements"),
)


def get_template_snapshot(template):
    """Return a detached template snapshot suitable for versioned rendering."""
    return {
        "slug": template.slug,
        "name": template.name,
        "config": deepcopy(template.config or {}),
    }


def _infer_design_style(raw, config):
    """Map legacy template settings to one of the richer visual design systems."""
    explicit = raw.get("design_style")
    if explicit in ALLOWED_DESIGN_STYLES:
        return explicit
    if config["layout"] == "sidebar":
        return "split_label"
    if config["header_style"] == "centered":
        return "elegant"
    return "modern_header"


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
    if raw.get("layout") in ALLOWED_LAYOUTS:
        config["layout"] = raw["layout"]
    if raw.get("header_style") in ALLOWED_HEADER_STYLES:
        config["header_style"] = raw["header_style"]
    if raw.get("section_style") in ALLOWED_SECTION_STYLES:
        config["section_style"] = raw["section_style"]
    if raw.get("density") in ALLOWED_DENSITIES:
        config["density"] = raw["density"]

    config["design_style"] = _infer_design_style(raw, config)

    if config["density"] == "compact":
        config["section_gap"] = min(config["section_gap"], 5)

    return config


def build_cv_render_context(cv):
    """Build the canonical view-model shared by CV preview and document renderers."""
    from cv.services.cv_builder import build_cv_payload

    payload = build_cv_payload(cv)
    config = get_render_config(payload.get("template", {}))
    sections = []
    for key, heading, kind, payload_key in RENDER_SECTIONS:
        value = payload.get(payload_key)
        if value:
            sections.append({"key": key, "heading": heading, "kind": kind, "value": value})
    return {"payload": payload, "config": config, "sections": sections}


def render_cv(cv_version):
    """Return the immutable payload stored on a CV version."""
    return deepcopy(cv_version.snapshot or {})
