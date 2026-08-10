from prisma import Prisma
import pytest
from datetime import datetime
from src.rules.Referee import Referee


@pytest.mark.asyncio
async def test_hits_diff(prisma_tx: Prisma, referee: Referee):
    battle = await prisma_tx.battles.create(
        data={
            "contender_1_address": "bc1",
            "contender_2_address": "bc2",
            "contenders_pv": 100,
            "rounds": 21,
            "owner_user_id": 1,
            "start_height": 400,
            "id": 1,
            "contender_1_name": "bc1",
            "contender_2_name": "bc2",
        }
    )

    await prisma_tx.rounds.create_many(
        data=[
            {"battle_id": 1, "contender_1_best_diff": 5, "contender_2_best_diff": 3, "winner": 1, "finalized_at": datetime(2026, 2, 1, 10, 30), "block_height": 401},
            {"battle_id": 1, "contender_1_best_diff": 1, "contender_2_best_diff": 4, "winner": 2, "finalized_at": datetime(2026, 2, 1, 10, 40), "block_height": 402},
            {"battle_id": 1, "contender_1_best_diff": 1, "contender_2_best_diff": 6, "winner": 2, "finalized_at": datetime(2026, 2, 1, 10, 50), "block_height": 403},
            {"battle_id": 1, "contender_1_best_diff": 1, "contender_2_best_diff": 6, "block_height": 404},
        ]
    )

    pv1, pv2 = await referee.compute_pv(battle)

    assert pv1 == 98
    assert pv2 == 99

@pytest.mark.asyncio
async def test_hits_one_unfinalized_diff(prisma_tx: Prisma, referee: Referee):
    battle = await prisma_tx.battles.create(
        data={
            "contender_1_address": "bc1",
            "contender_2_address": "bc2",
            "contenders_pv": 100,
            "rounds": 21,
            "owner_user_id": 1,
            "start_height": 400,
            "id": 1,
            "contender_1_name": "bc1",
            "contender_2_name": "bc2",
        }
    )

    await prisma_tx.rounds.create_many(
        data=[
            {"battle_id": 1, "contender_1_best_diff": 1, "contender_2_best_diff": 6, "block_height": 404},
        ]
    )

    pv1, pv2 = await referee.compute_pv(battle)

    assert pv1 == 100
    assert pv2 == 100