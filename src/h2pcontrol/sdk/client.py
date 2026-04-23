from typing import TYPE_CHECKING, Callable, TypeVar, cast

import grpc
from h2pcontrol.manager.v1.manager_pb2 import ListRequest

if TYPE_CHECKING:
    from h2pcontrol.manager.v1.manager_pb2_grpc import ManagerServiceAsyncStub, ManagerServiceStub
TStub = TypeVar("TStub")


class Client:
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
        response = await self._manager_stub.List(ListRequest())
        self._server_registry = {
            service.definition.name: f"{service.host}:{service.definition.port}"
            for service in response.services
        }

    async def device(self, name: str, stub_class: Callable[[grpc.aio.Channel], TStub]) -> TStub:
        """Get a ready-to-use gRPC stub for a named device."""
        await self._ensure_connected()

        if name not in self._server_registry:
            await self._refresh_registry()
            if name not in self._server_registry:
                raise DeviceNotFoundError(name, list(self._server_registry.keys()))

        if name not in self._channels:
            self._channels[name] = grpc.aio.insecure_channel(self._server_registry[name])

        return stub_class(self._channels[name])

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


class DeviceNotFoundError(Exception):
    def __init__(self, name, available):
        super().__init__(f"Device '{name}' not found. Available: {available}")
