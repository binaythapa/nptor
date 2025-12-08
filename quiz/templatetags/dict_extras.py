# quiz/templatetags/dict_extras.py
from django import template

register = template.Library()

@register.filter
def dict_get(d, key):
    """
    Safely get d[str(key)] when d is a dict (JSONField).
    Returns None if not found or if d is not a dict.
    """
    if not d:
        return None
    try:
        # prefer string key because JSONField often stores keys as strings
        return d.get(str(key), d.get(key))
    except Exception:
        return None
