from aiohttp.web import json_response


async def status(request):
    prisma = request.config_dict["prisma"]
    battle_id = int(request.match_info["id"])

    battle = await prisma.battles.find_unique(
        where={"id": battle_id},
        include={
            "entries": True,
            "rounds": {
                "order": {"round_number": "asc"}
            }
        },
    )

    if not battle:
        return json_response({"error": "not found"}, status=404)

    entries = []
    for e in battle.entries:
        entries.append({
            "slot": e.slot,
            "address": e.address,
            "worker": e.worker_name,
            "pv": e.current_pv,
            "rounds_won": e.rounds_won,
            "status": e.status,
        })

    rounds = []
    for r in battle.rounds:
        rounds.append({
            "round": r.round_number,
            "block": r.block_height,
            "winner_entry_id": int(r.winner_entry_id) if r.winner_entry_id is not None else None,
        })

    return json_response({
        "id": int(battle.id),
        "status": battle.status,
        "initial_pv": battle.initial_pv,
        "entries": entries,
        "rounds": rounds,
    })