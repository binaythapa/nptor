from decimal import Decimal
from typing import Any, Dict
import uuid

from .base import BasePaymentAdapter


class DummyPaymentAdapter(BasePaymentAdapter):
    """
    Test and development payment adapter for NPTOR Store.
    Provides deterministic simulation without calling live financial rails.
    """

    def initiate_payment(self, payment, return_url: str) -> Dict[str, Any]:
        gateway_order_id = f"DUMMY-GW-{uuid.uuid4().hex[:12].upper()}"
        payment.gateway_name = "dummy"
        payment.gateway_order_id = gateway_order_id
        payment.status = "processing"
        payment.save(update_fields=["gateway_name", "gateway_order_id", "status", "updated_at"])
        return {
            "success": True,
            "gateway_order_id": gateway_order_id,
            "redirect_url": f"{return_url}?gateway_order_id={gateway_order_id}&mock_status=success",
        }

    def verify_payment(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        mock_status = payload.get("mock_status", "success")
        gateway_order_id = payload.get("gateway_order_id", "")
        gateway_payment_id = payload.get("gateway_payment_id") or f"TXN-DUMMY-{uuid.uuid4().hex[:10].upper()}"

        is_successful = (mock_status == "success")
        return {
            "is_successful": is_successful,
            "status": "successful" if is_successful else "failed",
            "gateway_payment_id": gateway_payment_id,
            "gateway_order_id": gateway_order_id,
            "raw_response": payload,
        }

    def refund_payment(self, payment, amount: Decimal, reason: str = "") -> Dict[str, Any]:
        refund_id = f"REFUND-DUMMY-{uuid.uuid4().hex[:10].upper()}"
        return {
            "is_successful": True,
            "refund_id": refund_id,
            "refunded_amount": str(amount),
            "reason": reason,
        }
