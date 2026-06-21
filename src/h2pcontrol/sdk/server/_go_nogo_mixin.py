from abc import abstractmethod

import grpc
from h2pcontrol.gonogo.v1.gonogo_pb2 import GetReadyRequest, GetReadyResponse
from h2pcontrol.gonogo.v1.gonogo_pb2_grpc import GoNogoServiceServicer


class GoNogoMixin(GoNogoServiceServicer):
    """Optional mixin for services that have a physical readiness condition."""

    @abstractmethod
    async def _go_nogo(self) -> tuple[bool, str]:
        """Return (ready, reason). reason is empty string if ready."""
        ...

    async def GetReady(
        self, request: GetReadyRequest, context: grpc.aio.ServicerContext
    ) -> GetReadyResponse:
        ready, reason = await self._go_nogo()
        return GetReadyResponse(ready=ready, reason=reason)
