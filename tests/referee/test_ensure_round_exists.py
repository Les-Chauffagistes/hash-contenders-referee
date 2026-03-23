async def test_ensure_round_exists_creates_round_and_broadcasts(referee, prisma, broadcaster, battle, share_slot1):
    prisma.rounds.find_unique.return_value = None

    async def fake_try_create_round(battle_id, block_height):
        return True

    async def fake_get_current_round_number(battle_id):
        return 4

    referee._try_create_round = fake_try_create_round
    referee.get_current_round_number = fake_get_current_round_number

    ok = await referee._ensure_round_exists(battle, 100, share_slot1)

    assert ok is True
    broadcaster.new_round.assert_awaited_once_with(battle, 4, share_slot1)


async def test_ensure_round_exists_does_not_recreate_existing_round(referee, prisma, broadcaster, battle, share_slot1):
    prisma.rounds.find_unique.return_value = object()

    ok = await referee._ensure_round_exists(battle, 100, share_slot1)

    assert ok is True
    broadcaster.new_round.assert_not_awaited()