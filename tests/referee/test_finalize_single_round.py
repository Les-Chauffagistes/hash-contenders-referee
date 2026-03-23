async def test_finalize_single_round_slot1_wins_and_slot2_loses_1_pv(referee, prisma, battle):
    round_row = {"id": 900, "block_height": 100}

    async def fake_get_round_results(round_id):
        return [
            {"entry_id": 101, "slot": 1, "best_share_diff": 5000},
            {"entry_id": 102, "slot": 2, "best_share_diff": 2000},
        ]

    async def fake_get_entry_pv(battle_id):
        return 3, 2

    referee._get_round_results = fake_get_round_results
    referee._get_entry_pv = fake_get_entry_pv

    result = await referee._finalize_single_round(battle, round_row)

    assert result["winner"] == 1
    assert result["slot_1_best_diff"] == 5000
    assert result["slot_2_best_diff"] == 2000
    assert result["pv1"] == 3
    assert result["pv2"] == 2

    # update rounds + loser entry + winner entry
    assert prisma.execute_raw.await_count == 3


async def test_finalize_single_round_draw_does_not_change_pv(referee, prisma, battle):
    round_row = {"id": 901, "block_height": 101}

    async def fake_get_round_results(round_id):
        return [
            {"entry_id": 101, "slot": 1, "best_share_diff": 3000},
            {"entry_id": 102, "slot": 2, "best_share_diff": 3000},
        ]

    async def fake_get_entry_pv(battle_id):
        return 3, 3

    referee._get_round_results = fake_get_round_results
    referee._get_entry_pv = fake_get_entry_pv

    result = await referee._finalize_single_round(battle, round_row)

    assert result["winner"] is None
    assert result["pv1"] == 3
    assert result["pv2"] == 3

    # seulement update round
    assert prisma.execute_raw.await_count == 1


async def test_finalize_single_round_with_missing_results_finalizes_without_winner(referee, prisma, battle):
    round_row = {"id": 902, "block_height": 102}

    async def fake_get_round_results(round_id):
        return [{"entry_id": 101, "slot": 1, "best_share_diff": 3000}]

    referee._get_round_results = fake_get_round_results

    result = await referee._finalize_single_round(battle, round_row)

    assert result["winner"] is None
    assert result["slot_1_best_diff"] == 3000
    assert result["slot_2_best_diff"] == 0
    assert result["pv1"] is None
    assert result["pv2"] is None