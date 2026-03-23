from prisma import Prisma
from prisma.models import battles, battle_entries, rounds
from src.event_dispatcher.WebsocketBroadcaster import WebsocketBroadcaster
from src.apis.chauffagistes_pool.models.Share import Share
from src.modules.logger.logger import Logger


class Referee:
    prisma: Prisma
    log: Logger
    event_dispatcher: WebsocketBroadcaster

    def _get_duel_entries(self, battle: battles) -> tuple[battle_entries | None, battle_entries | None]:
        entries = getattr(battle, "entries", None) or []

        entry_1 = next((e for e in entries if e.slot == 1), None)
        entry_2 = next((e for e in entries if e.slot == 2), None)

        return entry_1, entry_2

    async def get_current_round(self, battle_id: int):
        result = await self.prisma.rounds.find_many(
            where={"battle_id": battle_id},
            order={"block_height": "desc"},
            take=1,
        )
        return result[0] if result else None

    async def get_current_round_number(self, battle_id: int) -> int:
        res = await self.prisma.query_raw(
            """
            SELECT COALESCE(MAX(round_number), 0) AS round_number
            FROM rounds
            WHERE battle_id = $1
            """,
            battle_id,
        )
        return int(res[0]["round_number"])

    async def _get_entry_pv(self, battle_id: int) -> tuple[int, int]:
        rows = await self.prisma.query_raw(
            """
            SELECT slot, current_pv
            FROM battle_entries
            WHERE battle_id = $1
            ORDER BY slot ASC
            """,
            battle_id,
        )

        pv1 = 0
        pv2 = 0

        for row in rows:
            if row["slot"] == 1:
                pv1 = int(row["current_pv"])
            elif row["slot"] == 2:
                pv2 = int(row["current_pv"])

        return pv1, pv2

    async def _try_create_round(self, battle_id: int, block_height: int) -> bool:
        result = await self.prisma.execute_raw(
            """
            INSERT INTO rounds (
                battle_id,
                block_height,
                round_number,
                status,
                pv_lost
            )
            SELECT
                $1,
                $2,
                COALESCE(MAX(r.round_number), 0) + 1,
                'PENDING',
                1
            FROM rounds r
            WHERE r.battle_id = $1
            ON CONFLICT (battle_id, block_height) DO NOTHING
            RETURNING id
            """,
            battle_id,
            block_height,
        )
        return result == 1

    async def _ensure_round_exists(self, battle: battles, block_height: int, payload: Share) -> bool:
        existing_round = await self.prisma.rounds.find_unique(
            where={
                "battle_id_block_height": {
                    "battle_id": battle.id,
                    "block_height": block_height,
                }
            }
        )

        if existing_round is None:
            created = await self._try_create_round(battle.id, block_height)
            if created:
                round_number = await self.get_current_round_number(battle.id)
                await self.event_dispatcher.new_round(battle, round_number, payload)

        return True

    async def _get_round_id(self, battle_id: int, block_height: int) -> int | None:
        round_obj = await self.prisma.rounds.find_unique(
            where={
                "battle_id_block_height": {
                    "battle_id": battle_id,
                    "block_height": block_height,
                }
            }
        )
        return int(round_obj.id) if round_obj else None

    async def _find_entry_from_share(self, battle: battles, payload: Share) -> battle_entries | None:
        entry_1, entry_2 = self._get_duel_entries(battle)

        for entry in [entry_1, entry_2]:
            if entry is None:
                continue

            if payload.address != entry.address:
                continue

            if entry.worker_name:
                if getattr(payload, "worker", None) == entry.worker_name:
                    return entry
                continue

            return entry

        return None

    async def _touch_entry_share_activity(self, entry_id: int):
        await self.prisma.execute_raw(
            """
            UPDATE battle_entries
            SET
                first_share_at = COALESCE(first_share_at, NOW()),
                last_share_at = NOW(),
                status = CASE WHEN status = 'JOINED' THEN 'ACTIVE' ELSE status END
            WHERE id = $1
            """,
            entry_id,
        )

    async def _upsert_round_result(self, round_id: int, entry_id: int):
        await self.prisma.execute_raw(
            """
            INSERT INTO round_results (
                round_id,
                entry_id,
                best_share_diff,
                submitted_share_count,
                created_at,
                updated_at
            )
            VALUES ($1, $2, 0, 0, NOW(), NOW())
            ON CONFLICT (round_id, entry_id) DO NOTHING
            """,
            round_id,
            entry_id,
        )

    async def _update_best_share(self, battle: battles, block_height: int, payload: Share):
        entry = await self._find_entry_from_share(battle, payload)
        if entry is None:
            self.log.warn(f"[BATTLE {battle.id}] Share reçu d'une adresse/worker inconnu")
            return

        round_id = await self._get_round_id(battle.id, block_height)
        if round_id is None:
            self.log.warn(f"[BATTLE {battle.id}] Impossible de retrouver le round du block {block_height}")
            return

        await self._touch_entry_share_activity(int(entry.id))
        await self._upsert_round_result(round_id, int(entry.id))

        updated = await self.prisma.execute_raw(
            """
            UPDATE round_results
            SET
                best_share_diff = GREATEST(best_share_diff, $3),
                submitted_share_count = submitted_share_count + 1,
                updated_at = NOW()
            WHERE round_id = $1
              AND entry_id = $2
            """,
            round_id,
            int(entry.id),
            int(payload.sdiff),
        )

        if updated:
            await self.event_dispatcher.new_best_share(battle, entry.slot, payload)

    async def _get_rounds_to_finalize(self, battle_id: int, next_block_height: int):
        return await self.prisma.query_raw(
            """
            SELECT id, block_height, round_number
            FROM rounds
            WHERE battle_id = $1
              AND block_height < $2
              AND finalized_at IS NULL
            ORDER BY block_height ASC
            """,
            battle_id,
            next_block_height,
        )

    async def _get_round_results(self, round_id: int):
        return await self.prisma.query_raw(
            """
            SELECT
                rr.entry_id,
                be.slot,
                rr.best_share_diff
            FROM round_results rr
            JOIN battle_entries be ON be.id = rr.entry_id
            WHERE rr.round_id = $1
            ORDER BY be.slot ASC
            """,
            round_id,
        )

    async def _finalize_single_round(self, battle: battles, round_row: dict):
        round_id = int(round_row["id"])
        block_height = int(round_row["block_height"])

        results = await self._get_round_results(round_id)
        if len(results) < 2:
            # Pas assez de données pour départager, on finalise sans vainqueur.
            await self.prisma.execute_raw(
                """
                UPDATE rounds
                SET
                    status = 'FINISHED',
                    finalized_at = NOW()
                WHERE id = $1
                """,
                round_id,
            )
            return {
                "round_id": round_id,
                "block_height": block_height,
                "winner": None,
                "slot_1_best_diff": int(results[0]["best_share_diff"]) if len(results) > 0 else 0,
                "slot_2_best_diff": int(results[1]["best_share_diff"]) if len(results) > 1 else 0,
                "pv1": None,
                "pv2": None,
            }

        r1 = results[0]
        r2 = results[1]

        diff1 = int(r1["best_share_diff"] or 0)
        diff2 = int(r2["best_share_diff"] or 0)

        winner_entry_id = None
        loser_entry_id = None
        winner_slot = None

        if diff1 > diff2:
            winner_entry_id = int(r1["entry_id"])
            loser_entry_id = int(r2["entry_id"])
            winner_slot = int(r1["slot"])
        elif diff2 > diff1:
            winner_entry_id = int(r2["entry_id"])
            loser_entry_id = int(r1["entry_id"])
            winner_slot = int(r2["slot"])

        await self.prisma.execute_raw(
            """
            UPDATE rounds
            SET
                status = 'FINISHED',
                finalized_at = NOW(),
                winner_entry_id = $2,
                loser_entry_id = $3,
                winner_best_share_diff = $4
            WHERE id = $1
            """,
            round_id,
            winner_entry_id,
            loser_entry_id,
            max(diff1, diff2) if winner_entry_id is not None else None,
        )

        if loser_entry_id is not None and winner_entry_id is not None:
            await self.prisma.execute_raw(
                """
                UPDATE battle_entries
                SET
                    current_pv = GREATEST(current_pv - 1, 0),
                    rounds_lost = rounds_lost + 1,
                    updated_at = NOW()
                WHERE id = $1
                """,
                loser_entry_id,
            )

            await self.prisma.execute_raw(
                """
                UPDATE battle_entries
                SET
                    rounds_won = rounds_won + 1,
                    updated_at = NOW()
                WHERE id = $1
                """,
                winner_entry_id,
            )

        pv1, pv2 = await self._get_entry_pv(int(battle.id))

        return {
            "round_id": round_id,
            "block_height": block_height,
            "winner": winner_slot,
            "slot_1_best_diff": diff1,
            "slot_2_best_diff": diff2,
            "pv1": pv1,
            "pv2": pv2,
        }

    async def finalize_rounds(self, battle: battles, next_block_height: int) -> list[dict]:
        rounds_to_finalize = await self._get_rounds_to_finalize(int(battle.id), next_block_height)

        finalized = []
        for round_row in rounds_to_finalize:
            finalized_round = await self._finalize_single_round(battle, round_row)
            finalized.append(finalized_round)

        return finalized

    async def _finalize_and_broadcast(self, battle: battles, block_height: int) -> list[dict]:
        closed_rounds = await self.finalize_rounds(battle, block_height)

        for r in closed_rounds:
            await self.event_dispatcher.hit_result(
                battle=battle,
                winner=r["winner"],
                block_height=r["block_height"],
                contender_1_best_diff=r["slot_1_best_diff"],
                contender_2_best_diff=r["slot_2_best_diff"],
                contender_1_pv=r["pv1"],
                contender_2_pv=r["pv2"],
            )

        return closed_rounds

    async def _check_battle_end(self, battle: battles) -> bool:
        rows = await self.prisma.query_raw(
            """
            SELECT id, slot, current_pv
            FROM battle_entries
            WHERE battle_id = $1
            ORDER BY slot ASC
            """,
            battle.id,
        )

        if len(rows) < 2:
            return False

        entry1 = rows[0]
        entry2 = rows[1]

        pv1 = int(entry1["current_pv"])
        pv2 = int(entry2["current_pv"])

        if pv1 > 0 and pv2 > 0:
            return False

        winner_slot = 1 if pv2 <= 0 else 2
        winner_entry_id = int(entry1["id"]) if winner_slot == 1 else int(entry2["id"])
        loser_entry_id = int(entry2["id"]) if winner_slot == 1 else int(entry1["id"])

        await self.prisma.execute_raw(
            """
            UPDATE battles
            SET
                status = 'FINISHED',
                finished_at = NOW(),
                winner_entry_id = $2,
                finish_reason = 'PV_DEPLETED',
                updated_at = NOW()
            WHERE id = $1
            """,
            battle.id,
            winner_entry_id,
        )

        await self.prisma.execute_raw(
            """
            UPDATE battle_entries
            SET
                is_winner = CASE WHEN id = $2 THEN TRUE ELSE FALSE END,
                status = CASE WHEN id = $3 THEN 'ELIMINATED' ELSE status END,
                updated_at = NOW()
            WHERE battle_id = $1
            """,
            battle.id,
            winner_entry_id,
            loser_entry_id,
        )

        await self.prisma.execute_raw(
            """
            DELETE FROM rounds
            WHERE battle_id = $1
              AND finalized_at IS NULL
            """,
            battle.id,
        )

        battle.status = "FINISHED"
        battle.finished_at = None  # optionnel selon ton usage runtime

        await self.event_dispatcher.battle_end(
            battle=battle,
            winner=winner_slot,
            contender_1_pv=pv1,
            contender_2_pv=pv2,
        )
        return True

    async def on_share(self, battle: battles, payload: Share, replay: bool):
        if replay:
            return

        block_height = int(payload.round, 16)

        self.log.debug(f"[BATTLE {battle.id}] Block height décodé = {block_height}")

        if battle.status == "FINISHED":
            self.log.debug(f"[BATTLE {battle.id}] Share ignoré : battle déjà terminée")
            return

        if battle.start_height is not None and block_height < battle.start_height:
            self.log.debug(
                f"[BATTLE {battle.id}] Share ignoré : block {block_height} < start_height {battle.start_height}"
            )
            return

        self.log.debug(f"[BATTLE {battle.id}] Traitement du share pour block {block_height}")

        closed_rounds = await self._finalize_and_broadcast(battle, block_height)

        if closed_rounds and await self._check_battle_end(battle):
            self.log.debug(f"[BATTLE {battle.id}] Fin de battle détectée après finalisation")
            return

        if battle.status == "FINISHED":
            self.log.debug(f"[BATTLE {battle.id}] Battle déjà terminée pendant le traitement")
            return

        if not await self._ensure_round_exists(battle, block_height, payload):
            return

        await self._update_best_share(battle, block_height, payload)