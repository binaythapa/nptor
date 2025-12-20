# quiz/templatetags/dict_extras.py

from django import template

register = template.Library()

@register.filter
def dict_get(d, key):
    try:
        return d.get(str(key)) or d.get(key)
    except Exception:
        return None

@register.filter
def get_item(d, key):
    try:
        return d.get(key)
    except Exception:
        return None
    


