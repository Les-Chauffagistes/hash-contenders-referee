from aiohttp.web import json_response


async def create(request):
    prisma = request.config_dict["prisma"]
    body = await request.json()

    owner_user_id = body.get("owner_user_id")
    address = body.get("address")
    worker = body.get("worker")
    pv = int(body.get("initial_pv", 3))
    mode = body.get("mode", "NO_RULES")

    if not owner_user_id:
        return json_response({"error": "owner_user_id required"}, status=400)

    if not address:
        return json_response({"error": "address required"}, status=400)

    owner = await prisma.users.find_unique(
        where={"id": int(owner_user_id)}
    )
    if owner is None:
        return json_response({"error": "owner user not found"}, status=400)

    battle = await prisma.battles.create(
        data={
            "owner_user_id": int(owner_user_id),
            "status": "OPEN",
            "initial_pv": pv,
            "matching_mode": mode,
            "entries": {
                "create": {
                    "user_id": int(owner_user_id),
                    "slot": 1,
                    "address": address,
                    "worker_name": worker,
                    "current_pv": pv,
                    "status": "JOINED",
                }
            },
        },
        include={"entries": True},
    )

    return json_response({"battle_id": int(battle.id)})