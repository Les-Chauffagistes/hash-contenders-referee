from prisma import Prisma


class ContenderAdminError(Exception):
    pass


class ContenderAdminService:
    def __init__(self, prisma: Prisma):
        self.prisma = prisma

    async def list_contenders(self, battle_id: int):
        battle = await self.prisma.battles.find_unique(where={"id": battle_id})
        if not battle:
            raise ContenderAdminError("Battle introuvable")

        return await self.prisma.contenders.find_many(
            where={"battle_id": battle_id},
            order={"slot": "asc"},
        )

    async def add_contender(self, battle_id: int, payload):
        battle = await self.prisma.battles.find_unique(where={"id": battle_id})
        if not battle:
            raise ContenderAdminError("Battle introuvable")

        if battle.status not in ("DRAFT", "SCHEDULED"):
            raise ContenderAdminError("Impossible d'ajouter un contender sur cette battle")

        existing_slot = await self.prisma.contenders.find_first(
            where={
                "battle_id": battle_id,
                "slot": payload.slot,
            }
        )
        if existing_slot:
            raise ContenderAdminError(f"Le slot {payload.slot} est déjà utilisé")

        existing_address = await self.prisma.contenders.find_first(
            where={
                "battle_id": battle_id,
                "address": payload.address,
            }
        )
        if existing_address:
            raise ContenderAdminError("Cette adresse est déjà utilisée dans cette battle")

        return await self.prisma.contenders.create(
            data={
                "battle_id": battle_id,
                "slot": payload.slot,
                "name": payload.name,
                "address": payload.address,
                "team_name": payload.team_name,
                "starting_pv": battle.max_pv,
                "current_pv": battle.max_pv,
                "is_ko": False,
                "is_winner": False,
            }
        )

    async def update_contender(self, contender_id: int, payload):
        contender = await self.prisma.contenders.find_unique(
            where={"id": contender_id},
            include={"battle": True},
        )
        if not contender:
            raise ContenderAdminError("Contender introuvable")

        if contender.battle.status not in ("DRAFT", "SCHEDULED"):
            raise ContenderAdminError("Impossible de modifier ce contender maintenant")

        update_data = {}
        for field_name in ["name", "address", "team_name"]:
            value = getattr(payload, field_name)
            if value is not None:
                update_data[field_name] = value

        if "address" in update_data:
            existing = await self.prisma.contenders.find_first(
                where={
                    "battle_id": contender.battle_id,
                    "address": update_data["address"],
                    "NOT": {"id": contender_id},
                }
            )
            if existing:
                raise ContenderAdminError("Cette adresse est déjà utilisée dans cette battle")

        if not update_data:
            raise ContenderAdminError("Aucune donnée à mettre à jour")

        return await self.prisma.contenders.update(
            where={"id": contender_id},
            data=update_data,
        )

    async def delete_contender(self, contender_id: int):
        contender = await self.prisma.contenders.find_unique(
            where={"id": contender_id},
            include={"battle": True},
        )
        if not contender:
            raise ContenderAdminError("Contender introuvable")

        if contender.battle.status not in ("DRAFT", "SCHEDULED"):
            raise ContenderAdminError("Impossible de supprimer ce contender maintenant")

        await self.prisma.contenders.delete(where={"id": contender_id})

        return {
            "success": True,
            "message": "Contender supprimé",
            "contender_id": contender_id,
        }