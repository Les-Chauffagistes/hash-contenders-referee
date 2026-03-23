async def test_update_best_share_updates_matching_entry(referee, prisma, broadcaster, battle, share_slot1):
    prisma.rounds.find_unique.return_value = type("Round", (), {"id": 555})()
    prisma.execute_raw.return_value = 1

    await referee._update_best_share(battle, 100, share_slot1)

    # 1) touch activité de l'entry
    # 2) ensure round_result existe
    # 3) update best_share_diff
    assert prisma.execute_raw.await_count >= 3
    broadcaster.new_best_share.assert_awaited_once_with(battle, 1, share_slot1)


async def test_update_best_share_ignores_unknown_share(referee, prisma, broadcaster, battle):
    unknown_share = type(
        "Share",
        (),
        {
            "address": "bc1unknown",
            "worker": "rigX",
            "sdiff": 999,
            "round": hex(100),
        },
    )()

    await referee._update_best_share(battle, 100, unknown_share)

    prisma.execute_raw.assert_not_awaited()
    broadcaster.new_best_share.assert_not_awaited()


async def test_find_entry_from_share_matches_address_and_worker(referee, battle, share_slot1):
    entry = await referee._find_entry_from_share(battle, share_slot1)

    assert entry is not None
    assert entry.slot == 1
    assert entry.address == "bc1aaa"