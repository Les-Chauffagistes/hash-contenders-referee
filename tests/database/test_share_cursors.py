import pytest
from prisma import Prisma

from src.database.share_cursors import StreamCursor

KEY = "address=bc1"


async def make_battle(prisma: Prisma, battle_id: int = 1):
    return await prisma.battles.create(
        data={
            "id": battle_id,
            "rounds": 21,
            "owner_user_id": 1,
            "contender_1_address": "bc1",
            "contender_1_name": "bc1",
            "contender_2_address": "bc2",
            "contender_2_name": "bc2",
            "contenders_pv": 100,
            "start_height": 400,
        }
    )


async def gap_count(prisma: Prisma) -> int:
    rows = await prisma.query_raw("SELECT gap_count FROM share_cursors WHERE battle_id = 1")
    return rows[0]["gap_count"]


@pytest.mark.asyncio
async def test_load_without_cursor_returns_none(prisma_tx: Prisma):
    await make_battle(prisma_tx)
    assert await StreamCursor(prisma_tx, 1, KEY).load() is None


@pytest.mark.asyncio
async def test_init_is_kept_when_cursor_exists(prisma_tx: Prisma):
    await make_battle(prisma_tx)
    cursor = StreamCursor(prisma_tx, 1, KEY)
    await cursor.init((1, 10))
    await cursor.init((1, 99))
    assert await cursor.load() == (1, 10)


@pytest.mark.asyncio
async def test_advance_is_monotonic_and_ordered_by_epoch_then_seq(prisma_tx: Prisma):
    await make_battle(prisma_tx)
    cursor = StreamCursor(prisma_tx, 1, KEY)
    await cursor.advance((1, 10))
    await cursor.advance((1, 5))
    assert await cursor.load() == (1, 10)
    await cursor.advance((1, 11))
    assert await cursor.load() == (1, 11)
    await cursor.advance((2, 1))
    assert await cursor.load() == (2, 1)
    await cursor.advance((1, 500))
    assert await cursor.load() == (2, 1)


@pytest.mark.asyncio
async def test_advance_counts_gaps_only_when_flagged_and_applied(prisma_tx: Prisma):
    await make_battle(prisma_tx)
    cursor = StreamCursor(prisma_tx, 1, KEY)
    await cursor.advance((1, 1))
    assert await gap_count(prisma_tx) == 0
    await cursor.advance((1, 2), gap=True)
    assert await gap_count(prisma_tx) == 1
    await cursor.advance((1, 2), gap=True)  # déjà couvert: rien ne change
    assert await gap_count(prisma_tx) == 1


@pytest.mark.asyncio
async def test_mark_gap_keeps_the_cursor_and_reset_moves_it_back(prisma_tx: Prisma):
    await make_battle(prisma_tx)
    cursor = StreamCursor(prisma_tx, 1, KEY)
    await cursor.advance((1, 100))
    await cursor.mark_gap()
    assert await cursor.load() == (1, 100)
    assert await gap_count(prisma_tx) == 1
    await cursor.reset((1, 50))
    assert await cursor.load() == (1, 50)
    assert await gap_count(prisma_tx) == 1


@pytest.mark.asyncio
async def test_cursors_are_per_stream_and_deleted_with_the_battle(prisma_tx: Prisma):
    await make_battle(prisma_tx)
    await StreamCursor(prisma_tx, 1, "address=bc1").advance((1, 7))
    await StreamCursor(prisma_tx, 1, "address=bc2").advance((1, 9))
    assert await StreamCursor(prisma_tx, 1, "address=bc1").load() == (1, 7)
    assert await StreamCursor(prisma_tx, 1, "address=bc2").load() == (1, 9)
    await prisma_tx.battles.delete(where={"id": 1})
    assert await StreamCursor(prisma_tx, 1, "address=bc1").load() is None
