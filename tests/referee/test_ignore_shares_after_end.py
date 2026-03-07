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
        diff=diff,
        sdiff=0.0,
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


@pytest.mark.asyncio
async def test_ignore_share_after_max_rounds_reached(
    prisma_tx: Prisma, referee: Referee
):
    """Les shares après le nombre max de rounds ne doivent pas créer de nouveau round"""
    battle = await prisma_tx.battles.create(
        data={
            "id": 1,
            "rounds": 3,  # Seulement 3 rounds autorisés
            "contender_1_address": "bc1_address",
            "contender_1_name": "Contender 1",
            "contender_2_address": "bc2_address",
            "contender_2_name": "Contender 2",
            "contenders_pv": 100,
            "start_height": 400,
        }
    )

    referee.event_dispatcher = AsyncMock()

    # Créer 3 rounds (le maximum)
    for block in [400, 401, 402]:
        share = make_share("bc1_address", block_height=block)
        await referee.on_share(battle, share)

    rounds_count = await prisma_tx.rounds.count(where={"battle_id": battle.id})
    assert rounds_count == 3

    # Envoyer un share pour un nouveau bloc (403) - devrait être ignoré
    share_after = make_share("bc1_address", block_height=403)
    await referee.on_share(battle, share_after)

    # Vérifier qu'aucun nouveau round n'a été créé
    rounds_count = await prisma_tx.rounds.count(where={"battle_id": battle.id})
    assert rounds_count == 3


@pytest.mark.asyncio
async def test_allow_share_on_last_round_in_progress(
    prisma_tx: Prisma, referee: Referee
):
    """Les shares sur le dernier round en cours doivent être acceptés"""
    battle = await prisma_tx.battles.create(
        data={
            "id": 1,
            "rounds": 3,
            "contender_1_address": "bc1_address",
            "contender_1_name": "Contender 1",
            "contender_2_address": "bc2_address",
            "contender_2_name": "Contender 2",
            "contenders_pv": 100,
            "start_height": 400,
        }
    )

    referee.event_dispatcher = AsyncMock()

    # Créer 3 rounds
    for block in [400, 401, 402]:
        share = make_share("bc1_address", block_height=block, diff=50.0)
        await referee.on_share(battle, share)

    # Envoyer un meilleur share sur le dernier round (402)
    better_share = make_share("bc1_address", block_height=402, diff=200.0)
    await referee.on_share(battle, better_share)

    # Vérifier que le best_diff a été mis à jour
    last_round = await prisma_tx.rounds.find_unique(
        where={"battle_id_block_height": {"battle_id": battle.id, "block_height": 402}}
    )
    assert last_round is not None
    assert last_round.contender_1_best_diff == 200


@pytest.mark.asyncio
async def test_allow_both_contenders_on_last_round(
    prisma_tx: Prisma, referee: Referee
):
    """Les deux contenders peuvent envoyer des shares sur le dernier round"""
    battle = await prisma_tx.battles.create(
        data={
            "id": 1,
            "rounds": 2,
            "contender_1_address": "bc1_address",
            "contender_1_name": "Contender 1",
            "contender_2_address": "bc2_address",
            "contender_2_name": "Contender 2",
            "contenders_pv": 100,
            "start_height": 400,
        }
    )

    referee.event_dispatcher = AsyncMock()

    # Créer 2 rounds avec contender 1
    for block in [400, 401]:
        share = make_share("bc1_address", block_height=block, diff=50.0)
        await referee.on_share(battle, share)

    # Contender 2 envoie un share sur le dernier round
    share_c2 = make_share("bc2_address", block_height=401, diff=150.0)
    await referee.on_share(battle, share_c2)

    # Vérifier que les deux contenders ont des best_diff
    last_round = await prisma_tx.rounds.find_unique(
        where={"battle_id_block_height": {"battle_id": battle.id, "block_height": 401}}
    )
    assert last_round is not None
    assert last_round.contender_1_best_diff == 50
    assert last_round.contender_2_best_diff == 150


