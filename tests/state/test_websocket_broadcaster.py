from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.event_dispatcher.WebsocketBroadcaster import WebsocketBroadcaster


@pytest.mark.asyncio
@pytest.mark.parametrize("event", ["new_share", "new_best_share", "new_round", "hit_result"])
async def test_block_height_is_an_integer_in_all_events(event):
    broadcaster = WebsocketBroadcaster()
    broadcaster.client_websockets = SimpleNamespace(broadcast=AsyncMock())
    battle = SimpleNamespace(id=1)
    height = 970429
    payload = SimpleNamespace(
        block_height=height, sdiff=42, share_id="share-1",
        created_at=SimpleNamespace(isoformat=lambda: "2026-11-20T12:00:00"),
    )

    if event == "hit_result":
        await broadcaster.hit_result(battle, 1, height, 42, 21, 100, 90)
    elif event == "new_round":
        await broadcaster.new_round(battle, 2, payload)
    else:
        await getattr(broadcaster, event)(battle, "contender_1", payload)

    battle_id, message = broadcaster.client_websockets.broadcast.await_args.args
    assert battle_id == battle.id
    assert message["block_height"] == height
    assert type(message["block_height"]) is int
