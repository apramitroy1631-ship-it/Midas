# app/core/log_capture.py
"""Persists application log records to Mongo so Settings > Developer Logs has something to show.

Writes go through a background thread and are best-effort: a Mongo hiccup here must
never affect the request/log call that triggered it, so all failures are swallowed.
"""
from __future__ import annotations

import logging
import queue
import threading
import time
from datetime import datetime, timezone

from app.tenancy.context import current_tenant_or_none

_QUEUE: "queue.Queue[dict]" = queue.Queue(maxsize=5000)
_MAX_ENTRIES = 5000


class MongoLogHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            tenant_id = current_tenant_or_none()
        except Exception:
            tenant_id = None
        entry = {
            "created_at": datetime.now(timezone.utc),
            "category": record.name,
            "level": record.levelname,
            "message": self.format(record),
            "tenant_id": tenant_id,
        }
        try:
            _QUEUE.put_nowait(entry)
        except queue.Full:
            pass


def _writer_loop() -> None:
    from app.db.mongo import raw

    coll = raw("logs")
    buffer: list[dict] = []
    flushes = 0
    while True:
        try:
            entry = _QUEUE.get(timeout=1.0)
            buffer.append(entry)
            while len(buffer) < 50:
                buffer.append(_QUEUE.get_nowait())
        except queue.Empty:
            pass
        if not buffer:
            continue
        try:
            coll.insert_many(buffer, ordered=False)
            flushes += 1
            # Trim occasionally rather than every flush - exact count isn't critical.
            if flushes % 20 == 0:
                total = coll.count_documents({})
                overflow = total - _MAX_ENTRIES
                if overflow > 0:
                    stale = list(
                        coll.find({}, {"_id": 1}).sort("created_at", 1).limit(overflow)
                    )
                    if stale:
                        coll.delete_many({"_id": {"$in": [d["_id"] for d in stale]}})
        except Exception:
            pass
        buffer.clear()


_started = False


def start_log_capture(level: int = logging.INFO) -> None:
    """Attach the Mongo handler to the root logger and start the background writer.

    Safe to call more than once - only wires up on the first call.
    """
    global _started
    if _started:
        return
    _started = True

    handler = MongoLogHandler()
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logging.getLogger().addHandler(handler)

    thread = threading.Thread(target=_writer_loop, name="log-capture-writer", daemon=True)
    thread.start()
