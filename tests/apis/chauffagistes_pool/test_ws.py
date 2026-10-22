import asyncio
import json
from urllib.parse import parse_qs, urlparse

import pytest
import pytest_asyncio
import websockets

from src.apis.chauffagistes_pool.ws import WebsocketWrapper
from tests.factories import make_share


def share_msg(seq: int, epoch: int = 1) -> dict:
    share = make_share("bc1", 800000, worker="rig")
    share.epoch, share.seq, share.share_id = epoch, seq, f"test:0/0.sharelog:{epoch * 1000 + seq}"
    return share.model_dump(mode="json")


class FakeCursor:
    """Même interface que StreamCursor, en mémoire (le vrai est testé contre Postgres dans tests/database)."""

    def __init__(self, stored=None):
        self.stored, self.gaps, self.events = stored, 0, []

    async def load(self):
        return self.stored

    async def init(self, cursor):
        self.events.append(("init", cursor))
        self.stored = self.stored or cursor

    async def advance(self, cursor, gap=False):
        if self.stored is None or cursor > self.stored:
            self.stored = cursor
            self.gaps += int(gap)

    async def mark_gap(self):
        self.events.append(("mark_gap", None))
        self.gaps += 1

    async def reset(self, cursor):
        self.events.append(("reset", cursor))
        self.stored = cursor


class FakePool:
    """Serveur WS du pool. Une entrée de `connections` par connexion attendue:
    {"head": "1:100", "send": [seq...], "close": code | None, "unfiltered": bool}. Les shares envoyés avec un `from` sont filtrés
    comme le fait le vrai pool (strictement après le curseur)."""

    def __init__(self, connections):
        self.connections = list(connections)
        self.requests: list[str] = []

    @property
    def froms(self):
        return [parse_qs(urlparse(path).query).get("from", [None])[0] for path in self.requests]

    async def handler(self, ws):
        self.requests.append(ws.request.path)
        script = self.connections.pop(0) if self.connections else {"send": []}
        start = self.froms[-1]
        await ws.send(json.dumps({"type": "hello", "cursor": start or script.get("head", "1:0"), "head": script.get("head", "1:0")}))
        after = parse_qs(urlparse(ws.request.path).query).get("from")
        floor = tuple(int(x) for x in after[0].split(":")) if after else None
        for seq in script.get("send", []):
            if floor is None or script.get("unfiltered") or (1, seq) > floor:
                await ws.send(json.dumps({"type": "share", **share_msg(seq)}))
        await ws.send(json.dumps({"type": "heartbeat", "time": "2026-10-22T00:00:00+00:00"}))
        await ws.send(json.dumps({"type": "watermark", "watermark": "2026-10-22T00:00:00+00:00"}))
        if script.get("close"):
            await ws.close(script["close"])
        else:
            await ws.wait_closed()


@pytest_asyncio.fixture
async def start_pool():
    servers = []

    async def start(connections):
        pool = FakePool(connections)
        server = await websockets.serve(pool.handler, "127.0.0.1", 0)
        servers.append(server)
        pool.uri = f"ws://127.0.0.1:{server.sockets[0].getsockname()[1]}/v1/shares/stream?address=bc1"
        return pool

    yield start
    for server in servers:
        server.close()
        await server.wait_closed()


class Recorder:
    def __init__(self, fail_times=0, always_fail=False, delay=0.0):
        self.seqs, self.fail_times, self.always_fail, self.delay = [], fail_times, always_fail, delay

    async def __call__(self, share):
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.always_fail or self.fail_times > 0:
            self.fail_times -= 1
            raise RuntimeError("boom")
        self.seqs.append(share.seq)


async def run(pool, on_message, cursor, until, **kwargs):
    kwargs = {"retry_delay": 0.01, "reconnect_delay": 0.05, **kwargs}
    wrapper = WebsocketWrapper(pool.uri, on_message, cursor, **kwargs)
    task = asyncio.create_task(wrapper.continuous_listener())
    try:
        async with asyncio.timeout(10):
            while not until():
                await asyncio.sleep(0.02)
    finally:
        await wrapper.stop()
        await asyncio.wait_for(task, 5)


@pytest.mark.asyncio
async def test_first_connection_goes_live_and_stores_the_starting_point(start_pool):
    pool = await start_pool([{"head": "1:100", "send": [101, 102]}])
    cursor, rec = FakeCursor(), Recorder()
    await run(pool, rec, cursor, lambda: rec.seqs == [101, 102])
    assert pool.froms[0] is None
    assert cursor.events[0] == ("init", (1, 100))
    assert cursor.stored == (1, 102)


