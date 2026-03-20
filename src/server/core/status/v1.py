from typing import NotRequired, TypedDict

from prisma import Prisma
from prisma.models import rounds

from init import app, log, referee
from src.server.utils.formatter import format_rows


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


def get_duel_contenders(battle):
    contenders = getattr(battle, "contenders", None) or []

    contender_1 = next((c for c in contenders if c.slot == 1), None)
    contender_2 = next((c for c in contenders if c.slot == 2), None)

    return contender_1, contender_2


async def get_battle_status(battle_id: int | str, include_hits: bool) -> BattleResponse:
    prisma: Prisma = app["prisma"]

    battle = await prisma.battles.find_unique(
        where={"id": int(battle_id)},
        include={
            "contenders": True,
            **({"all_rounds": True} if include_hits else {}),
        },
    )

    if not battle:
        log.warn("404")
        raise Exception("Battle not found")

    contender_1, contender_2 = get_duel_contenders(battle)
    if contender_1 is None or contender_2 is None:
        raise Exception(f"Battle {battle.id} has missing contenders")

    contender_1_pv, contender_2_pv = await referee.compute_pv(battle)
    current_round = await referee.get_current_round(battle.id)
    current_round_number = await referee.get_current_round_number(battle.id)

    if current_round:
        best_diff1 = current_round.contender_1_best_diff
        best_diff2 = current_round.contender_2_best_diff
    else:
        best_diff1 = 0
        best_diff2 = 0

    contenders_infos: list[ContenderInfo] = [
        {
            "address": contender_1.address,
            "pv": contender_1_pv,
            "name": contender_1.name,
            "current_round_best_diff": best_diff1,
        },
        {
            "address": contender_2.address,
            "pv": contender_2_pv,
            "name": contender_2.name,
            "current_round_best_diff": best_diff2,
        },
    ]

    if battle.are_addresses_privates:
        for contender_info in contenders_infos:
            contender_info.pop("address", None)

    if include_hits:
        hits = await prisma.rounds.find_many(
            where={"battle_id": int(battle_id)},
            order={"block_height": "desc"},
        )
    else:
        hits: list[rounds] = []

    return BattleResponse(
        battle_id=int(battle.id),
        rounds=battle.rounds,
        contenders_base_pv=battle.max_pv,
        start_height=battle.start_height,
        hits=list(format_rows(hits)),
        current_round=current_round_number,
        is_finished=battle.is_finished,
        contender_info=contenders_infos,
    )


async def get_battle_hits(battle_id: str | int):
    prisma: Prisma = app["prisma"]

    hits = await prisma.rounds.find_many(
        where={"battle_id": int(battle_id)},
        order={"block_height": "desc"},
    )

    return format_rows(hits)


websockets = []