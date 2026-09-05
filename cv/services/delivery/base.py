from dataclasses import dataclass


class DeliveryNotConfigured(RuntimeError):
    """Raised when an external delivery provider is not configured."""


@dataclass(frozen=True)
class DeliveryResult:
    status: str
    provider: str
    error_message: str = ""


class DeliveryProvider:
    channel = ""

    def send(self, artifact, recipient, metadata=None):
        raise NotImplementedError
