import asyncio
import logging
import queue
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from google.protobuf.timestamp_pb2 import Timestamp
from h2pcontrol.manager.v1.manager_pb2 import (
    Attr,
    AttrValue,
    Level,
    LogRequest,
)

if TYPE_CHECKING:
    from h2pcontrol.manager.v1.manager_pb2_grpc import ManagerServiceAsyncStub

logger = logging.getLogger(__name__)

_MAX_QUEUE_SIZE = 4096

# skip built-in LogRecord attributes
# http://docs.python.org/library/logging.html#logrecord-attributes
_RESERVED_ATTRS = frozenset(
    (
        "asctime",
        "args",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "message",
        "module",
        "msecs",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
        "taskName",
    )
)


def _to_attr_value(v: object) -> AttrValue:
    if isinstance(v, bool):
        return AttrValue(bool_value=v)
    if isinstance(v, int):
        return AttrValue(int_value=v)
    if isinstance(v, float):
        return AttrValue(double_value=v)
    return AttrValue(string_value=str(v))


def _get_extras(record: logging.LogRecord) -> list[Attr]:
    return [
        Attr(key=k, value=_to_attr_value(v))
        for k, v in record.__dict__.items()
        if k not in _RESERVED_ATTRS
    ]


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
        try:
            await stub.Log(self._generate())
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
                    attrs=_get_extras(record),
                )
            )
        except queue.Full:
            pass

    def close(self):
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
