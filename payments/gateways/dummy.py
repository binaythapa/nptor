from .base import BasePaymentGateway


class DummyPaymentGateway(BasePaymentGateway):

    gateway_name = "dummy"

    def create_payment(self, *, order):

        return {
            "success": True,
            "gateway_order_id": (
                f"DUMMY-{order.order_number}"
            ),
            "payment_url": None,
            "raw_response": {
                "test": True,
                "order_number": order.order_number,
            },
        }

    def verify_payment(self, *, data):

        if not data:
            return {
                "success": False,
                "error": "Payment data is required.",
            }

        gateway_payment_id = data.get(
            "gateway_payment_id"
        )

        if not gateway_payment_id:
            return {
                "success": False,
                "error": "Gateway payment ID is required.",
            }

        return {
            "success": True,
            "gateway_payment_id": gateway_payment_id,
            "raw_response": data,
        }

    def verify_webhook(
        self,
        *,
        payload,
        signature,
    ):

        # Dummy gateway is only for local testing.
        return True