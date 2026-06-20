import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Callable, TypeVar, cast

import grpc
from h2pcontrol.manager.v1.manager_pb2 import ListRequest, LogEntry, StreamLogsRequest, WatchRequest
from h2pcontrol.manager.v1.manager_pb2_grpc import ManagerServiceStub

if TYPE_CHECKING:
    from h2pcontrol.manager.v1.manager_pb2_grpc import ManagerServiceAsyncStub
TStub = TypeVar("TStub")

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Service:
    """A service registered with the manager."""

    name: str
    address: str
    healthy: bool
    last_seen: datetime


class Client:
    """
    H2PControl Manager Client implementation. This provides utilities
    for connecting to Services registered with a manager.
    """

    def __init__(self, manager_address: str):
        self._manager_address = manager_address
        self._manager_channel: grpc.aio.Channel
        self._manager_stub: ManagerServiceAsyncStub
        self._channels: dict[str, grpc.aio.Channel] = {}
        self._server_registry: dict[str, str] = {}  # name -> address
        self._connected = False

    async def _ensure_connected(self):
        """Lazy connect to manager on first use."""
        if self._connected:
            return
        self._manager_channel = grpc.aio.insecure_channel(self._manager_address)
        self._manager_stub = cast(
            "ManagerServiceAsyncStub", ManagerServiceStub(self._manager_channel)
        )
        await self._refresh_registry()
        self._connected = True

    async def _refresh_registry(self):
        """Fetch the current server list from manager."""
        try:
            response = await self._manager_stub.List(ListRequest())
            self._server_registry = {
                service.definition.name: service.definition.address for service in response.services
            }
        except grpc.aio.AioRpcError as e:
            await self._manager_channel.close()
            self._connected = False
            logger.warning("No response received from manager: %s", e.details())
            raise

    async def service(self, name: str, stub_class: Callable[[grpc.aio.Channel], TStub]) -> TStub:
        """Get a ready-to-use gRPC stub for a named service."""
        await self._ensure_connected()

        if name not in self._server_registry:
            await self._refresh_registry()
            if name not in self._server_registry:
                raise ServiceNotFoundError(name, list(self._server_registry.keys()))

        if name not in self._channels:
            self._channels[name] = grpc.aio.insecure_channel(self._server_registry[name])

        return stub_class(self._channels[name])

    async def watch(self) -> AsyncIterator[list[Service]]:
        """Stream registry updates from the manager.

        Yields a list of all registered services whenever the registry changes.
        """
        await self._ensure_connected()
        response_stream = self._manager_stub.Watch(WatchRequest())
        async for response in response_stream:
            yield [
                Service(
                    name=svc.definition.name,
                    address=svc.definition.address,
                    healthy=svc.healthy,
                    last_seen=svc.last_seen.ToDatetime(),
                )
                for svc in response.services
            ]

    async def stream_logs(self, follow: bool = True, tail: int = -1) -> AsyncIterator[LogEntry]:
        """Stream service logs from the manager.

        :param follow: whether to keep the stream open for new logs (default true)
        :param tail: how many logs from the history to include, starting from most recent.
            -1 for all (default).
        """
        await self._ensure_connected()
        request = StreamLogsRequest(follow=follow, tail=tail)
        response_stream = self._manager_stub.StreamLogs(request)
        async for response in response_stream:
            yield response.entry

    async def close(self):
        for ch in self._channels.values():
            await ch.close()
        if self._manager_channel:
            await self._manager_channel.close()
        self._channels.clear()
        self._server_registry.clear()
        self._connected = False

    async def __aenter__(self):
        await self._ensure_connected()
        return self

    async def __aexit__(self, *exc):
        await self.close()


class ServiceNotFoundError(Exception):
    def __init__(self, name: str, available: list[str]):
        super().__init__(f"Service '{name}' not found. Available: {available}")
