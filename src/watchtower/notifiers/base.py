"""Base notifier interface protocol."""

from typing import List, Protocol, runtime_checkable

from watchtower.schemas.alert import AlertPayload


@runtime_checkable
class BaseNotifier(Protocol):
    """Protocol that all alert channel providers must implement."""

    name: str

    def is_configured(self) -> bool:
        """Return True if credentials and parameters are validly configured."""
        ...

    def send(self, payloads: List[AlertPayload]) -> bool:
        """Dispatch a batch of alert payloads to the destination channel."""
        ...
