import asyncio
import logging
import queue
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import grpc
from google.protobuf.timestamp_pb2 import Timestamp
from h2pcontrol.manager.v1.manager_pb2 import (
    Level,
    LogRequest,
)

if TYPE_CHECKING:
    from h2pcontrol.manager.v1.manager_pb2_grpc import ManagerServiceAsyncStub

logger = logging.getLogger(__name__)

_MAX_QUEUE_SIZE = 4096


class GrpcLogHandler(logging.Handler):
    LEVEL_MAP = {
        logging.DEBUG: Level.LEVEL_DEBUG,
        logging.INFO: Level.LEVEL_INFO,
        logging.WARNING: Level.LEVEL_WARN,
        logging.ERROR: Level.LEVEL_ERROR,
        logging.CRITICAL: Level.LEVEL_ERROR,
    }

    def __init__(self, service_name: str) -> None:
        super().__init__()
        self.service_name = service_name
        self._closed = False
        self._queue: queue.Queue[LogRequest | None] = queue.Queue(maxsize=_MAX_QUEUE_SIZE)

    async def _generate(self):
        while True:
            record = await asyncio.to_thread(self._queue.get)
            if record is None:
                return
            yield record

    async def run(self, stub: "ManagerServiceAsyncStub") -> None:
        """Stream logs to the manager. Blocks until the stream ends or is cancelled."""
        try:
            await stub.Log(self._generate())
        except grpc.RpcError as e:
            self._closed = True  # need to set before logging
            logger.warning("Log stream ended with error: %s", e)
        finally:
            self._closed = True

    def emit(self, record):
        if self._closed:
            return
        proto_level = self.LEVEL_MAP.get(record.levelno, Level.LEVEL_UNSPECIFIED)
        ts = Timestamp()
        ts.FromDatetime(datetime.fromtimestamp(record.created, tz=timezone.utc))
        try:
            self._queue.put_nowait(
                LogRequest(
                    service_name=self.service_name,
                    level=proto_level,
                    message=self.format(record),
                    timestamp=ts,
                )
            )
        except queue.Full:
            pass  # drop the log rather than block or leak memory

    def close(self):
        """Shut down the handler and stop the generator."""
        self._closed = True
        try:
            self._queue.put_nowait(None)
        except queue.Full:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                pass
            try:
                self._queue.put_nowait(None)
            except queue.Full:
                pass
        super().close()
