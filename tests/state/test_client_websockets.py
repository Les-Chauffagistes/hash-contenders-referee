import pytest

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
