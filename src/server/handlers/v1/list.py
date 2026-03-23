from aiohttp.web import json_response


async def list_battles(request):
    prisma = request.config_dict["prisma"]

    battles = await prisma.battles.find_many(
        include={"entries": True},
        order={"created_at": "desc"},
    )

    result = []

    for b in battles:
        e1 = next((e for e in b.entries if e.slot == 1), None)
        e2 = next((e for e in b.entries if e.slot == 2), None)

        result.append({
            "id": int(b.id),
            "status": b.status,
            "pv": b.initial_pv,
            "player1": e1.address if e1 else None,
            "player2": e2.address if e2 else None,
        })

    return json_response(result)