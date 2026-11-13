import pytest
from unittest.mock import AsyncMock

from state import ClientWebsockets


class DeadSocket:
    closed = False

    async def send_json(self, data):
        raise ConnectionResetError

    async def close(self):
        self.closed = True


@pytest.mark.asyncio
async def test_broadcast_drops_a_client_whose_connection_died():
    clients = ClientWebsockets()
    dead = DeadSocket()
    clients.add(1, dead)
    await clients.broadcast(1, {"type": "BEST_SHARE_UPDATE"})
    assert dead.closed
    await clients.broadcast(1, {"type": "BEST_SHARE_UPDATE"})  # plus de client: rien à envoyer


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
