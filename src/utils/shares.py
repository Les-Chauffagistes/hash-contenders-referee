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


def build_shares_url(api_url: str, address: str, worker: str | None) -> str:
    """Construit l'URL WS `/shares` pour un contender. Si `worker` est renseigné, la
    connexion est restreinte à ce mineur (le pool filtre lui-même via ce query param) ;
    sinon toute la pool de l'adresse compte"""
    base_url = f"{api_url}/v1/shares/stream"
    if worker:
        return f"{base_url}?workername={quote(f"{address}.{worker}", safe = '')}"
    else:
        return f"{base_url}?address={address}"
