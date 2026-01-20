from decimal import Decimal

class PricingService:

    @staticmethod
    def calculate_price(base_price, coupon=None):
        final_price = Decimal(base_price)

        if coupon:
            if coupon.percent_off:
                discount = (coupon.percent_off / Decimal(100)) * final_price
                final_price -= discount

            if coupon.flat_off:
                final_price -= coupon.flat_off

        return max(final_price, Decimal("0.00"))
