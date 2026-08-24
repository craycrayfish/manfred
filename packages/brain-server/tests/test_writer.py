from __future__ import annotations

import asyncio

import pytest

from brain_server.writer import Writer


def test_writer_serializes_concurrent_submits():
    """Ops submitted concurrently are applied one-at-a-time, in arrival order.

    The apply callback brackets each op with an in-progress flag; if two ran
    concurrently the flag would already be set and we'd record a violation.
    """
    applied: list[int] = []
    in_progress = {"flag": False}
    violations = {"n": 0}

    def apply(op):
        if in_progress["flag"]:
            violations["n"] += 1
        in_progress["flag"] = True
        # synchronous, no awaits — to_thread runs it; the queue must still
        # guarantee one-at-a-time consumption
        applied.append(op["i"])
        in_progress["flag"] = False
        return op["i"]

    async def run():
        w = Writer(apply)
        w.start()
        results = await asyncio.gather(*(w.submit({"kind": "x", "i": i}) for i in range(50)))
        await w.stop()
        return results

    results = asyncio.run(run())
    assert results == list(range(50))   # futures resolve to their own op result
    assert applied == list(range(50))   # applied strictly in submission order
    assert violations["n"] == 0         # never two at once


def test_writer_propagates_exceptions():
    def apply(op):
        raise ValueError("boom")

    async def run():
        w = Writer(apply)
        w.start()
        try:
            with pytest.raises(ValueError, match="boom"):
                await w.submit({"kind": "x"})
        finally:
            await w.stop()

    asyncio.run(run())
