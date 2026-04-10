from datetime import datetime
from state import ClientWebsockets
from prisma.models import battles
from pool_api_types.models import Share


class WebsocketBroadcaster:
    client_websockets: ClientWebsockets

    async def new_best_share(self, battle: battles, contender: str, payload: Share):
        await self.client_websockets.broadcast(
            battle.id,
            {
                "type": "BEST_SHARE_UPDATE",
                "user": contender,
                "diff": payload.sdiff,
            },
        )

    async def new_round(self, battle: battles, round_number: int, payload: Share):
        await self.client_websockets.broadcast(
            battle.id,
            {
                "type": "ROUND_UPDATE",
                "round": round_number,
                "block_height": payload.round,
            },
        )
    
    async def hit_result(self, battle: battles, winner: int, block_height: int, contender_1_best_diff: int, contender_2_best_diff: int, contender_1_pv: int, contender_2_pv: int):
        await self.client_websockets.broadcast(
            battle.id,
            {
                "type": "HIT_RESULT",
                # "round": round_number,
                "block_height": hex(block_height),
                "winner": winner,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "contender_1_best_diff": contender_1_best_diff,
                "contender_2_best_diff": contender_2_best_diff,
                "contender_1_pv": contender_1_pv,
                "contender_2_pv": contender_2_pv
            },
    )

    async def battle_end(self, battle: battles, winner: int, contender_1_pv: int, contender_2_pv: int):
        await self.client_websockets.broadcast(
            battle.id,
            {
                "type": "BATTLE_END",
                "winner": winner,
                "contender_1_pv": contender_1_pv,
                "contender_2_pv": contender_2_pv,
            },
    )