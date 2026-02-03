from datetime import datetime
from prisma import Prisma

import pytest
from src.rules.Referee import Referee


@pytest.mark.asyncio
async def test_get_current_round(prisma_tx: Prisma):
    referee = Referee()
    referee.prisma = prisma_tx

    await prisma_tx.battles.create(
        data={
            "contender_1_address": "bc1",
            "contender_2_address": "bc2",
            "contenders_pv": 100,
            "rounds": 21,
            "start_height": 400,
            "id": 1,
            "contender_1_name": "bc1",
            "contender_2_name": "bc2",
        }
    )

    await prisma_tx.rounds.create_many(
        data=[
            {"battle_id": 1, "contender_1_best_diff": 5, "contender_2_best_diff": 3, "finalized_at": datetime(2026, 2, 1, 10, 30), "block_height": 400},
            {"battle_id": 1, "contender_1_best_diff": 1, "contender_2_best_diff": 4, "finalized_at": datetime(2026, 2, 1, 10, 40), "block_height": 401},
        ]
    )

    current_round = await referee.get_current_round(1)

    assert current_round is not None
    assert current_round.block_height == 401

@pytest.mark.asyncio
async def test_get_current_round_when_no_hits(prisma_tx: Prisma):
    referee = Referee()
    referee.prisma = prisma_tx

    await prisma_tx.battles.create(
        data={
            "contender_1_address": "bc1",
            "contender_2_address": "bc2",
            "contenders_pv": 100,
            "rounds": 21,
            "start_height": 400,
            "id": 1,
            "contender_1_name": "bc1",
            "contender_2_name": "bc2",
        }
    )

    current_round = await referee.get_current_round(1)
    assert current_round is None

@pytest.mark.asyncio
async def test_get_current_round_when_has_not_started(prisma_tx: Prisma):
    referee = Referee()
    referee.prisma = prisma_tx

    await prisma_tx.battles.create(
        data={
            "contender_1_address": "bc1",
            "contender_2_address": "bc2",
            "contenders_pv": 100,
            "rounds": 21,
            "id": 1,
            "start_height": 300,
            "contender_1_name": "bc1",
            "contender_2_name": "bc2",
        }
    )

    current_round = await referee.get_current_round(1)

    assert current_round == None