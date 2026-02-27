from typing import NotRequired, TypedDict
from prisma import Prisma
from prisma.models import battles, rounds
from init import app, log, referee
from src.server.utils.formatter import format_row, format_rows


class ContenderInfo(TypedDict):
    address: NotRequired[str]
    pv: int
    name: str
    current_round_best_diff: int


class BattleResponse(TypedDict):
    battle_id: int
    rounds: int
    contenders_base_pv: int
    start_height: int | None
    hits: list
    is_finished: bool
    current_round: int
    contender_info: list[ContenderInfo]

# HTPP API response
async def get_battle_status(battle_id: int | str, include_hits: bool) -> BattleResponse:
    prisma: Prisma = app["prisma"]

    battle = await prisma.battles.find_unique(
        where={"id": int(battle_id)},
        include={"all_rounds": True} if include_hits else None,
    )
    if not battle:
        log.warn("404")
        raise Exception("Battle not found")

    contender_1_pv, contender_2_pv = await referee.compute_pv(battle)
    current_round_block_height = await referee.get_current_round(battle.id)
    current_round_number = await referee.get_current_round_number(battle.id)
    if current_round_block_height:
        best_diff1 = current_round_block_height.contender_1_best_diff
        best_diff2 = current_round_block_height.contender_2_best_diff
    
    else:
        best_diff1 = 0
        best_diff2 = 0

    contenders_infos: list[ContenderInfo] = [
        {
            "address": battle.contender_1_address,
            "pv": contender_1_pv,
            "name": battle.contender_1_name,
            "current_round_best_diff": best_diff1
        },
        {
            "address": battle.contender_2_address,
            "pv": contender_2_pv,
            "name": battle.contender_2_name,
            "current_round_best_diff": best_diff2
        },
    ]

    if battle.are_addresses_privates:
        for contender_info in contenders_infos:
            contender_info.pop("address")

    if include_hits:
        hits = await prisma.rounds.find_many(
            where={"battle_id": int(battle_id)}, order={"block_height": "desc"}
        )

    else:
        hits: list[rounds] = []

    return BattleResponse(
        battle_id=battle.id,
        rounds=battle.rounds,
        contenders_base_pv=battle.contenders_pv,
        start_height=battle.start_height,
        hits=list(format_rows(hits)),
        current_round=current_round_number,
        is_finished=battle.is_finished,
        contender_info=contenders_infos,
    )


async def get_battle_hits(battle_id: str | int):
    prisma: Prisma = app["prisma"]

    hits = await prisma.rounds.find_many(
        where={"battle_id": int(battle_id)}, order={"block_height": "desc"}
    )

    return format_rows(hits)

websockets = []
