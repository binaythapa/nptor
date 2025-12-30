from decimal import Decimal
from quiz.models import Coupon

def apply_coupon(price, coupon_code):
    if not coupon_code:
        return price, None

    try:
        coupon = Coupon.objects.get(code=coupon_code.upper())
    except Coupon.DoesNotExist:
        return price, "Invalid coupon"

    if not coupon.is_valid():
        return price, "Coupon expired or inactive"

    new_price = Decimal(price)

    if coupon.percent_off:
        new_price -= (new_price * Decimal(coupon.percent_off) / 100)

    if coupon.flat_off:
        new_price -= Decimal(coupon.flat_off)

    new_price = max(new_price, Decimal("0.00"))

    return new_price, coupon
