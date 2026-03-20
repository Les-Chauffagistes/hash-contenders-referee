from init import app
from prisma import Prisma


def get_duel_contenders(battle):
    contenders = getattr(battle, "contenders", None) or []

    contender_1 = next((c for c in contenders if c.slot == 1), None)
    contender_2 = next((c for c in contenders if c.slot == 2), None)

    return contender_1, contender_2


async def get_battles():
    prisma: Prisma = app["prisma"]

    battles = await prisma.battles.find_many(
        include={"contenders": True},
        order={"created_at": "desc"},
    )

    result = []

    for battle in battles:
        contender_1, contender_2 = get_duel_contenders(battle)

        result.append({
            "id": int(battle.id),
            "name": battle.name,
            "status": battle.status,
            "mode": battle.mode,
            "start_height": battle.start_height,
            "rounds": battle.rounds,
            "current_round_number": battle.current_round_number,
            "max_pv": battle.max_pv,
            "is_finished": battle.is_finished,
            "are_addresses_privates": battle.are_addresses_privates,
            "created_at": battle.created_at.isoformat() if battle.created_at else None,
            "updated_at": battle.updated_at.isoformat() if battle.updated_at else None,
            "contender_1_name": contender_1.name if contender_1 else None,
            "contender_2_name": contender_2.name if contender_2 else None,
        })

    return result