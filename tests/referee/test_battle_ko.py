import pytest
from unittest.mock import AsyncMock
from src.rules.Referee import Referee
from pool_api_types.models import Share
from prisma import Prisma


def make_share(address: str, block_height: int, diff: float = 100.0) -> Share:
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
        worker="",
        workernameAddr="",
        ip="",
        agent="",
        round=hex(block_height),
        file="",
    )


async def create_battle(prisma_tx: Prisma, contenders_pv: int = 2, rounds: int = 10):
    return await prisma_tx.battles.create(
        data={
            "id": 1,
            "rounds": rounds,
            "contender_1_address": "bc1_address",
            "contender_1_name": "Contender 1",
            "contender_2_address": "bc2_address",
            "contender_2_name": "Contender 2",
            "contenders_pv": contenders_pv,
            "start_height": 400,
        }
    )


@pytest.mark.asyncio
async def test_battle_ends_when_contender_1_pv_reaches_zero(
    prisma_tx: Prisma, referee: Referee
):
    """La bataille se termine quand contender 1 perd tous ses PV"""
    battle = await create_battle(prisma_tx, contenders_pv=2)
    referee.event_dispatcher = AsyncMock()

    # Round 1 (block 400): contender 2 gagne (diff 200 > 100)
    await referee.on_share(battle, make_share("bc1_address", 400, diff=100))
    await referee.on_share(battle, make_share("bc2_address", 400, diff=200))

    # Round 2 (block 401): contender 2 gagne encore -> contender 1 PV = 0
    await referee.on_share(battle, make_share("bc1_address", 401, diff=100))
    await referee.on_share(battle, make_share("bc2_address", 401, diff=200))

    # Block 402 arrive, finalise le round 2 -> KO détecté
    await referee.on_share(battle, make_share("bc1_address", 402, diff=100))

    # Vérifier que la bataille est terminée
    updated_battle = await prisma_tx.battles.find_unique(where={"id": battle.id})
    assert updated_battle.is_finished is True

    # Vérifier qu'aucun round n'a été créé pour le block 402
    round_402 = await prisma_tx.rounds.find_unique(
        where={"battle_id_block_height": {"battle_id": battle.id, "block_height": 402}}
    )
    assert round_402 is None


@pytest.mark.asyncio
async def test_battle_ends_when_contender_2_pv_reaches_zero(
    prisma_tx: Prisma, referee: Referee
):
    """La bataille se termine quand contender 2 perd tous ses PV"""
    battle = await create_battle(prisma_tx, contenders_pv=2)
    referee.event_dispatcher = AsyncMock()

    # Round 1 (block 400): contender 1 gagne (diff 200 > 100)
    await referee.on_share(battle, make_share("bc1_address", 400, diff=200))
    await referee.on_share(battle, make_share("bc2_address", 400, diff=100))

    # Round 2 (block 401): contender 1 gagne encore -> contender 2 PV = 0
    await referee.on_share(battle, make_share("bc1_address", 401, diff=200))
    await referee.on_share(battle, make_share("bc2_address", 401, diff=100))

    # Block 402 arrive, finalise le round 2 -> KO détecté
    await referee.on_share(battle, make_share("bc1_address", 402, diff=100))

    updated_battle = await prisma_tx.battles.find_unique(where={"id": battle.id})
    assert updated_battle.is_finished is True


@pytest.mark.asyncio
async def test_shares_ignored_after_ko(prisma_tx: Prisma, referee: Referee):
    """Après un KO, les shares suivants sont ignorés"""
    battle = await create_battle(prisma_tx, contenders_pv=1)
    referee.event_dispatcher = AsyncMock()

    # Round 1 (block 400): contender 1 gagne
    await referee.on_share(battle, make_share("bc1_address", 400, diff=200))
    await referee.on_share(battle, make_share("bc2_address", 400, diff=100))

    # Block 401 finalise -> KO de contender 2
    await referee.on_share(battle, make_share("bc1_address", 401, diff=100))

    rounds_after_ko = await prisma_tx.rounds.count(where={"battle_id": battle.id})

    # Envoyer des shares supplémentaires (battle.is_finished = True)
    await referee.on_share(battle, make_share("bc1_address", 402, diff=100))
    await referee.on_share(battle, make_share("bc2_address", 403, diff=100))

    # Aucun nouveau round ne doit être créé
    rounds_final = await prisma_tx.rounds.count(where={"battle_id": battle.id})
    assert rounds_final == rounds_after_ko


