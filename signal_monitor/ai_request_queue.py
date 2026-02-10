from __future__ import annotations

import logging
import os
import queue
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Optional, TypeVar

T = TypeVar("T")

logger = logging.getLogger(__name__)


@dataclass
class _Task:
    func: Callable[[], T]
    attempts: int
    retry_delay: float
    result: Optional[T] = None
    error: Optional[BaseException] = None
    event: threading.Event = field(default_factory=threading.Event)


_TASK_QUEUE: "queue.Queue[_Task]" = queue.Queue()
_WORKER_STARTED = False
_WORKER_LOCK = threading.Lock()
_RATE_LOCK = threading.Lock()
_LAST_REQUEST_TS = 0.0
_COOLDOWN_UNTIL = 0.0
_LAST_429_TS = 0.0

_LEGACY_MIN_INTERVAL = float(os.getenv("NOFX_AI_QUEUE_MIN_INTERVAL_SEC", "2.0") or 2.0)
_MIN_INTERVAL_FAST_SEC = float(os.getenv("NOFX_AI_QUEUE_MIN_INTERVAL_FAST_SEC", "") or 0.0)
_MIN_INTERVAL_SLOW_SEC = float(os.getenv("NOFX_AI_QUEUE_MIN_INTERVAL_SLOW_SEC", "") or 0.0)
_RECOVER_AFTER_SEC = float(os.getenv("NOFX_AI_QUEUE_RECOVER_SEC", "600") or 600.0)
_COOLDOWN_ON_429_SEC = float(os.getenv("NOFX_AI_QUEUE_429_COOLDOWN_SEC", "20") or 20.0)
_RETRY_429_WAIT_SEC = float(os.getenv("NOFX_AI_RETRY_429_WAIT_SEC", "20") or 20.0)
_MAX_RETRIES = int(os.getenv("NOFX_AI_MAX_RETRIES", "3") or 3)
_DEFAULT_ATTEMPTS = max(1, _MAX_RETRIES + 1)

if _MIN_INTERVAL_FAST_SEC <= 0:
    _MIN_INTERVAL_FAST_SEC = _LEGACY_MIN_INTERVAL
if _MIN_INTERVAL_SLOW_SEC <= 0:
    _MIN_INTERVAL_SLOW_SEC = max(_MIN_INTERVAL_FAST_SEC, 10.0)

_CURRENT_MIN_INTERVAL = _MIN_INTERVAL_FAST_SEC


_NUM_WORKERS = int(os.getenv("NOFX_AI_QUEUE_WORKERS", "3") or 3)


def _ensure_worker() -> None:
    global _WORKER_STARTED
    if _WORKER_STARTED:
        return
    with _WORKER_LOCK:
        if _WORKER_STARTED:
            return
        for i in range(_NUM_WORKERS):
            thread = threading.Thread(target=_worker, daemon=True, name=f"AIWorker-{i+1}")
            thread.start()
        _WORKER_STARTED = True
        logger.info(f"Started {_NUM_WORKERS} AI request worker threads")


_MAX_BACKOFF_SEC = 300.0


def _calculate_backoff(attempt: int) -> float:
    return _RETRY_429_WAIT_SEC


def _is_429_error(exc: BaseException) -> bool:
    msg = str(exc).lower()
    tokens = ("429", "too many requests", "capacity", "no capacity")
    return any(token in msg for token in tokens)


def _sleep_until_ready() -> None:
    global _LAST_REQUEST_TS, _CURRENT_MIN_INTERVAL
    with _RATE_LOCK:
        now = time.time()
        if _LAST_429_TS and (now - _LAST_429_TS) >= _RECOVER_AFTER_SEC:
            _CURRENT_MIN_INTERVAL = _MIN_INTERVAL_FAST_SEC
        wait_for = 0.0
        if now < _COOLDOWN_UNTIL:
            wait_for = _COOLDOWN_UNTIL - now
        min_wait = (_LAST_REQUEST_TS + _CURRENT_MIN_INTERVAL) - now
        if min_wait > wait_for:
            wait_for = min_wait
        if wait_for > 0:
            time.sleep(wait_for)
        _LAST_REQUEST_TS = time.time()


def _worker() -> None:
    while True:
        task = _TASK_QUEUE.get()
        try:
            last_error: Optional[BaseException] = None
            attempts = max(1, int(task.attempts))
            for attempt in range(1, attempts + 1):
                try:
                    _sleep_until_ready()
                    result = task.func()
                    if result is None or result == "":
                        logger.warning("AI returned empty response (attempt %d/%d)", attempt, attempts)
                        task.result = None
                    else:
                        task.result = result
                    task.error = None
                    break
                except Exception as exc:
                    last_error = exc
                    if _is_429_error(exc):
                        with _RATE_LOCK:
                            global _COOLDOWN_UNTIL
                            _COOLDOWN_UNTIL = max(_COOLDOWN_UNTIL, time.time() + _COOLDOWN_ON_429_SEC)
                            global _LAST_429_TS
                            _LAST_429_TS = time.time()
                            global _CURRENT_MIN_INTERVAL
                            _CURRENT_MIN_INTERVAL = _MIN_INTERVAL_SLOW_SEC
                        logger.warning(
                            "AI 429 detected. Cooling down for %.1fs (min interval %.1fs).",
                            _COOLDOWN_ON_429_SEC,
                            _MIN_INTERVAL_SLOW_SEC,
                        )
                    if attempt < attempts:
                        if _is_429_error(exc):
                            backoff = _calculate_backoff(attempt)
                            logger.info("429 backoff: sleeping %.1fs before retry %d/%d", backoff, attempt + 1, attempts)
                            time.sleep(backoff)
                        else:
                            time.sleep(task.retry_delay * attempt)
                        continue
                    task.error = exc
            if task.result is None and task.error is None and last_error is not None:
                task.error = last_error
        finally:
            task.event.set()
            _TASK_QUEUE.task_done()


def call_ai_with_queue(
    func: Callable[[], T],
    attempts: int = _DEFAULT_ATTEMPTS,
    retry_delay: float = 2.0,
    raise_on_error: bool = False,
) -> Optional[T]:
    _ensure_worker()
    task = _Task(func=func, attempts=attempts, retry_delay=retry_delay)
    _TASK_QUEUE.put(task)
    task.event.wait()
    if task.error:
        if raise_on_error:
            raise task.error
        logger.warning("AI request failed after %s attempts: %s", task.attempts, task.error)
        return None
    return task.result
