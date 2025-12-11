# quiz/utils.py
from functools import lru_cache
from typing import Optional
from .models import Category

@lru_cache(maxsize=1024)
def _leaf_category_name_cached(category_id: int) -> Optional[str]:
    """
    Internal cached lookup:
      - returns "" if category exists but has children (treated as parent)
      - returns leaf name (last segment after '->') if it's a leaf
      - returns None if category_id is falsy or the category does not exist
    """
    if not category_id:
        return None
    try:
        c = Category.objects.get(pk=category_id)
    except Category.DoesNotExist:
        return None

    # If the category has children, treat it as a parent -> skip (return empty string)
    try:
        if c.children.exists():
            return ""
    except Exception:
        # if related name / DB issue, fall back to name parsing below
        pass

    parts = [p.strip() for p in (c.name or "").split('->') if p is not None]
    return parts[-1] if parts else (c.name or "")


def get_leaf_category_name(category: Optional[Category]) -> Optional[str]:
    """
    Public wrapper that accepts a Category model instance (or None).
    Uses the cached function for saved Category objects; falls back to parsing
    the name for unsaved instances.
    """
    if not category:
        return None
    cid = getattr(category, 'id', None)
    if cid is None:
        parts = [p.strip() for p in (category.name or "").split('->') if p is not None]
        return parts[-1] if parts else (category.name or "")
    return _leaf_category_name_cached(cid)


def clear_leaf_category_cache() -> None:
    """Clear the internal LRU cache (call when categories change)."""
    _leaf_category_name_cached.cache_clear()
