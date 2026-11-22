import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.event_dispatcher.WebsocketBroadcaster import WebsocketBroadcaster
from src.rules.hashrate_fetch import HashrateFetch, worker_hashrate

ADDRESS = "bc1qsecretaddress"
OTHER_ADDRESS = "bc1qotheraddress"


def make_stats():
    return SimpleNamespace(
        address=ADDRESS,
        globalStats=SimpleNamespace(hashrate1m="60T"),
        workers=[
            SimpleNamespace(workername=f"{ADDRESS}.rig.1", hashrate1m="10T"),
            SimpleNamespace(workername=f"{ADDRESS}.rig2", hashrate1m="20T"),
        ],
    )


def make_battle(c1_worker=None, c2_address=OTHER_ADDRESS, c2_worker=None):
    return SimpleNamespace(
        id=7,
        contender_1_address=ADDRESS,
        contender_1_worker=c1_worker,
        contender_2_address=c2_address,
        contender_2_worker=c2_worker,
    )


def test_worker_hashrate_uses_worker_or_whole_address():
    stats = make_stats()
    assert worker_hashrate(stats, ADDRESS, None) == "60T"
    assert worker_hashrate(stats, ADDRESS, "RIG.1") == "10T"
    assert worker_hashrate(stats, ADDRESS, "unknown") is None


@pytest.mark.asyncio
async def test_hashrate_update_only_carries_contender_and_hashrate():
    broadcaster = WebsocketBroadcaster()
    broadcaster.client_websockets = SimpleNamespace(broadcast=AsyncMock())

    await broadcaster.hashrate_update(7, "contender_1", "60T")

    broadcaster.client_websockets.broadcast.assert_awaited_once_with(
        7, {"type": "HASHRATE_UPDATE", "user": "contender_1", "hashrate": "60T"}
    )


@pytest.mark.asyncio
async def test_broadcast_never_leaks_address_or_workers():
    broadcaster = WebsocketBroadcaster()
    broadcaster.client_websockets = SimpleNamespace(broadcast=AsyncMock())
    fetch = HashrateFetch()
    fetch.event_dispatcher = broadcaster
    fetch._subscribers[ADDRESS] = {7: [("contender_1", "rig.1")]}

    await fetch._broadcast(ADDRESS, make_stats())

    (battle_id, message), = [c.args for c in broadcaster.client_websockets.broadcast.await_args_list]
    assert battle_id == 7
    assert message == {"type": "HASHRATE_UPDATE", "user": "contender_1", "hashrate": "10T"}
    assert ADDRESS not in json.dumps(message)


@pytest.mark.asyncio
async def test_acquire_targets_each_contender_using_the_address():
    fetch = HashrateFetch()
    fetch.event_dispatcher = SimpleNamespace(hashrate_update=AsyncMock())
    battle = make_battle(c1_worker="rig.1", c2_address=ADDRESS, c2_worker="rig2")
    fetch._tasks[ADDRESS] = object()  # évite de démarrer un vrai poller

    fetch.acquire(ADDRESS, battle)
    await fetch._broadcast(ADDRESS, make_stats())

    calls = [c.args for c in fetch.event_dispatcher.hashrate_update.await_args_list]
    assert calls == [(7, "contender_1", "10T"), (7, "contender_2", "20T")]
