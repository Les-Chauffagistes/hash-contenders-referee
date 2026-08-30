import pytest
from unittest.mock import AsyncMock
from src.rules.Referee import Referee
from pool_api_types.models import Share
from prisma import Prisma


def make_share(
    address: str,
    block_height: int,
    diff: float = 100.0,
    result: bool = True,
    errn: int = 0,
) -> Share:
    """Crée un Share de test, avec la possibilité de marquer une share invalide (result=False/errn!=0)."""
    return Share(
        workinfoid=1,
        clientid=1,
        diff=diff,
        sdiff=float(diff),
        hash="",
        result=result,
        errn=errn,
        createdate="",
        ts=0.0,
        workername="",
        username="",
        address=address,
        worker="",
        workernameAddr="",
        ip="",
        agent="",
        round=hex(block_height),
        file="",
    )


async def _make_battle(prisma_tx: Prisma):
    return await prisma_tx.battles.create(
        data={
            "id": 1,
            "rounds": 2,
            "owner_user_id": 1,
            "contender_1_address": "bc1_address",
            "contender_1_name": "Contender 1",
            "contender_2_address": "bc2_address",
            "contender_2_name": "Contender 2",
            "contenders_pv": 100,
            "start_height": 400,
        }
    )


@pytest.mark.asyncio
async def test_invalid_result_share_does_not_update_best_diff(
    prisma_tx: Prisma, referee: Referee
):
    """Une share avec result=False (rejetée par le pool) ne doit jamais devenir la meilleure share du round."""
    battle = await _make_battle(prisma_tx)
    referee.event_dispatcher = AsyncMock()

    valid = make_share("bc1_address", block_height=400, diff=50.0, result=True, errn=0)
    await referee.on_share(battle, valid)

    invalid_better = make_share("bc1_address", block_height=400, diff=500.0, result=False, errn=0)
    await referee.on_share(battle, invalid_better)

    round_row = await prisma_tx.rounds.find_unique(
        where={"battle_id_block_height": {"battle_id": battle.id, "block_height": 400}}
    )
    assert round_row is not None
    assert round_row.contender_1_best_diff == 50


@pytest.mark.asyncio
async def test_nonzero_errn_share_does_not_update_best_diff(
    prisma_tx: Prisma, referee: Referee
):
    """Une share avec errn != 0 (erreur pool) ne doit pas non plus compter, même si result=True."""
    battle = await _make_battle(prisma_tx)
    referee.event_dispatcher = AsyncMock()

    valid = make_share("bc2_address", block_height=400, diff=50.0, result=True, errn=0)
    await referee.on_share(battle, valid)

    invalid_better = make_share("bc2_address", block_height=400, diff=500.0, result=True, errn=1)
    await referee.on_share(battle, invalid_better)

    round_row = await prisma_tx.rounds.find_unique(
        where={"battle_id_block_height": {"battle_id": battle.id, "block_height": 400}}
    )
    assert round_row is not None
    assert round_row.contender_2_best_diff == 50


@pytest.mark.asyncio
async def test_invalid_share_does_not_dispatch_best_share_event(
    prisma_tx: Prisma, referee: Referee
):
    """Une share invalide ne doit pas non plus déclencher l'événement broadcasté aux clients."""
    battle = await _make_battle(prisma_tx)
    referee.event_dispatcher = AsyncMock()

    invalid = make_share("bc1_address", block_height=400, diff=500.0, result=False, errn=0)
    await referee.on_share(battle, invalid)

    referee.event_dispatcher.new_best_share.assert_not_called()
