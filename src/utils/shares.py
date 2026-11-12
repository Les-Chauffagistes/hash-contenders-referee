from dataclasses import dataclass
from chauff_cmn.models import PoolWebsocketShareElement
from urllib.parse import quote


def get_worker_name(share: PoolWebsocketShareElement) -> str:
    """Renvoie le nom du worker sans l'adresse ("<adresse>.<worker>" -> "<worker>").

    Seul le préfixe "<adresse>." est retiré, pour préserver les workers dont le
    nom contient lui-même un point. Renvoie "" si le share n'a pas de worker.
    """
    if share.workername == share.username:
        return ""
    return share.workername.removeprefix(f"{share.username}.")


def stream_key(address: str, worker: str | None) -> str:
    """Identifie un flux par son filtre: un curseur de reprise n'est valable qu'avec le même filtre."""
    return f"workername={address}.{worker}" if worker else f"address={address}"


def build_shares_url(api_url: str, address: str, worker: str | None) -> str:
    """Construit l'URL WS `/shares` pour un contender. Si `worker` est renseigné, la
    connexion est restreinte à ce mineur (le pool filtre lui-même via ce query param) ;
    sinon toute la pool de l'adresse compte"""
    base_url = f"{api_url}/v1/shares/stream"
    if worker:
        return f"{base_url}?workername={quote(f"{address}.{worker}", safe = '')}"
    else:
        return f"{base_url}?address={address}"



@dataclass(frozen=True)
class ShareStream:
    """Un flux WS du pool: un filtre (adresse, worker optionnel) et les contenders (1 et/ou 2) qu'il alimente."""
    address: str
    worker: str | None
    contenders: tuple[int, ...]


def contender_streams(battle) -> list[ShareStream]:
    """Un flux par filtre *distinct* de la bataille.

    Deux contenders au même filtre (même adresse et même worker, casse ignorée comme côté pool) partagent un
    flux: deux connexions identiques feraient traiter chaque share deux fois. Mais deux contenders de même
    adresse et de workers différents (Mineur vs Mineur) ont chacun le leur, de même que deux adresses sans
    worker (Pool vs Pool).
    """
    streams: dict[tuple[str, str | None], list[int]] = {}
    for number in (1, 2):
        address = getattr(battle, f"contender_{number}_address")
        worker = getattr(battle, f"contender_{number}_worker") or None
        key = (address, worker.casefold() if worker else None)
        streams.setdefault(key, []).append(number)
    return [
        ShareStream(
            address=address,
            worker=getattr(battle, f"contender_{numbers[0]}_worker") or None,
            contenders=tuple(numbers),
        )
        for (address, _), numbers in streams.items()
    ]
