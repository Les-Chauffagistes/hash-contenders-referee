from datetime import datetime, timezone

from chauff_cmn.models import PoolWebsocketShareElement


def make_share(
    address: str,
    block_height: int,
    worker: str = "",
    diff: float = 100.0,
    result: bool = True,
    parse_error: bool = False,
) -> PoolWebsocketShareElement:
    """Crée une share de test au format du WebSocket du pool.

    `workername` suit le format réel du pool : "<adresse>.<worker>".
    """
    return PoolWebsocketShareElement(
        type="share",
        share_id="test:0/0.sharelog:0",
        epoch=1,
        seq=0,
        instance="test",
        created_at=datetime.now(timezone.utc),
        workinfoid=1,
        block_height=block_height,
        username=address,
        workername=f"{address}.{worker}",
        diff=diff,
        sdiff=float(diff),
        result=result,
        parse_error=parse_error,
    )
