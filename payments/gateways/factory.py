from django.core.exceptions import ImproperlyConfigured

from .base import BasePaymentGateway
from .dummy import DummyPaymentGateway


class PaymentGatewayFactory:

    _gateways = {}

    @classmethod
    def register(cls, name, gateway_class):

        if not issubclass(
            gateway_class,
            BasePaymentGateway,
        ):
            raise TypeError(
                "Gateway must inherit BasePaymentGateway."
            )

        cls._gateways[name.lower()] = gateway_class

    @classmethod
    def get(cls, name):

        if not name:
            raise ImproperlyConfigured(
                "Payment gateway name is required."
            )

        gateway_class = cls._gateways.get(
            name.lower()
        )

        if not gateway_class:
            raise ImproperlyConfigured(
                f"Payment gateway '{name}' "
                f"is not registered."
            )

        return gateway_class()

    @classmethod
    def available_gateways(cls):
        return list(cls._gateways.keys())


# ============================================================
# REGISTER GATEWAYS
# ============================================================

PaymentGatewayFactory.register(
    "dummy",
    DummyPaymentGateway,
)