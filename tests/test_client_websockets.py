from unittest.mock import AsyncMock

import pytest

from state import ClientWebsockets


@pytest.mark.asyncio
async def test_new_spectator_does_not_disconnect_existing_spectators():
    clients = ClientWebsockets()
    first, second = AsyncMock(), AsyncMock()
    clients.add("42", first)
    clients.add("42", second)

    await clients.broadcast(42, {"type": "SHARE"})
    first.send_json.assert_awaited_once_with({"type": "SHARE"})
    second.send_json.assert_awaited_once_with({"type": "SHARE"})

    clients.remove("42", first)
    await clients.broadcast(42, {"type": "ROUND_UPDATE"})
    assert first.send_json.await_count == 1
    second.send_json.assert_awaited_with({"type": "ROUND_UPDATE"})
