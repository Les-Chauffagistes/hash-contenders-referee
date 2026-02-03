from datetime import datetime
from prisma import Prisma
import pytest
from src.rules.Referee import Referee


@pytest.mark.asyncio
async def test_get_current_round_number_with_rounds(prisma_tx: Prisma, referee: Referee):
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
            {"battle_id": 1, "contender_1_best_diff": 1, "contender_2_best_diff": 4, "finalized_at": None, "block_height": 401},
        ]
    )

    current_round = await referee.get_current_round_number(1)

    assert current_round is not None
    assert current_round == 2

@pytest.mark.asyncio
async def test_get_current_round_number_with_one_round(prisma_tx: Prisma, referee: Referee):
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
        ]
    )

    current_round = await referee.get_current_round_number(1)

    assert current_round is not None
    assert current_round == 1

@pytest.mark.asyncio
async def test_get_current_round_number_with_no_round(prisma_tx: Prisma, referee: Referee):
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

    current_round = await referee.get_current_round_number(1)

    assert current_round is not None
    assert current_round == 0