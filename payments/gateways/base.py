from abc import ABC, abstractmethod


class BasePaymentGateway(ABC):
    """
    Common interface for every payment gateway.

    Razorpay, Khalti, eSewa, Stripe, etc.
    must implement this interface.
    """

    gateway_name = None

    @abstractmethod
    def create_payment(self, *, order):
        """
        Create/initiate a payment with the gateway.

        Must return a normalized dictionary, for example:

        {
            "success": True,
            "gateway_order_id": "...",
            "payment_url": "...",
            "raw_response": {...},
        }
        """
        raise NotImplementedError

    @abstractmethod
    def verify_payment(self, *, data):
        """
        Verify a payment/callback.

        Must return normalized payment information.
        """
        raise NotImplementedError

    @abstractmethod
    def verify_webhook(self, *, payload, signature):
        """
        Verify that a webhook genuinely came from
        the payment provider.
        """
        raise NotImplementedError

    def refund_payment(
        self,
        *,
        transaction,
        amount=None,
    ):
        """
        Optional capability.

        Gateways supporting refunds can override this.
        """
        raise NotImplementedError(
            f"{self.gateway_name} does not support refunds."
        )