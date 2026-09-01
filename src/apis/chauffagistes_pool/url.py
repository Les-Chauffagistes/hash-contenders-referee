from urllib.parse import quote


def build_shares_url(base_url: str, address: str, worker: str | None) -> str:
    """Construit l'URL WS `/shares` pour un contender. Si `worker` est renseigné, la
    connexion est restreinte à ce mineur (le pool filtre lui-même via ce query param) ;
    sinon toute la pool de l'adresse compte, comme aujourd'hui."""
    url = f"{base_url}/shares?address={address}"
    if worker:
        url += f"&worker={quote(worker, safe='')}"
    return url
