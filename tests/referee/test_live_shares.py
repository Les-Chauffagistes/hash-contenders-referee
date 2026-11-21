from unittest.mock import AsyncMock

import pytest

from tests.factories import make_share


@pytest.mark.asyncio
async def test_every_valid_share_is_broadcast_even_without_a_new_record(prisma_tx, referee):
    battle = await prisma_tx.battles.create(data={
        "id": 1, "rounds": 2, "owner_user_id": 1,
        "contender_1_address": "bc1", "contender_1_name": "One",
        "contender_2_address": "bc2", "contender_2_name": "Two",
        "contenders_pv": 100, "start_height": 400,
    })
    referee.event_dispatcher = AsyncMock()
    await referee.on_share(battle, make_share("bc1", 400, diff=50))
    await referee.on_share(battle, make_share("bc1", 400, diff=10))
    await referee.on_share(battle, make_share("bc1", 400, diff=100, result=False))

    assert referee.event_dispatcher.new_share.await_count == 2
    assert referee.event_dispatcher.new_best_share.await_count == 1
