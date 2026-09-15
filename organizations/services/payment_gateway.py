from dataclasses import dataclass


@dataclass(frozen=True)
class GatewayCheckout:
    checkout_url: str
    reference: str


class PaymentGateway:
    """Small gateway contract so a real provider can replace the dummy later."""

    provider = "manual"

    def create_checkout(self, *, payment):
        raise NotImplementedError

    def verify_payment(self, *, payment, reference):
        raise NotImplementedError


class DummyPaymentGateway(PaymentGateway):
    """Development gateway that simulates a hosted payment page."""

    provider = "manual"

    def create_checkout(self, *, payment):
        return GatewayCheckout(
            checkout_url=f"/organizations/admin/payment-checkout/{payment.pk}/",
            reference=f"DUMMY-{payment.pk}",
        )

    def verify_payment(self, *, payment, reference):
        expected = f"DUMMY-{payment.pk}"
        return reference == expected and payment.status == payment.STATUS_PENDING


def get_payment_gateway():
    """Return the configured gateway adapter.

    The adapter boundary intentionally stays independent of any real provider
    SDK. A future gateway can replace DummyPaymentGateway without changing
    subscription or entitlement business rules.
    """
    return DummyPaymentGateway()
