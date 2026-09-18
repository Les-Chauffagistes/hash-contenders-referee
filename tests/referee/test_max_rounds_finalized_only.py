import pytest
from unittest.mock import AsyncMock
from src.rules.Referee import Referee
from chauff_cmn.models import Share
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


async def create_battle(prisma_tx: Prisma, rounds: int = 3, contenders_pv: int = 100):
    return await prisma_tx.battles.create(
        data={
            "id": 1,
            "rounds": rounds,
            "owner_user_id": 1,
            "contender_1_address": "bc1_address",
            "contender_1_name": "Contender 1",
            "contender_2_address": "bc2_address",
            "contender_2_name": "Contender 2",
            "contenders_pv": contenders_pv,
            "start_height": 400,
        }
    )


@pytest.mark.asyncio
async def test_battle_terminates_when_max_rounds_reached_and_opponent_never_played(
    prisma_tx: Prisma, referee: Referee
):
    """Reproduit le bug de la battle 13 : un seul contender envoie des shares,
    donc aucun round ne peut jamais être finalisé équitablement (finalize_rounds
    et le force-finalize exigent des diffs > 0 des DEUX contenders). Avant le
    fix, une fois le nombre de rounds *créés* (finalisés ou non) égal à
    battle.rounds, tous les shares suivants étaient ignorés en silence sans
    que la bataille ne soit jamais marquée terminée (is_finished restait
    False, le websocket frontend n'était jamais fermé).

    Le comportement attendu : dès que le max de rounds créés est atteint sans
    qu'ils aient pu être décidés équitablement, ils sont nettoyés (comme pour
    le cleanup KO) et la bataille se termine normalement, aux PV."""
    battle = await create_battle(prisma_tx, rounds=3)
    referee.event_dispatcher = AsyncMock()

    # Seul le contender 1 envoie des shares, sur 4 hauteurs de bloc distinctes
    # (battle.rounds = 3 : la 4e doit déclencher la fin de bataille).
    for block_height in (400, 401, 402, 403):
        await referee.on_share(battle, make_share("bc1_address", block_height, diff=100))

    updated_battle = await prisma_tx.battles.find_unique(where={"id": battle.id})
    assert updated_battle.is_finished is True, (
        "La bataille doit se terminer une fois le max de rounds atteint, même "
        "si aucun round n'a pu être décidé équitablement (contender 2 absent)."
    )

    referee.event_dispatcher.battle_end.assert_called_once()
    referee.event_dispatcher.client_websockets.close.assert_called_once_with(battle.id)

    # Aucun round n'a jamais pu être décidé équitablement : ils sont tous nettoyés
    rounds_count = await prisma_tx.rounds.count(where={"battle_id": battle.id})
    assert rounds_count == 0

    # Un share supplémentaire, envoyé après la fin, est bien ignoré
    await referee.on_share(battle, make_share("bc1_address", 404, diff=100))
    rounds_count_after = await prisma_tx.rounds.count(where={"battle_id": battle.id})
    assert rounds_count_after == 0


@pytest.mark.asyncio
async def test_never_more_than_configured_rounds_are_created(
    prisma_tx: Prisma, referee: Referee
):
    """Jamais plus de battle.rounds rounds ne doivent exister, y compris
    quand la bataille se termine par force-finalisation du dernier round."""
    battle = await create_battle(prisma_tx, rounds=2)
    referee.event_dispatcher = AsyncMock()

    # Round 1 (block 400) et round 2 (block 401), joués par les deux contenders
    await referee.on_share(battle, make_share("bc1_address", 400, diff=200))
    await referee.on_share(battle, make_share("bc2_address", 400, diff=100))
    await referee.on_share(battle, make_share("bc1_address", 401, diff=200))
    await referee.on_share(battle, make_share("bc2_address", 401, diff=100))

    # Block 402 : max de rounds créés atteint (2) -> round 401 force-finalisé,
    # bataille terminée, round 402 jamais créé
    await referee.on_share(battle, make_share("bc1_address", 402, diff=100))

    rounds_count = await prisma_tx.rounds.count(where={"battle_id": battle.id})
    assert rounds_count <= 2

    updated_battle = await prisma_tx.battles.find_unique(where={"id": battle.id})
    assert updated_battle.is_finished is True
