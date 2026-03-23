async def test_get_current_round_number_returns_zero_when_empty(referee, prisma):
    prisma.query_raw.return_value = [{"round_number": 0}]

    result = await referee.get_current_round_number(1)

    assert result == 0


async def test_get_current_round_number_returns_max_round(referee, prisma):
    prisma.query_raw.return_value = [{"round_number": 7}]

    result = await referee.get_current_round_number(1)

    assert result == 7