@pytest.mark.asyncio
async def test_ignore_multiple_shares_after_end(prisma_tx: Prisma, referee: Referee):
    """Plusieurs shares après la fin de la bataille sont tous ignorés"""
    battle = await prisma_tx.battles.create(
        data={
            "id": 1,
            "rounds": 2,
            "contender_1_address": "bc1_address",
            "contender_1_name": "Contender 1",
            "contender_2_address": "bc2_address",
            "contender_2_name": "Contender 2",
            "contenders_pv": 100,
            "start_height": 400,
        }
    )

    referee.event_dispatcher = AsyncMock()

    # Créer les 2 rounds max
    for block in [400, 401]:
        share = make_share("bc1_address", block_height=block)
        await referee.on_share(battle, share)

    # Envoyer plusieurs shares pour de nouveaux blocs
    for block in [402, 403, 404, 405]:
        share = make_share("bc1_address", block_height=block)
        await referee.on_share(battle, share)

    # Vérifier qu'on a toujours seulement 2 rounds
    rounds_count = await prisma_tx.rounds.count(where={"battle_id": battle.id})
    assert rounds_count == 2


@pytest.mark.asyncio
async def test_finalize_rounds_still_works_after_max(
    prisma_tx: Prisma, referee: Referee
):
    """La finalisation des rounds fonctionne même quand le max est atteint"""
    battle = await prisma_tx.battles.create(
        data={
            "id": 1,
            "rounds": 2,
            "contender_1_address": "bc1_address",
            "contender_1_name": "Contender 1",
            "contender_2_address": "bc2_address",
            "contender_2_name": "Contender 2",
            "contenders_pv": 100,
            "start_height": 400,
        }
    )

    referee.event_dispatcher = AsyncMock()

    # Créer le round 1 avec des shares des deux contenders
    share1_c1 = make_share("bc1_address", block_height=400, diff=100.0)
    await referee.on_share(battle, share1_c1)
    share1_c2 = make_share("bc2_address", block_height=400, diff=50.0)
    await referee.on_share(battle, share1_c2)

    # Vérifier que le round 1 n'est pas encore finalisé
    round1 = await prisma_tx.rounds.find_unique(
        where={"battle_id_block_height": {"battle_id": battle.id, "block_height": 400}}
    )
    assert round1 is not None
    assert round1.finalized_at is None

    # Créer le round 2 - cela devrait finaliser le round 1
    share2 = make_share("bc1_address", block_height=401, diff=75.0)
    await referee.on_share(battle, share2)

    # Vérifier que le round 1 est maintenant finalisé
    round1_updated = await prisma_tx.rounds.find_unique(
        where={"battle_id_block_height": {"battle_id": battle.id, "block_height": 400}}
    )
    assert round1_updated is not None
    assert round1_updated.finalized_at is not None
    assert round1_updated.winner == 1  # contender 1 a gagné (100 > 50)

    # Envoyer un share après le max (block 402)
    # Cela devrait finaliser le round 2 mais ne pas créer de round 3
    share_after = make_share("bc1_address", block_height=402)
    await referee.on_share(battle, share_after)

    # Vérifier que le round 2 est finalisé
    round2 = await prisma_tx.rounds.find_unique(
        where={"battle_id_block_height": {"battle_id": battle.id, "block_height": 401}}
    )
    assert round2 is not None
    assert round2.finalized_at is not None

    # Vérifier qu'aucun round 3 n'a été créé
    rounds_count = await prisma_tx.rounds.count(where={"battle_id": battle.id})
    assert rounds_count == 2


@pytest.mark.asyncio
async def test_single_round_battle(prisma_tx: Prisma, referee: Referee):
    """Une bataille avec un seul round fonctionne correctement"""
    battle = await prisma_tx.battles.create(
        data={
            "id": 1,
            "rounds": 1,
            "contender_1_address": "bc1_address",
            "contender_1_name": "Contender 1",
            "contender_2_address": "bc2_address",
            "contender_2_name": "Contender 2",
            "contenders_pv": 100,
            "start_height": 400,
        }
    )

    referee.event_dispatcher = AsyncMock()

    # Créer le seul round autorisé
    share = make_share("bc1_address", block_height=400, diff=100.0)
    await referee.on_share(battle, share)

    rounds_count = await prisma_tx.rounds.count(where={"battle_id": battle.id})
    assert rounds_count == 1

    # Les shares suivants pour de nouveaux blocs sont ignorés
    share_after = make_share("bc1_address", block_height=401)
    await referee.on_share(battle, share_after)

    rounds_count = await prisma_tx.rounds.count(where={"battle_id": battle.id})
    assert rounds_count == 1

    # Mais on peut toujours mettre à jour le round en cours
    better_share = make_share("bc2_address", block_height=400, diff=200.0)
    await referee.on_share(battle, better_share)

    the_round = await prisma_tx.rounds.find_unique(
        where={"battle_id_block_height": {"battle_id": battle.id, "block_height": 400}}
    )
    assert the_round is not None
    assert the_round.contender_2_best_diff == 200
