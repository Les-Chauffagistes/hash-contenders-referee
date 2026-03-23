from types import SimpleNamespace


async def test_get_current_round_returns_none_when_no_round(referee, prisma):
    prisma.rounds.find_many.return_value = []

    current = await referee.get_current_round(1)

    assert current is None
    prisma.rounds.find_many.assert_awaited_once_with(
        where={"battle_id": 1},
        order={"block_height": "desc"},
        take=1,
    )


async def test_get_current_round_returns_latest_round(referee, prisma):
    latest = SimpleNamespace(id=99, block_height=321)
    prisma.rounds.find_many.return_value = [latest]

    current = await referee.get_current_round(1)

    assert current is latest