import pytest
from prisma import Prisma
from src.server.core.status.v1 import get_battle_status


async def _make_battle(prisma_tx: Prisma, **overrides):
    data = {
        "id": 1,
        "rounds": 2,
        "owner_user_id": 1,
        "contender_1_address": "addr1",
        "contender_1_name": "Contender 1",
        "contender_2_address": "addr2",
        "contender_2_name": "Contender 2",
        "contenders_pv": 100,
        "start_height": 400,
    }
    data.update(overrides)
    return await prisma_tx.battles.create(data=data)


@pytest.mark.asyncio
async def test_status_exposes_configured_worker_per_contender(prisma_tx: Prisma, wired_app):
    battle = await _make_battle(prisma_tx, contender_1_worker="rig1")

    status = await get_battle_status(battle.id, include_hits=False)

    assert status["contender_info"][0]["worker"] == "rig1"
    assert status["contender_info"][1]["worker"] is None


@pytest.mark.asyncio
async def test_status_worker_defaults_to_none_for_pool_vs_pool_battles(prisma_tx: Prisma, wired_app):
    """Non-régression : une bataille sans mineur ciblé (mode historique) expose worker=None."""
    battle = await _make_battle(prisma_tx)

    status = await get_battle_status(battle.id, include_hits=False)

    assert status["contender_info"][0]["worker"] is None
    assert status["contender_info"][1]["worker"] is None


@pytest.mark.asyncio
async def test_status_keeps_worker_visible_when_addresses_are_private(prisma_tx: Prisma, wired_app):
    """`are_addresses_privates` masque l'adresse (donnée financière), pas le nom du
    mineur ciblé : ce n'est pas la donnée que ce flag est censé protéger."""
    battle = await _make_battle(
        prisma_tx, contender_1_worker="rig1", are_addresses_privates=True
    )

    status = await get_battle_status(battle.id, include_hits=False)

    assert "address" not in status["contender_info"][0]
    assert status["contender_info"][0]["worker"] == "rig1"
