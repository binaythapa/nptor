from django.utils import timezone
from quiz.models import Coupon

class CouponService:

    @staticmethod
    def validate_coupon(code, *, exam=None, track=None):
        try:
            coupon = Coupon.objects.get(code=code.upper())
        except Coupon.DoesNotExist:
            return None, "Invalid coupon code"

        if not coupon.is_valid():
            return None, "Coupon expired or inactive"

        if coupon.exam and exam and coupon.exam != exam:
            return None, "Coupon not applicable for this exam"

        if coupon.track and track and coupon.track != track:
            return None, "Coupon not applicable for this track"

        return coupon, None
