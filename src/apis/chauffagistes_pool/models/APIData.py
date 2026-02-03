from .Pool import Pool
from .User import User
from .Repartition import Repartition
from .BestRecord import BestRecord
from .Node import Node
from typing import Dict, List, TypedDict

class APIDataPayload(TypedDict):
    backup_pool: bool
    pool: Pool
    users: Dict[str, User]
    repartition: Dict[str, Repartition]
    monthly_bests: List[BestRecord]
    node: Node