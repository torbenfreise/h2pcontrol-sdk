# h2pcontrol/server.py
import asyncio
import logging
from abc import ABC, abstractmethod

import grpc
from h2pcontrol.manager.v1.manager_pb2 import (
    RegisterRequest,
    ServiceDefinition,
    HeartbeatRequest,
)
from h2pcontrol.manager.v1.manager_pb2_grpc import ManagerServiceAsyncStub
from h2pcontrol.config import H2PServerConfig

logger = logging.getLogger(__name__)


class Server(ABC):
    def __init__(self, config: H2PServerConfig):
        self._config = config

    @abstractmethod
    async def run(self):
        """Implement your gRPC server here."""
        ...

    async def start(self):
        """Starts the service and registers with the manager."""
        await asyncio.gather(
            self.run(),
            self._register_and_heartbeat(),
        )

    async def _register_and_heartbeat(self):
        async with grpc.aio.insecure_channel(self._config.manager.address) as channel:
            stub = ManagerServiceAsyncStub(channel)

            await stub.Register(
                RegisterRequest(
                    service=ServiceDefinition(
                        name=self._config.service.name,
                        description=self._config.service.description,
                        port=self._config.service.port,
                    )
                )
            )
            logger.info(f"Registered with manager at {self._config.manager.address}")

            async def heartbeat_requests():
                while True:
                    yield HeartbeatRequest(healthy=True)
                    await asyncio.sleep(self._config.manager.heartbeat_interval_s)

            async for _ in stub.Heartbeat(heartbeat_requests()):
                logger.debug("Heartbeat acknowledged")