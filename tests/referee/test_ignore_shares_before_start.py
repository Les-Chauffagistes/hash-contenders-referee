import pytest
from unittest.mock import AsyncMock
from src.rules.Referee import Referee
from src.apis.chauffagistes_pool.models.Share import Share
from prisma import Prisma


def make_share(address: str, block_height: int, diff: float = 100.0) -> Share:
    """Crée un Share de test avec la hauteur de bloc spécifiée"""
    return Share(
        workinfoid=1,
        clientid=1,
        enonce1="",
        enonce2="",
        nonce="",
        ntime="",
        diff=diff,
        sdiff=None,
        hash="",
        result=True,
        errn=0,
        createdate=0.0,
        createby="",
        createcode="",
        createinet="",
        workername="",
        username="",
        address=address,
        agent="",
        reject_reason=None,
        round=hex(block_height),
    )


@pytest.mark.asyncio
async def test_ignore_share_before_start_height(prisma_tx: Prisma, referee: Referee):
    """Les shares reçus avant start_height ne doivent pas créer de round"""
    battle = await prisma_tx.battles.create(
        data={
            "id": 1,
            "rounds": 21,
            "contender_1_address": "bc1_address",
            "contender_1_name": "Contender 1",
            "contender_2_address": "bc2_address",
            "contender_2_name": "Contender 2",
            "contenders_pv": 100,
            "start_height": 400,
        }
    )

    # Mock l'event_dispatcher car on_share l'utilise
    referee.event_dispatcher = AsyncMock()

    # Envoyer un share au bloc 399 (avant start_height=400)
    share_before = make_share("bc1_address", block_height=399)
    await referee.on_share(battle, share_before)

    # Vérifier qu'aucun round n'a été créé
    rounds_count = await prisma_tx.rounds.count(where={"battle_id": battle.id})
    assert rounds_count == 0


@pytest.mark.asyncio
async def test_ignore_multiple_shares_before_start_height(
    prisma_tx: Prisma, referee: Referee
):
    """Plusieurs shares avant start_height doivent tous être ignorés"""
    battle = await prisma_tx.battles.create(
        data={
            "id": 1,
            "rounds": 21,
            "contender_1_address": "bc1_address",
            "contender_1_name": "Contender 1",
            "contender_2_address": "bc2_address",
            "contender_2_name": "Contender 2",
            "contenders_pv": 100,
            "start_height": 500,
        }
    )

    referee.event_dispatcher = AsyncMock()

    # Envoyer plusieurs shares avant start_height
    for block in [100, 200, 300, 499]:
        share = make_share("bc1_address", block_height=block)
        await referee.on_share(battle, share)

    # Vérifier qu'aucun round n'a été créé
    rounds_count = await prisma_tx.rounds.count(where={"battle_id": battle.id})
    assert rounds_count == 0


@pytest.mark.asyncio
async def test_accept_share_at_start_height(prisma_tx: Prisma, referee: Referee):
    """Un share exactement à start_height doit être accepté"""
    battle = await prisma_tx.battles.create(
        data={
            "id": 1,
            "rounds": 21,
            "contender_1_address": "bc1_address",
            "contender_1_name": "Contender 1",
            "contender_2_address": "bc2_address",
            "contender_2_name": "Contender 2",
            "contenders_pv": 100,
            "start_height": 400,
        }
    )

    referee.event_dispatcher = AsyncMock()

    # Envoyer un share exactement à start_height=400
    share_at_start = make_share("bc1_address", block_height=400)
    await referee.on_share(battle, share_at_start)

    # Vérifier qu'un round a été créé
    rounds_count = await prisma_tx.rounds.count(where={"battle_id": battle.id})
    assert rounds_count == 1


@pytest.mark.asyncio
async def test_accept_share_after_start_height(prisma_tx: Prisma, referee: Referee):
    """Un share après start_height doit être accepté"""
    battle = await prisma_tx.battles.create(
        data={
            "id": 1,
            "rounds": 21,
            "contender_1_address": "bc1_address",
            "contender_1_name": "Contender 1",
            "contender_2_address": "bc2_address",
            "contender_2_name": "Contender 2",
            "contenders_pv": 100,
            "start_height": 400,
        }
    )

    referee.event_dispatcher = AsyncMock()

    # Envoyer un share après start_height
    share_after = make_share("bc1_address", block_height=401)
    await referee.on_share(battle, share_after)

    # Vérifier qu'un round a été créé
    rounds_count = await prisma_tx.rounds.count(where={"battle_id": battle.id})
    assert rounds_count == 1


@pytest.mark.asyncio
async def test_ignore_before_then_accept_after_start_height(
    prisma_tx: Prisma, referee: Referee
):
    """Les shares avant start_height sont ignorés, ceux après sont acceptés"""
    battle = await prisma_tx.battles.create(
        data={
            "id": 1,
            "rounds": 21,
            "contender_1_address": "bc1_address",
            "contender_1_name": "Contender 1",
            "contender_2_address": "bc2_address",
            "contender_2_name": "Contender 2",
            "contenders_pv": 100,
            "start_height": 400,
        }
    )

    referee.event_dispatcher = AsyncMock()

    # Envoyer des shares avant start_height
    for block in [398, 399]:
        share = make_share("bc1_address", block_height=block)
        await referee.on_share(battle, share)

    # Vérifier qu'aucun round n'a été créé
    rounds_count = await prisma_tx.rounds.count(where={"battle_id": battle.id})
    assert rounds_count == 0

    # Envoyer des shares à partir de start_height
    for block in [400, 401]:
        share = make_share("bc1_address", block_height=block)
        await referee.on_share(battle, share)

    # Vérifier que 2 rounds ont été créés
    rounds_count = await prisma_tx.rounds.count(where={"battle_id": battle.id})
    assert rounds_count == 2


@pytest.mark.asyncio
async def test_no_best_diff_update_before_start_height(
    prisma_tx: Prisma, referee: Referee
):
    """Les shares avant start_height ne doivent pas mettre à jour les best_diff"""
    battle = await prisma_tx.battles.create(
        data={
            "id": 1,
            "rounds": 21,
            "contender_1_address": "bc1_address",
            "contender_1_name": "Contender 1",
            "contender_2_address": "bc2_address",
            "contender_2_name": "Contender 2",
            "contenders_pv": 100,
            "start_height": 400,
        }
    )

    referee.event_dispatcher = AsyncMock()

    # Créer manuellement un round au bloc 400
    await prisma_tx.rounds.create(
        data={"battle_id": battle.id, "block_height": 400}
    )

    # Envoyer un share avant start_height avec une difficulté élevée
    share_before = make_share("bc1_address", block_height=399, diff=9999.0)
    await referee.on_share(battle, share_before)

    # Vérifier que le round existant n'a pas été modifié
    round_400 = await prisma_tx.rounds.find_unique(
        where={"battle_id_block_height": {"battle_id": battle.id, "block_height": 400}}
    )
    assert round_400 is not None
    assert round_400.contender_1_best_diff == 0
