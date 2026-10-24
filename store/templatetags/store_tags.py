from django import template

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
