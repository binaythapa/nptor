from cart.models import Cart
from store.models import Category


def store_context(request):
    """
    Provides store categories and cart item count for store navigation
    without database overhead on non-store routes.
    """
    cart_count = 0
    try:
        if request.user.is_authenticated:
            cart = Cart.objects.filter(user=request.user).first()
            if cart:
                cart_count = sum(item.quantity for item in cart.items.all())
        else:
            guest_id = request.session.get("guest_cart_id")
            session_key = request.session.session_key
            if guest_id:
                cart = Cart.objects.filter(id=guest_id).first()
                if cart:
                    cart_count = sum(item.quantity for item in cart.items.all())
            elif session_key:
                cart = Cart.objects.filter(session_key=session_key).first()
                if cart:
                    cart_count = sum(item.quantity for item in cart.items.all())
    except Exception:
        cart_count = 0

    try:
        categories = list(
            Category.objects.filter(is_active=True, parent=None).prefetch_related("children")
        )
    except Exception:
        categories = []

    return {
        "store_header_categories": categories,
        "store_cart_count": cart_count,
        "store_query": request.GET.get("q", "") if hasattr(request, "GET") else "",
        "store_category_slug": request.GET.get("category", "") if hasattr(request, "GET") else "",
    }
