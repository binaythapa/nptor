from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any, Dict


class BasePaymentAdapter(ABC):
    """
    Provider-independent boundary for Store online payments.
    Encapsulates initiation, callback verification, and refunds.
    """

    @abstractmethod
    def initiate_payment(self, payment, return_url: str) -> Dict[str, Any]:
        """
        Initiates a payment request with the gateway provider.
        Returns a dict containing gateway response, redirect_url, gateway_reference, etc.
        """
        pass

    @abstractmethod
    def verify_payment(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verifies callback or webhook data from the payment gateway.
        Returns a normalized dict:
        {
            "is_successful": bool,
            "status": "successful" | "failed" | "pending",
            "gateway_payment_id": str,
            "gateway_order_id": str,
            "raw_response": dict,
        }
        """
        pass

    @abstractmethod
    def refund_payment(self, payment, amount: Decimal, reason: str = "") -> Dict[str, Any]:
        """
        Processes a refund with the gateway provider.
        """
        pass
