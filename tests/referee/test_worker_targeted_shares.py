import pytest
from unittest.mock import AsyncMock
from src.rules.Referee import Referee
from pool_api_types.models import Share
from prisma import Prisma


def make_share(
    address: str,
    block_height: int,
    worker: str = "",
    diff: float = 100.0,
) -> Share:
    return Share(
        workinfoid=1,
        clientid=1,
        diff=diff,
        sdiff=float(diff),
        hash="",
        result=True,
        errn=0,
        createdate="",
        ts=0.0,
        workername="",
        username="",
        address=address,
        worker=worker,
        workernameAddr="",
        ip="",
        agent="",
        round=hex(block_height),
        file="",
    )


async def _make_battle(prisma_tx: Prisma, **overrides):
    data = {
        "id": 1,
        "rounds": 10,
        "owner_user_id": 1,
        "contender_1_address": "shared_address",
        "contender_1_name": "Contender 1",
        "contender_2_address": "shared_address",
        "contender_2_name": "Contender 2",
        "contenders_pv": 100,
        "start_height": 400,
    }
    data.update(overrides)
    return await prisma_tx.battles.create(data=data)


@pytest.mark.asyncio
async def test_shares_from_same_address_are_routed_by_worker(
    prisma_tx: Prisma, referee: Referee
):
    """Cas réel : deux mineurs du même compte pool (même adresse), ciblés
    individuellement. Un share de rig2 ne doit jamais compter pour contender_1,
    et réciproquement, même si `payload.address` est identique pour les deux."""
    battle = await _make_battle(
        prisma_tx, contender_1_worker="rig1", contender_2_worker="rig2"
    )
    referee.event_dispatcher = AsyncMock()

    share_from_rig1 = make_share("shared_address", block_height=400, worker="rig1", diff=50.0)
    await referee.on_share(battle, share_from_rig1)

    share_from_rig2 = make_share("shared_address", block_height=400, worker="rig2", diff=70.0)
    await referee.on_share(battle, share_from_rig2)

    round_row = await prisma_tx.rounds.find_unique(
        where={"battle_id_block_height": {"battle_id": battle.id, "block_height": 400}}
    )
    assert round_row is not None
    assert round_row.contender_1_best_diff == 50
    assert round_row.contender_2_best_diff == 70


@pytest.mark.asyncio
async def test_second_contender_worker_share_dispatches_its_own_event(
    prisma_tx: Prisma, referee: Referee
):
    battle = await _make_battle(
        prisma_tx, contender_1_worker="rig1", contender_2_worker="rig2"
    )
    referee.event_dispatcher = AsyncMock()

    share_from_rig2 = make_share("shared_address", block_height=400, worker="rig2", diff=70.0)
    await referee.on_share(battle, share_from_rig2)

    referee.event_dispatcher.new_best_share.assert_awaited_once_with(
        battle, "contender_2", share_from_rig2
    )


@pytest.mark.asyncio
async def test_share_ambiguous_between_whole_pool_and_targeted_miner_is_dropped(
    prisma_tx: Prisma, referee: Referee
):
    """Config limite : contender_1 cible "toute la pool" (pas de worker) et
    contender_2 cible un mineur précis de cette même pool. Les shares de ce mineur
    appartiennent aux deux à la fois (il est un sous-ensemble de la pool) : plutôt
    que de les compter à tort pour un seul camp, on les ignore et on log."""
    battle = await _make_battle(prisma_tx, contender_1_worker=None, contender_2_worker="rig2")
    referee.event_dispatcher = AsyncMock()

    share_from_rig2 = make_share("shared_address", block_height=400, worker="rig2", diff=70.0)
    await referee.on_share(battle, share_from_rig2)

    round_row = await prisma_tx.rounds.find_unique(
        where={"battle_id_block_height": {"battle_id": battle.id, "block_height": 400}}
    )
    assert round_row is not None
    assert round_row.contender_1_best_diff == 0
    assert round_row.contender_2_best_diff == 0
    referee.event_dispatcher.new_best_share.assert_not_called()


@pytest.mark.asyncio
async def test_worker_matching_is_case_insensitive(prisma_tx: Prisma, referee: Referee):
    """Bug observé en staging : le mineur configure un worker en casse mixte
    ("Fulcran") mais le pool renvoie parfois une casse différente ("fulcran") dans
    le share. Une comparaison sensible à la casse faisait échouer
    `_identify_contender` pour les deux contenders simultanément (même compte pool),
    bloquant toute progression de la bataille."""
    battle = await _make_battle(
        prisma_tx, contender_1_worker="Fulcran", contender_2_worker="Hugo"
    )
    referee.event_dispatcher = AsyncMock()

    share_from_fulcran = make_share("shared_address", block_height=400, worker="fulcran", diff=50.0)
    await referee.on_share(battle, share_from_fulcran)

    share_from_hugo = make_share("shared_address", block_height=400, worker="HUGO", diff=70.0)
    await referee.on_share(battle, share_from_hugo)

    round_row = await prisma_tx.rounds.find_unique(
        where={"battle_id_block_height": {"battle_id": battle.id, "block_height": 400}}
    )
    assert round_row is not None
    assert round_row.contender_1_best_diff == 50
    assert round_row.contender_2_best_diff == 70
