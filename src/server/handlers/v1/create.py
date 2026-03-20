from json import JSONDecodeError

from prisma import Prisma
from aiohttp.web_request import Request
from aiohttp.web_response import json_response

import zon

from .base import routes


validator = zon.record({
    "contender_1_address": zon.string(),
    "contender_1_name": zon.string(),
    "contender_2_address": zon.string(),
    "contender_2_name": zon.string(),
    "contenders_pv": zon.number().int(),
    "rounds": zon.number().int(),
    "start_height": zon.number().int(),
    "are_addresses_privates": zon.boolean()
})


def serialize_battle(battle):
    return {
        "id": int(battle.id),
        "name": battle.name,
        "description": battle.description,
        "status": battle.status,
        "mode": battle.mode,
        "start_height": battle.start_height,
        "planned_start_at": battle.planned_start_at.isoformat() if battle.planned_start_at else None,
        "started_at": battle.started_at.isoformat() if battle.started_at else None,
        "finished_at": battle.finished_at.isoformat() if battle.finished_at else None,
        "rounds": battle.rounds,
        "current_round_number": battle.current_round_number,
        "max_pv": battle.max_pv,
        "is_finished": battle.is_finished,
        "are_addresses_privates": battle.are_addresses_privates,
        "created_at": battle.created_at.isoformat() if battle.created_at else None,
        "updated_at": battle.updated_at.isoformat() if battle.updated_at else None,
        "contenders": [
            {
                "id": int(contender.id),
                "battle_id": int(contender.battle_id),
                "slot": contender.slot,
                "name": contender.name,
                "address": contender.address,
                "current_pv": contender.current_pv,
                "starting_pv": contender.starting_pv,
                "is_ko": contender.is_ko,
                "is_winner": contender.is_winner,
                "team_name": contender.team_name,
                "created_at": contender.created_at.isoformat() if contender.created_at else None,
                "updated_at": contender.updated_at.isoformat() if contender.updated_at else None,
            }
            for contender in (battle.contenders or [])
        ],
    }


@routes.post("/battle")
async def create_battle(request: Request):
    prisma: Prisma = request.config_dict["prisma"]

    try:
        data = await request.json()
        validated_data = validator.validate(data)

        battle_data = {
            "name": f'{validated_data["contender_1_name"]} vs {validated_data["contender_2_name"]}',
            "start_height": validated_data["start_height"],
            "rounds": validated_data["rounds"],
            "max_pv": validated_data["contenders_pv"],
            "are_addresses_privates": validated_data["are_addresses_privates"],
            "contenders": {
                "create": [
                    {
                        "slot": 1,
                        "name": validated_data["contender_1_name"],
                        "address": validated_data["contender_1_address"],
                        "current_pv": validated_data["contenders_pv"],
                        "starting_pv": validated_data["contenders_pv"],
                    },
                    {
                        "slot": 2,
                        "name": validated_data["contender_2_name"],
                        "address": validated_data["contender_2_address"],
                        "current_pv": validated_data["contenders_pv"],
                        "starting_pv": validated_data["contenders_pv"],
                    },
                ]
            },
        }

        battle = await prisma.battles.create(
            data=battle_data,
            include={"contenders": True},
        )

    except JSONDecodeError:
        return json_response({"error": "Invalid JSON"}, status=400)

    except zon.ZonError:
        return json_response({"error": "Invalid data"}, status=400)

    return json_response(serialize_battle(battle))