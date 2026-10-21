from chauff_cmn.models import PoolWebsocketShareElement


def get_worker_name(share: PoolWebsocketShareElement) -> str:
    """Renvoie le nom du worker sans l'adresse ("<adresse>.<worker>" -> "<worker>").

    Seul le préfixe "<adresse>." est retiré, pour préserver les workers dont le
    nom contient lui-même un point. Renvoie "" si le share n'a pas de worker.
    """
    if share.workername == share.username:
        return ""
    return share.workername.removeprefix(f"{share.username}.")
