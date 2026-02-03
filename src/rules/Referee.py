from prisma import Prisma
from prisma.models import battles, rounds
from src.event_dispatcher.WebsocketBroadcaster import WebsocketBroadcaster
from src.apis.chauffagistes_pool.models.Share import Share
from src.modules.logger.logger import Logger


class Referee:

    prisma: Prisma
    log: Logger
    event_dispatcher: WebsocketBroadcaster

    async def get_current_round(self, battle_id: int):
        """Renvoie la hauteur de block du round en cours"""
        result = await self.prisma.rounds.find_many(
            where={"battle_id": battle_id}, order={"block_height": "desc"}, take=1
        )
        if len(result) == 0:
            return None

        else:
            return result[0]
    
    async def get_current_round_number(self, battle_id: int) -> int:
        res = await self.prisma.query_raw(
            """
            SELECT COUNT(*) AS round_number
            FROM rounds
            WHERE battle_id = $1;
            """,
            battle_id,
        )
        return res[0]["round_number"]

    async def compute_pv(self, battle: battles) -> tuple[int, int]:
        """Calcule les PV réstants à partir de l'historique des hits. Renvoie 2 entiers (pv_joueur1, pv_joueur2)"""

        hits_by_contender1 = await self.prisma.query_raw(
            """
            SELECT *
            FROM "rounds"
            WHERE battle_id = $1
            AND contender_1_best_diff > contender_2_best_diff
            """,
            battle.id,
        )

        hits_by_contenders2 = await self.prisma.query_raw(
            """
            SELECT *
            FROM "rounds"
            WHERE battle_id = $1
            AND contender_1_best_diff < contender_2_best_diff
            """,
            battle.id,
        )

        return battle.contenders_pv - len(
            hits_by_contenders2
        ), battle.contenders_pv - len(hits_by_contender1)
    
    async def _try_create_round(self, battle_id: int, block_height: int) -> bool:
        """Essaie de créer un round à chaque share"""

        # Egal 1 si le round a bien été créé
        result = await self.prisma.execute_raw(
            """
            INSERT INTO rounds (battle_id, block_height)
            VALUES ($1, $2)
            ON CONFLICT DO NOTHING
            RETURNING battle_id
            """,
            battle_id,
            block_height,
        )
        return result == 1

    async def _get_rounds_to_close(self, battle: battles, block_height: int):
        return await self.prisma.query_raw(
            """
            WITH ordered AS (
                SELECT
                    battle_id,
                    block_height,
                    contender_1_best_diff,
                    contender_2_best_diff,
                    ROW_NUMBER() OVER (ORDER BY block_height) AS round_number
                FROM rounds
                WHERE battle_id = $1
            )
            SELECT
                o.round_number,
                r.block_height,
                CASE
                    WHEN r.contender_1_best_diff > r.contender_2_best_diff THEN 1
                    WHEN r.contender_2_best_diff > r.contender_1_best_diff THEN 2
                    ELSE NULL
                END AS winner
            FROM rounds r
            JOIN ordered o USING (battle_id, block_height)
            WHERE r.battle_id = $1
            AND r.block_height < $2
            AND r.finalized_at IS NULL
            ORDER BY r.block_height;
            """,
            battle.id,
            block_height,
        )
    
    async def finalize_rounds(self, battle_id: int, next_block_height: int):
        # Update uniquement les rounds non finalisés avant le bloc actuel
        # RETURNING permet de récupérer uniquement les rounds réellement fermés
        rows = await self.prisma.query_raw(
            """
            UPDATE rounds
            SET
                finalized_at = NOW(),
                winner = CASE
                    WHEN contender_1_best_diff > contender_2_best_diff THEN 1
                    WHEN contender_2_best_diff > contender_1_best_diff THEN 2
                    ELSE NULL
                END
            WHERE battle_id = $1
            AND block_height < $2
            AND finalized_at IS NULL
            RETURNING block_height, winner, contender_1_best_diff, contender_2_best_diff;
            """,
            battle_id,
            next_block_height,
        )
        return rows  # seulement les rounds fermés

    async def on_share(self, battle: battles, payload: Share):
        block_height = int(payload.round, 16)

        # Ignorer les shares avant le début de la bataille
        if block_height < battle.start_height:
            self.log.debug(
                f"Ignoring share for battle {battle.id} at block {block_height}, "
                f"before start_height {battle.start_height}"
            )
            return

        # 1. Finaliser les rounds précédents
        closed_rounds = await self.finalize_rounds(battle.id, block_height)
        for r in closed_rounds:
            pv1, pv2 = await self.compute_pv(battle)
            await self.event_dispatcher.hit_result(
                battle=battle,
                winner=r["winner"],
                block_height=r["block_height"],
                contender_1_best_diff=r["contender_1_best_diff"],
                contender_2_best_diff=r["contender_2_best_diff"],
                contender_1_pv=pv1,
                contender_2_pv=pv2
            )

        # 2. Vérifier si le round existe déjà pour cette hauteur de bloc
        existing_round = await self.prisma.rounds.find_unique(
            where={
                "battle_id_block_height": {
                    "battle_id": battle.id,
                    "block_height": block_height,
                }
            }
        )

        # 3. Si le round n'existe pas, vérifier si on peut en créer un nouveau
        if existing_round is None:
            current_round_count = await self.get_current_round_number(battle.id)
            if current_round_count >= battle.rounds:
                self.log.debug(
                    f"Ignoring share for battle {battle.id} at block {block_height}, "
                    f"battle has reached max rounds ({battle.rounds})"
                )
                return

            # Créer le round courant
            created = await self._try_create_round(battle.id, block_height)
            if created:
                round_number = await self.get_current_round_number(battle.id)
                await self.event_dispatcher.new_round(battle, round_number, payload)

        # 4. Mettre à jour le best share
        if payload.address == battle.contender_1_address:
            contender = "contender_1"
            query = """
                UPDATE rounds
                SET contender_1_best_diff = $2
                WHERE battle_id = $1
                AND block_height = $3
                AND contender_1_best_diff < $2
                RETURNING contender_1_best_diff;
            """
        elif payload.address == battle.contender_2_address:
            contender = "contender_2"
            query = """
                UPDATE rounds
                SET contender_2_best_diff = $2
                WHERE battle_id = $1
                AND block_height = $3
                AND contender_2_best_diff < $2
                RETURNING contender_2_best_diff;
            """
        else:
            self.log.warn("Received share from unknown address")
            return

        rows = await self.prisma.execute_raw(query, battle.id, int(payload.diff), block_height)
        if rows:
            await self.event_dispatcher.new_best_share(battle, contender, payload)