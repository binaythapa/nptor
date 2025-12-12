# quiz/utils.py
from functools import lru_cache
from typing import Optional
from .models import Category

@lru_cache(maxsize=1024)
def _leaf_category_name_cached(category_id: int) -> Optional[str]:
    """
    Returns:
      - "" (empty string) if the category exists but has children (parent)
      - leaf name (last segment after '->') if it's a leaf
      - None if category does not exist or category_id falsy
    """
    if not category_id:
        return None
    try:
        c = Category.objects.get(pk=category_id)
    except Category.DoesNotExist:
        return None

    try:
        if c.children.exists():
            return ""
    except Exception:
        # fallback to parsing name
        pass

    parts = [p.strip() for p in (c.name or "").split('->') if p is not None]
    return parts[-1] if parts else (c.name or "")


def get_leaf_category_name(category: Optional[Category]) -> Optional[str]:
    """
    Wrapper that accepts a Category instance (or None) and returns the leaf label.
    """
    if not category:
        return None
    cid = getattr(category, 'id', None)
    if cid is None:
        # unsaved instance: parse name directly
        parts = [p.strip() for p in (category.name or "").split('->') if p is not None]
        return parts[-1] if parts else (category.name or "")
    return _leaf_category_name_cached(cid)


def clear_leaf_category_cache() -> None:
    """Clear the internal LRU cache. Call on category changes."""
    _leaf_category_name_cached.cache_clear()
