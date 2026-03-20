from datetime import datetime, timezone

from prisma import Prisma


class BattleAdminError(Exception):
    pass


class BattleAdminService:
    def __init__(self, prisma: Prisma):
        self.prisma = prisma

    async def list_battles(self):
        return await self.prisma.battles.find_many(
            order={"created_at": "desc"},
            include={
                "contenders": True,
                "all_rounds": True,
                "events": True,
            },
        )

    async def get_battle(self, battle_id: int):
        battle = await self.prisma.battles.find_unique(
            where={"id": battle_id},
            include={
                "contenders": True,
                "all_rounds": True,
                "events": True,
            },
        )
        if not battle:
            raise BattleAdminError("Battle introuvable")
        return battle

    async def create_battle(self, payload):
        battle = await self.prisma.battles.create(
            data={
                "name": payload.name,
                "description": payload.description,
                "mode": payload.mode,
                "start_height": payload.start_height,
                "planned_start_at": payload.planned_start_at,
                "rounds": payload.rounds,
                "max_pv": payload.max_pv,
                "are_addresses_privates": payload.are_addresses_privates,
                "status": "DRAFT",
                "is_finished": False,
                "current_round_number": 0,
            }
        )

        await self.prisma.battle_events.create(
            data={
                "battle_id": battle.id,
                "type": "BATTLE_CREATED",
                "payload": {
                    "name": battle.name,
                    "mode": battle.mode,
                },
            }
        )

        return battle

    async def update_battle(self, battle_id: int, payload):
        battle = await self.prisma.battles.find_unique(where={"id": battle_id})
        if not battle:
            raise BattleAdminError("Battle introuvable")

        if battle.status in ("LIVE", "FINISHED", "CANCELLED"):
            raise BattleAdminError("Impossible de modifier cette battle dans son état actuel")

        update_data = {}
        for field_name in [
            "name",
            "description",
            "mode",
            "start_height",
            "planned_start_at",
            "rounds",
            "max_pv",
            "are_addresses_privates",
        ]:
            value = getattr(payload, field_name)
            if value is not None:
                update_data[field_name] = value

        if not update_data:
            raise BattleAdminError("Aucune donnée à mettre à jour")

        updated = await self.prisma.battles.update(
            where={"id": battle_id},
            data=update_data,
        )

        await self.prisma.battle_events.create(
            data={
                "battle_id": battle_id,
                "type": "BATTLE_UPDATED",
                "payload": update_data,
            }
        )

        return updated

    async def delete_battle(self, battle_id: int):
        battle = await self.prisma.battles.find_unique(where={"id": battle_id})
        if not battle:
            raise BattleAdminError("Battle introuvable")

        if battle.status != "DRAFT":
            raise BattleAdminError("Seule une battle en brouillon peut être supprimée")

        await self.prisma.battles.delete(where={"id": battle_id})

        return {
            "success": True,
            "message": "Battle supprimée",
            "battle_id": battle_id,
        }

    async def schedule_battle(self, battle_id: int):
        battle = await self.prisma.battles.find_unique(
            where={"id": battle_id},
            include={"contenders": True},
        )
        if not battle:
            raise BattleAdminError("Battle introuvable")

        if battle.status != "DRAFT":
            raise BattleAdminError("Seule une battle en brouillon peut être planifiée")

        if len(battle.contenders) < 2:
            raise BattleAdminError("Il faut au moins 2 contenders pour planifier la battle")

        updated = await self.prisma.battles.update(
            where={"id": battle_id},
            data={"status": "SCHEDULED"},
        )

        await self.prisma.battle_events.create(
            data={
                "battle_id": battle_id,
                "type": "BATTLE_SCHEDULED",
                "payload": {"status": "SCHEDULED"},
            }
        )

        return updated

    async def start_battle(self, battle_id: int):
        battle = await self.prisma.battles.find_unique(
            where={"id": battle_id},
            include={"contenders": True},
        )
        if not battle:
            raise BattleAdminError("Battle introuvable")

        if battle.status != "SCHEDULED":
            raise BattleAdminError("Seule une battle planifiée peut être démarrée")

        if len(battle.contenders) < 2:
            raise BattleAdminError("Il faut au moins 2 contenders pour démarrer la battle")

        now = datetime.now(timezone.utc)

        updated_battle = await self.prisma.battles.update(
            where={"id": battle_id},
            data={
                "status": "LIVE",
                "started_at": now,
                "is_finished": False,
                "current_round_number": 1,
            },
        )

        for contender in battle.contenders:
            await self.prisma.contenders.update(
                where={"id": contender.id},
                data={
                    "starting_pv": battle.max_pv,
                    "current_pv": battle.max_pv,
                    "is_ko": False,
                    "is_winner": False,
                },
            )

        block_height = battle.start_height if battle.start_height is not None else 0

        await self.prisma.rounds.create(
            data={
                "battle_id": battle_id,
                "block_height": block_height,
                "round_number": 1,
                "status": "LIVE",
                "started_at": now,
                "contender_1_best_diff": 0,
                "contender_2_best_diff": 0,
            }
        )

        await self.prisma.battle_events.create_many(
            data=[
                {
                    "battle_id": battle_id,
                    "type": "BATTLE_STARTED",
                    "payload": {"started_at": now.isoformat()},
                },
                {
                    "battle_id": battle_id,
                    "round_battle_id": battle_id,
                    "round_block_height": block_height,
                    "type": "ROUND_STARTED",
                    "payload": {"round_number": 1},
                },
            ]
        )

        return updated_battle

    async def stop_battle(self, battle_id: int):
        battle = await self.prisma.battles.find_unique(where={"id": battle_id})
        if not battle:
            raise BattleAdminError("Battle introuvable")

        if battle.status != "LIVE":
            raise BattleAdminError("Seule une battle en cours peut être arrêtée")

        now = datetime.now(timezone.utc)

        await self.prisma.rounds.update_many(
            where={
                "battle_id": battle_id,
                "status": "LIVE",
            },
            data={
                "status": "FINISHED",
                "finalized_at": now,
            }
        )

        updated = await self.prisma.battles.update(
            where={"id": battle_id},
            data={
                "status": "FINISHED",
                "finished_at": now,
                "is_finished": True,
            },
        )

        await self.prisma.battle_events.create(
            data={
                "battle_id": battle_id,
                "type": "BATTLE_FINISHED",
                "payload": {"finished_at": now.isoformat()},
            }
        )

        return updated

    async def cancel_battle(self, battle_id: int):
        battle = await self.prisma.battles.find_unique(where={"id": battle_id})
        if not battle:
            raise BattleAdminError("Battle introuvable")

        if battle.status in ("FINISHED", "CANCELLED"):
            raise BattleAdminError("Cette battle ne peut plus être annulée")

        updated = await self.prisma.battles.update(
            where={"id": battle_id},
            data={
                "status": "CANCELLED",
                "is_finished": True,
            },
        )

        await self.prisma.battle_events.create(
            data={
                "battle_id": battle_id,
                "type": "BATTLE_CANCELLED",
                "payload": {},
            }
        )

        return updated