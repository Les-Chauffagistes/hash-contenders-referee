import pytest
from unittest.mock import AsyncMock
from src.rules.Referee import Referee
from pool_api_types.models import Share
from prisma import Prisma


def make_share(address: str, block_height: int, diff: float = 100.0) -> Share:
    return Share(
        workinfoid=1, clientid=1, diff=diff, sdiff=float(diff),
        hash="", result=True, errn=0, createdate="", ts=0.0,
        workername="", username="", address=address, worker="",
        workernameAddr="", ip="", agent="", round=hex(block_height), file="",
    )


async def create_battle(prisma_tx: Prisma, rounds: int = 10, contenders_pv: int = 10):
    return await prisma_tx.battles.create(
        data={
            "id": 1, "rounds": rounds,
            "contender_1_address": "bc1_address", "contender_1_name": "Contender 1",
            "contender_2_address": "bc2_address", "contender_2_name": "Contender 2",
            "contenders_pv": contenders_pv, "start_height": 400,
        }
    )


@pytest.mark.asyncio
async def test_round_not_finalized_when_only_contender_1_confirmed_next_block(
    prisma_tx: Prisma, referee: Referee
):
    """Round N reste ouvert si seulement C1 a soumis pour N+1 (C2 pas encore confirmé)"""
    battle = await create_battle(prisma_tx)
    referee.event_dispatcher = AsyncMock()

    await referee.on_share(battle, make_share("bc1_address", 400, diff=200))
    await referee.on_share(battle, make_share("bc2_address", 400, diff=100))

    await referee.on_share(battle, make_share("bc1_address", 401, diff=100))

    round_400 = await prisma_tx.rounds.find_unique(
        where={"battle_id_block_height": {"battle_id": battle.id, "block_height": 400}}
    )
    assert round_400.finalized_at is None


@pytest.mark.asyncio
async def test_round_not_finalized_when_only_contender_2_confirmed_next_block(
    prisma_tx: Prisma, referee: Referee
):
    """Round N reste ouvert si seulement C2 a soumis pour N+1 (C1 pas encore confirmé)"""
    battle = await create_battle(prisma_tx)
    referee.event_dispatcher = AsyncMock()

    await referee.on_share(battle, make_share("bc1_address", 400, diff=200))
    await referee.on_share(battle, make_share("bc2_address", 400, diff=100))

    await referee.on_share(battle, make_share("bc2_address", 401, diff=100))

    round_400 = await prisma_tx.rounds.find_unique(
        where={"battle_id_block_height": {"battle_id": battle.id, "block_height": 400}}
    )
    assert round_400.finalized_at is None


@pytest.mark.asyncio
async def test_round_finalized_once_both_contenders_confirmed_next_block(
    prisma_tx: Prisma, referee: Referee
):
    """Round N est finalisé une fois que les deux ont confirmé N+1, via le trigger N+2"""
    battle = await create_battle(prisma_tx)
    referee.event_dispatcher = AsyncMock()

    await referee.on_share(battle, make_share("bc1_address", 400, diff=200))
    await referee.on_share(battle, make_share("bc2_address", 400, diff=100))

    await referee.on_share(battle, make_share("bc1_address", 401, diff=100))
    await referee.on_share(battle, make_share("bc2_address", 401, diff=100))

    # Pas encore finalisé : les deux ont confirmé 401 mais aucun share au 402 n'a déclenché
    round_400 = await prisma_tx.rounds.find_unique(
        where={"battle_id_block_height": {"battle_id": battle.id, "block_height": 400}}
    )
    assert round_400.finalized_at is None

    await referee.on_share(battle, make_share("bc1_address", 402, diff=100))

    round_400_updated = await prisma_tx.rounds.find_unique(
        where={"battle_id_block_height": {"battle_id": battle.id, "block_height": 400}}
    )
    assert round_400_updated.finalized_at is not None
    assert round_400_updated.winner == 1


@pytest.mark.asyncio
async def test_draw_sets_winner_to_null(prisma_tx: Prisma, referee: Referee):
    """Un round avec diffs égales produit winner = NULL"""
    battle = await create_battle(prisma_tx)
    referee.event_dispatcher = AsyncMock()

    await referee.on_share(battle, make_share("bc1_address", 400, diff=100))
    await referee.on_share(battle, make_share("bc2_address", 400, diff=100))

    await referee.on_share(battle, make_share("bc1_address", 401, diff=100))
    await referee.on_share(battle, make_share("bc2_address", 401, diff=100))
    await referee.on_share(battle, make_share("bc1_address", 402, diff=100))

    round_400 = await prisma_tx.rounds.find_unique(
        where={"battle_id_block_height": {"battle_id": battle.id, "block_height": 400}}
    )
    assert round_400.finalized_at is not None
    assert round_400.winner is None


@pytest.mark.asyncio
async def test_multiple_rounds_finalized_at_once(prisma_tx: Prisma, referee: Referee):
    """Plusieurs rounds en attente sont tous finalisés en un seul UPDATE quand le trigger arrive"""
    battle = await create_battle(prisma_tx)
    referee.event_dispatcher = AsyncMock()

    # Injecter directement 3 rounds avec les deux diffs (simule un backlog sans trigger intermédiaire)
    for block, c1, c2 in [(400, 200, 100), (401, 150, 180), (402, 120, 90)]:
        await prisma_tx.rounds.create(
            data={"battle_id": battle.id, "block_height": block,
                  "contender_1_best_diff": c1, "contender_2_best_diff": c2}
        )

    # Round 403 avec les deux diffs rend les trois rounds précédents finalisables
    await prisma_tx.rounds.create(
        data={"battle_id": battle.id, "block_height": 403,
              "contender_1_best_diff": 100, "contender_2_best_diff": 100}
    )

    finalized = await referee.finalize_rounds(battle.id, 404)

    assert len(finalized) == 3
    by_height = {r["block_height"]: r for r in finalized}
    assert set(by_height.keys()) == {400, 401, 402}
    assert by_height[400]["winner"] == 1  # 200 > 100
    assert by_height[401]["winner"] == 2  # 150 < 180
    assert by_height[402]["winner"] == 1  # 120 > 90