async def test_check_battle_end_finishes_battle_when_slot2_pv_reaches_zero(referee, prisma, broadcaster, battle):
    prisma.query_raw.return_value = [
        {"id": 101, "slot": 1, "current_pv": 2},
        {"id": 102, "slot": 2, "current_pv": 0},
    ]

    ended = await referee._check_battle_end(battle)

    assert ended is True
    assert prisma.execute_raw.await_count == 3
    broadcaster.battle_end.assert_awaited_once_with(
        battle=battle,
        winner=1,
        contender_1_pv=2,
        contender_2_pv=0,
    )


async def test_check_battle_end_returns_false_when_both_alive(referee, prisma, broadcaster, battle):
    prisma.query_raw.return_value = [
        {"id": 101, "slot": 1, "current_pv": 2},
        {"id": 102, "slot": 2, "current_pv": 1},
    ]

    ended = await referee._check_battle_end(battle)

    assert ended is False
    broadcaster.battle_end.assert_not_awaited()