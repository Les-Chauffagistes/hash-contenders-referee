async def test_on_share_ignores_replay(referee, prisma, battle, share_slot1):
    await referee.on_share(battle, share_slot1, replay=True)

    prisma.execute_raw.assert_not_awaited()
    prisma.query_raw.assert_not_awaited()


async def test_on_share_ignores_share_before_start_height(referee, prisma, battle, share_slot1):
    battle.start_height = 200
    share_slot1.round = hex(150)

    await referee.on_share(battle, share_slot1, replay=False)

    prisma.execute_raw.assert_not_awaited()
    prisma.query_raw.assert_not_awaited()


async def test_on_share_ignores_when_battle_already_finished(referee, prisma, battle, share_slot1):
    battle.status = "FINISHED"

    await referee.on_share(battle, share_slot1, replay=False)

    prisma.execute_raw.assert_not_awaited()
    prisma.query_raw.assert_not_awaited()