@pytest.mark.asyncio
async def test_battle_end_event_dispatched(prisma_tx: Prisma, referee: Referee):
    """L'événement battle_end est broadcasté avec le bon winner"""
    battle = await create_battle(prisma_tx, contenders_pv=1)
    referee.event_dispatcher = AsyncMock()

    # Round 1 (block 400): contender 1 gagne
    await referee.on_share(battle, make_share("bc1_address", 400, diff=200))
    await referee.on_share(battle, make_share("bc2_address", 400, diff=100))

    # Block 401 finalise -> KO de contender 2, winner = 1
    await referee.on_share(battle, make_share("bc1_address", 401, diff=100))

    referee.event_dispatcher.battle_end.assert_called_once()
    call_kwargs = referee.event_dispatcher.battle_end.call_args
    assert call_kwargs.kwargs["winner"] == 1
    assert call_kwargs.kwargs["contender_2_pv"] == 0


@pytest.mark.asyncio
async def test_battle_continues_while_pv_above_zero(
    prisma_tx: Prisma, referee: Referee
):
    """La bataille continue normalement tant que les PV sont > 0"""
    battle = await create_battle(prisma_tx, contenders_pv=3)
    referee.event_dispatcher = AsyncMock()

    # Round 1 (block 400): contender 1 gagne
    await referee.on_share(battle, make_share("bc1_address", 400, diff=200))
    await referee.on_share(battle, make_share("bc2_address", 400, diff=100))

    # Round 2 (block 401): contender 1 gagne encore (PV contender 2 = 1, pas encore KO)
    await referee.on_share(battle, make_share("bc1_address", 401, diff=200))
    await referee.on_share(battle, make_share("bc2_address", 401, diff=100))

    # Round 3 (block 402): nouveau round créé normalement
    await referee.on_share(battle, make_share("bc1_address", 402, diff=50))

    # La bataille n'est pas terminée
    updated_battle = await prisma_tx.battles.find_unique(where={"id": battle.id})
    assert updated_battle.is_finished is False

    # Le round 3 existe bien
    round_402 = await prisma_tx.rounds.find_unique(
        where={"battle_id_block_height": {"battle_id": battle.id, "block_height": 402}}
    )
    assert round_402 is not None

    # battle_end n'a pas été appelé
    referee.event_dispatcher.battle_end.assert_not_called()


@pytest.mark.asyncio
async def test_ko_cleans_up_spurious_round_from_race_condition(
    prisma_tx: Prisma, referee: Referee
):
    """Quand un round est créé par une race condition pendant le KO,
    _check_ko le supprime (round non finalisé).
    Scénario : les 2 tasks WS reçoivent un share au même block h+1.
    Task 2 crée le round h+1 pendant que Task 1 détecte le KO."""
    battle = await create_battle(prisma_tx, contenders_pv=1)
    referee.event_dispatcher = AsyncMock()

    # Round 1 (block 400): contender 1 gagne
    await referee.on_share(battle, make_share("bc1_address", 400, diff=200))
    await referee.on_share(battle, make_share("bc2_address", 400, diff=100))

    # Simuler la race condition : Task 2 a créé le round 401
    # pendant que Task 1 est en train de finaliser round 400
    await prisma_tx.rounds.create(
        data={"battle_id": battle.id, "block_height": 401}
    )

    round_401 = await prisma_tx.rounds.find_unique(
        where={"battle_id_block_height": {"battle_id": battle.id, "block_height": 401}}
    )
    assert round_401 is not None
    assert round_401.finalized_at is None

    # Task 1 : share au block 401, finalise round 400 -> KO détecté -> cleanup
    await referee.on_share(battle, make_share("bc1_address", 401, diff=100))

    # Le KO a dû supprimer le round 401 (non finalisé, créé par la race)
    round_401_after = await prisma_tx.rounds.find_unique(
        where={"battle_id_block_height": {"battle_id": battle.id, "block_height": 401}}
    )
    assert round_401_after is None

    # Seul le round 400 (finalisé) subsiste
    total_rounds = await prisma_tx.rounds.count(where={"battle_id": battle.id})
    assert total_rounds == 1


@pytest.mark.asyncio
async def test_ko_preserves_finalized_rounds(
    prisma_tx: Prisma, referee: Referee
):
    """Le cleanup KO ne supprime que les rounds non finalisés,
    les rounds finalisés sont préservés."""
    battle = await create_battle(prisma_tx, contenders_pv=1)
    referee.event_dispatcher = AsyncMock()

    # Round 1 (block 400): contender 1 gagne
    await referee.on_share(battle, make_share("bc1_address", 400, diff=200))
    await referee.on_share(battle, make_share("bc2_address", 400, diff=100))

    # Block 401 finalise round 400 -> KO
    await referee.on_share(battle, make_share("bc1_address", 401, diff=100))

    # Le round 400 (finalisé) doit toujours exister
    round_400 = await prisma_tx.rounds.find_unique(
        where={"battle_id_block_height": {"battle_id": battle.id, "block_height": 400}}
    )
    assert round_400 is not None
    assert round_400.finalized_at is not None
