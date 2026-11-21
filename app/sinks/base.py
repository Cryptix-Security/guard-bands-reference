from abc import ABC, abstractmethod

from app.audit import AuditEvent


class AuditSink(ABC):
    @abstractmethod
    async def emit(self, event: AuditEvent) -> None: ...

    async def startup(self) -> None:  # noqa: B027 - optional hook, no-op by default
        pass

    async def shutdown(self) -> None:  # noqa: B027 - optional hook, no-op by default
        pass
