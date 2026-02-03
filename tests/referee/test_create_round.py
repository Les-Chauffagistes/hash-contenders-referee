import pytest
from src.rules.Referee import Referee
from prisma import Prisma

@pytest.mark.asyncio
async def test_create_needed_round(prisma_tx: Prisma, referee: Referee):
    battle = await prisma_tx.battles.create(
        data = {
            "id": 1,
            "rounds": 21,
            "contender_1_address": "bc1",
            "contender_1_name": "bc1",
            "contender_2_address": "bc2",
            "contender_2_name": "bc2",
            "contenders_pv": 100,
            "start_height": 400
        }
    )

    await referee._try_create_round(battle.id, 401)

    rounds = await prisma_tx.rounds.count(
        where = {
            "battle_id": battle.id
        }
    )

    assert rounds == 1

@pytest.mark.asyncio
async def test_create_not_needed_round(prisma_tx: Prisma, referee: Referee):
    battle = await prisma_tx.battles.create(
        data = {
            "id": 1,
            "rounds": 21,
            "contender_1_address": "bc1",
            "contender_1_name": "bc1",
            "contender_2_address": "bc2",
            "contender_2_name": "bc2",
            "contenders_pv": 100,
            "start_height": 400
        }
    )

    await referee._try_create_round(battle.id, 401)
    await referee._try_create_round(battle.id, 401)

    rounds = await prisma_tx.rounds.count(
        where = {
            "battle_id": battle.id
        }
    )

    assert rounds == 1