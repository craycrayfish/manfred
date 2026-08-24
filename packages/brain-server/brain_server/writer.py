"""Single-writer queue: serializes every vault mutation.

POST handlers submit an op and await its result; one consumer task applies ops
strictly in order, so no two writes ever race on the vault files or the index.
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable

Op = dict[str, Any]
Apply = Callable[[Op], Any]


class Writer:
    def __init__(self, apply: Apply):
        self._apply = apply
        self._queue: asyncio.Queue = asyncio.Queue()
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run())

    async def _run(self) -> None:
        while True:
            op, fut = await self._queue.get()
            try:
                # Apply is synchronous (fast sqlite + file ops); run it off the
                # event loop so a slow disk never stalls request handling.
                result = await asyncio.to_thread(self._apply, op)
                if not fut.cancelled():
                    fut.set_result(result)
            except Exception as exc:  # noqa: BLE001 - propagate to the awaiter
                if not fut.cancelled():
                    fut.set_exception(exc)
            finally:
                self._queue.task_done()

    async def submit(self, op: Op) -> Any:
        fut: asyncio.Future = asyncio.get_running_loop().create_future()
        await self._queue.put((op, fut))
        return await fut

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
