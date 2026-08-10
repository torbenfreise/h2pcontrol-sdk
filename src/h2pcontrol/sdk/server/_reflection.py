import logging
from collections.abc import Iterable
from typing import Any

import grpc

logger = logging.getLogger(__name__)


class ServiceNameRecorder:
    """
    Wraps a gRPC server to record the fully-qualified names of the services
    registered on it, e.g. ``h2pcontrol.mccdaq.v1.MccDaqService``.
    """

    def __init__(self, server: grpc.aio.Server) -> None:
        self._server = server
        self.service_names: list[str] = []

    def __getattr__(self, name: str) -> Any:
        return getattr(self._server, name)

    def add_generic_rpc_handlers(self, handlers: Iterable[Any]) -> None:
        handlers = tuple(handlers)
        for handler in handlers:
            if isinstance(handler, grpc.ServiceRpcHandler):
                self.service_names.append(handler.service_name())
            else:
                logger.debug("Handler %r does not report a service name", handler)
        self._server.add_generic_rpc_handlers(handlers)
