from prisma import Prisma

Cursor = tuple[int, int]


class StreamCursor:
    """Curseur de reprise (epoch, seq) d'un flux du pool pour une bataille, persisté en base.

    Les écritures sont idempotentes et le curseur ne recule jamais (sauf `reset`, après une perte avérée).
    """

    def __init__(self, prisma: Prisma, battle_id: int, stream_key: str):
        self.prisma = prisma
        self.battle_id = battle_id
        self.stream_key = stream_key

    async def load(self) -> Cursor | None:
        rows = await self.prisma.query_raw(
            "SELECT epoch, seq FROM share_cursors WHERE battle_id = $1 AND stream_key = $2",
            self.battle_id,
            self.stream_key,
        )
        return (int(rows[0]["epoch"]), int(rows[0]["seq"])) if rows else None

    async def init(self, cursor: Cursor) -> None:
        """Premier curseur du flux (point de départ donné par `hello`); sans effet s'il existe déjà."""
        await self.prisma.execute_raw(
            """
            INSERT INTO share_cursors (battle_id, stream_key, epoch, seq)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT DO NOTHING
            """,
            self.battle_id, self.stream_key, *cursor,
        )

    async def advance(self, cursor: Cursor, gap: bool = False) -> None:
        """Avance le curseur après traitement d'un share. `gap`: le share a été abandonné (perte avérée)."""
        await self.prisma.execute_raw(
            """
            INSERT INTO share_cursors (battle_id, stream_key, epoch, seq, gap_count)
            VALUES ($1, $2, $3, $4, $5::int)
            ON CONFLICT (battle_id, stream_key) DO UPDATE
            SET epoch = EXCLUDED.epoch,
                seq = EXCLUDED.seq,
                gap_count = share_cursors.gap_count + EXCLUDED.gap_count,
                updated_at = now()
            WHERE (share_cursors.epoch, share_cursors.seq) < (EXCLUDED.epoch, EXCLUDED.seq)
            """,
            self.battle_id, self.stream_key, *cursor, int(gap),
        )

    async def mark_gap(self) -> None:
        """Enregistre une perte avérée sans toucher au curseur (4410: l'historique demandé n'existe plus)."""
        await self.prisma.execute_raw(
            """
            UPDATE share_cursors SET gap_count = gap_count + 1, updated_at = now()
            WHERE battle_id = $1 AND stream_key = $2
            """,
            self.battle_id, self.stream_key,
        )

    async def reset(self, cursor: Cursor) -> None:
        """Repart d'un nouveau point (après une perte avérée): seul cas où le curseur peut reculer."""
        await self.prisma.execute_raw(
            """
            INSERT INTO share_cursors (battle_id, stream_key, epoch, seq)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (battle_id, stream_key) DO UPDATE
            SET epoch = EXCLUDED.epoch, seq = EXCLUDED.seq, updated_at = now()
            """,
            self.battle_id, self.stream_key, *cursor,
        )
