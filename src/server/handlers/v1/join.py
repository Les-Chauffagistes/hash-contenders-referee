from aiohttp.web import json_response


async def join(request):
    prisma = request.config_dict["prisma"]
    body = await request.json()

    battle_id = body.get("battle_id")
    user_id = body.get("user_id")
    address = body.get("address")
    worker = body.get("worker")

    if not battle_id:
        return json_response({"error": "battle_id required"}, status=400)

    if not user_id:
        return json_response({"error": "user_id required"}, status=400)

    if not address:
        return json_response({"error": "address required"}, status=400)

    battle = await prisma.battles.find_unique(
        where={"id": int(battle_id)},
        include={"entries": True},
    )

    if not battle:
        return json_response({"error": "battle not found"}, status=404)

    if len(battle.entries) >= 2:
        return json_response({"error": "battle full"}, status=400)

    await prisma.battle_entries.create(
        data={
            "battle_id": int(battle_id),
            "user_id": int(user_id),
            "slot": 2,
            "address": address,
            "worker_name": worker,
            "current_pv": battle.initial_pv,
            "status": "JOINED",
        },
    )

    await prisma.battles.update(
        where={"id": int(battle_id)},
        data={"status": "MATCHED"},
    )

    return json_response({"success": True})