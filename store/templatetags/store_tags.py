import re
from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter(name="category_icon")
def category_icon(name):
    """
    Returns an appropriate FontAwesome icon class for any general marketplace
    category name (electronics, fashion, home, beauty, books, groceries, sports, etc.).
    """
    if not name:
        return "fa-tag"
    n = str(name).lower()
    if any(k in n for k in ["electronic", "tech", "gadget", "mobile", "phone", "computer", "laptop", "audio", "camera", "engineering"]):
        return "fa-laptop"
    if any(k in n for k in ["fashion", "clothing", "apparel", "wear", "shirt", "dress", "shoe", "footwear"]):
        return "fa-shirt"
    if any(k in n for k in ["home", "kitchen", "furniture", "living", "appliance", "decor"]):
        return "fa-couch"
    if any(k in n for k in ["beauty", "personal care", "cosmetic", "skincare", "fragrance", "health", "wellness"]):
        return "fa-spa"
    if any(k in n for k in ["book", "study", "exam", "guide", "notes", "education", "academic", "learning"]):
        return "fa-book-bookmark"
    if any(k in n for k in ["stationery", "pen", "notebook", "office", "supplies"]):
        return "fa-pen-ruler"
    if any(k in n for k in ["grocery", "groceries", "food", "beverage", "snack", "daily"]):
        return "fa-basket-shopping"
    if any(k in n for k in ["sport", "fitness", "gym", "exercise", "outdoor", "athletic"]):
        return "fa-dumbbell"
    if any(k in n for k in ["toy", "game", "gaming", "baby", "kid"]):
        return "fa-gamepad"
    if any(k in n for k in ["desk", "organizer", "storage"]):
        return "fa-boxes-stacked"
    if any(k in n for k in ["auto", "vehicle", "car", "tool", "hardware"]):
        return "fa-screwdriver-wrench"
    return "fa-layer-group"


@register.filter(name="render_markdown")
def render_markdown(value):
    """
    Safely converts Markdown syntax (headings, bold, italics, lists, paragraphs)
    into sanitized HTML without requiring external third-party dependencies.
    """
    if not value:
        return ""

    # 1. Escape any raw HTML characters to prevent XSS
    text = escape(str(value).strip())

    # 2. Parse headings
    text = re.sub(r"^\s*###\s+(.+)$", r'<h4 class="title is-6 mb-2 mt-4">\1</h4>', text, flags=re.MULTILINE)
    text = re.sub(r"^\s*##\s+(.+)$", r'<h3 class="title is-5 mb-2 mt-4">\1</h3>', text, flags=re.MULTILINE)
    text = re.sub(r"^\s*#\s+(.+)$", r'<h2 class="title is-4 mb-3 mt-4">\1</h2>', text, flags=re.MULTILINE)

    # 3. Bold: **text**
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)

    # 4. Italics: *text* (excluding already formatted bold)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", text)

    # 5. Process lists & paragraphs line by line
    lines = text.split("\n")
    in_list = False
    output_lines = []

    for line in lines:
        stripped = line.strip()
        if re.match(r"^[-*]\s+(.+)$", stripped):
            item_text = re.sub(r"^[-*]\s+", "", stripped)
            if not in_list:
                output_lines.append('<ul class="store-desc-list">')
                in_list = True
            output_lines.append(f"<li>{item_text}</li>")
        else:
            if in_list:
                output_lines.append("</ul>")
                in_list = False
            if stripped:
                if stripped.startswith("<h") and (
                    stripped.endswith("</h3>") or stripped.endswith("</h4>") or stripped.endswith("</h2>")
                ):
                    output_lines.append(stripped)
                else:
                    output_lines.append(f'<p class="mb-3">{stripped}</p>')

    if in_list:
        output_lines.append("</ul>")

    return mark_safe("\n".join(output_lines))
