async def test_on_share_finalizes_previous_round_then_updates_current_one(
    referee, battle, share_slot1
):
    called = {
        "finalize": False,
        "check_end": False,
        "ensure_round": False,
        "update_best": False,
    }

    async def fake_finalize_and_broadcast(b, block_height):
        called["finalize"] = True
        assert b is battle
        assert block_height == 100
        return [{"block_height": 99, "winner": 1}]

    async def fake_check_battle_end(b):
        called["check_end"] = True
        return False

    async def fake_ensure_round_exists(b, block_height, payload):
        called["ensure_round"] = True
        assert block_height == 100
        assert payload is share_slot1
        return True

    async def fake_update_best_share(b, block_height, payload):
        called["update_best"] = True
        assert block_height == 100
        assert payload is share_slot1

    referee._finalize_and_broadcast = fake_finalize_and_broadcast
    referee._check_battle_end = fake_check_battle_end
    referee._ensure_round_exists = fake_ensure_round_exists
    referee._update_best_share = fake_update_best_share

    await referee.on_share(battle, share_slot1, replay=False)

    assert called == {
        "finalize": True,
        "check_end": True,
        "ensure_round": True,
        "update_best": True,
    }


async def test_on_share_stops_after_battle_end(referee, battle, share_slot1):
    called = {
        "ensure_round": False,
        "update_best": False,
    }

    async def fake_finalize_and_broadcast(b, block_height):
        return [{"block_height": 99, "winner": 1}]

    async def fake_check_battle_end(b):
        return True

    async def fake_ensure_round_exists(b, block_height, payload):
        called["ensure_round"] = True
        return True

    async def fake_update_best_share(b, block_height, payload):
        called["update_best"] = True

    referee._finalize_and_broadcast = fake_finalize_and_broadcast
    referee._check_battle_end = fake_check_battle_end
    referee._ensure_round_exists = fake_ensure_round_exists
    referee._update_best_share = fake_update_best_share

    await referee.on_share(battle, share_slot1, replay=False)

    assert called["ensure_round"] is False
    assert called["update_best"] is False