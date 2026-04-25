import asyncio
import inspect
import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, cast

import grpc
from h2pcontrol.manager.v1.manager_pb2 import (
    HeartbeatRequest,
    RegisterRequest,
    ServiceDefinition,
)

if TYPE_CHECKING:
    from h2pcontrol.manager.v1.manager_pb2_grpc import ManagerServiceAsyncStub

from h2pcontrol.manager.v1.manager_pb2_grpc import ManagerServiceStub

from h2pcontrol.sdk import H2PServerConfig as Config

logger = logging.getLogger(__name__)


class Server(ABC):
    def __init__(self, config: Config):
        self._config = config

    async def start(self):
        """Starts the service and registers with the manager."""
        async with asyncio.TaskGroup() as tg:
            tg.create_task(self._run())
            tg.create_task(self._register_and_heartbeat())

    @abstractmethod
    def healthy(self) -> bool:
        """Returns whether the service is currently healthy."""
        ...

    async def _run(self):
        server = grpc.aio.server()
        self._add_to_server(server)
        server.add_insecure_port(f"[::]:{self._config.service.port}")
        await server.start()
        await server.wait_for_termination()

    def _add_to_server(self, server: grpc.aio.Server) -> None:
        for cls in inspect.getmro(type(self)):
            if cls.__name__.endswith("Servicer"):
                module = inspect.getmodule(cls)
                fn = getattr(module, f"add_{cls.__name__}_to_server", None)
                if fn:
                    fn(self, server)
                    return
        raise RuntimeError(f"No gRPC servicer found in MRO of {type(self).__name__}")

    async def _heartbeat_requests(self) -> AsyncIterator[HeartbeatRequest]:
        while True:
            yield HeartbeatRequest(healthy=True)
            await asyncio.sleep(self._config.manager.heartbeat_interval_s)

    async def _register_and_heartbeat(self):
        while True:
            try:
                async with grpc.aio.insecure_channel(self._config.manager.address) as channel:
                    stub = cast("ManagerServiceAsyncStub", ManagerServiceStub(channel))

                    await stub.Register(
                        RegisterRequest(
                            service=ServiceDefinition(
                                name=self._config.service.name,
                                description=self._config.service.description,
                                port=self._config.service.port,
                            )
                        ),
                        timeout=10,
                    )
                    logger.info("Registered with manager at %s", self._config.manager.address)

                    async for _ in stub.Heartbeat(self._heartbeat_requests()):
                        logger.debug("Heartbeat acknowledged")

            except grpc.aio.AioRpcError as e:
                retry_interval = self._config.manager.heartbeat_interval_s

                logger.warning(
                    "Manager unreachable, retrying in %ds: %s", retry_interval, e.details()
                )
                await asyncio.sleep(retry_interval)