@pytest.mark.asyncio
async def test_resumes_from_the_cursor_stored_in_db_and_skips_what_was_processed(start_pool):
    pool = await start_pool([{"head": "1:9", "send": [4, 5, 6, 7]}])
    cursor, rec = FakeCursor(stored=(1, 5)), Recorder()
    await run(pool, rec, cursor, lambda: rec.seqs == [6, 7])
    assert pool.froms == ["1:5"]
    assert cursor.stored == (1, 7)


@pytest.mark.asyncio
async def test_duplicates_at_or_before_the_cursor_are_ignored(start_pool):
    # un pool qui rejoue plus que demandé (au moins une fois): le garde-fou monotone filtre
    pool = await start_pool([{"head": "1:7", "send": [3, 5, 5, 6, 6, 7], "unfiltered": True}])
    cursor, rec = FakeCursor(stored=(1, 5)), Recorder()
    await run(pool, rec, cursor, lambda: rec.seqs == [6, 7])
    assert rec.seqs == [6, 7]


@pytest.mark.asyncio
async def test_reconnects_from_the_db_cursor_after_a_drop_and_catches_up(start_pool):
    pool = await start_pool([
        {"head": "1:0", "send": [1, 2, 3], "close": 1011},
        {"head": "1:6", "send": [1, 2, 3, 4, 5, 6]},
    ])
    cursor, rec = FakeCursor(stored=(1, 0)), Recorder()
    await run(pool, rec, cursor, lambda: rec.seqs == [1, 2, 3, 4, 5, 6])
    assert pool.froms == ["1:0", "1:3"]


@pytest.mark.asyncio
async def test_failed_share_is_retried_without_losing_it(start_pool):
    pool = await start_pool([{"head": "1:0", "send": [1, 2]}])
    cursor, rec = FakeCursor(stored=(1, 0)), Recorder(fail_times=2)
    await run(pool, rec, cursor, lambda: rec.seqs == [1, 2])
    assert cursor.gaps == 0 and cursor.stored == (1, 2)


@pytest.mark.asyncio
async def test_share_failing_every_attempt_is_abandoned_and_counted_as_a_gap(start_pool):
    pool = await start_pool([{"head": "1:0", "send": [1]}])
    cursor, rec = FakeCursor(stored=(1, 0)), Recorder(always_fail=True)
    await run(pool, rec, cursor, lambda: cursor.stored == (1, 1), process_attempts=3)
    assert cursor.gaps == 1


@pytest.mark.asyncio
async def test_cursor_is_not_advanced_while_a_share_is_still_being_processed(start_pool):
    pool = await start_pool([{"head": "1:0", "send": [1]}])
    cursor = FakeCursor(stored=(1, 0))
    seen = []

    async def slow(share):
        await asyncio.sleep(0.3)
        seen.append(cursor.stored)  # lu AVANT l'avance du curseur

    await run(pool, slow, cursor, lambda: cursor.stored == (1, 1))
    assert seen == [(1, 0)]


@pytest.mark.asyncio
async def test_out_of_retention_marks_a_gap_and_restarts_live_with_a_reset(start_pool):
    pool = await start_pool([
        {"head": "1:900", "send": [], "close": 4410},
        {"head": "1:900", "send": [901]},
    ])
    cursor, rec = FakeCursor(stored=(1, 5)), Recorder()
    await run(pool, rec, cursor, lambda: rec.seqs == [901])
    assert pool.froms == ["1:5", None]
    assert [e[0] for e in cursor.events] == ["mark_gap", "reset"]
    assert cursor.events[1][1] == (1, 900)
    assert cursor.stored == (1, 901)


@pytest.mark.asyncio
async def test_full_queue_reconnects_from_the_cursor_and_eventually_processes_everything(start_pool):
    seqs = list(range(1, 21))
    pool = await start_pool([{"head": "1:20", "send": seqs}] * 20)
    cursor, rec = FakeCursor(stored=(1, 0)), Recorder(delay=0.02)
    await run(pool, rec, cursor, lambda: cursor.stored == (1, 20), queue_size=3)
    assert rec.seqs == seqs  # ni trou, ni doublon, dans l'ordre
    assert len(pool.requests) > 1
