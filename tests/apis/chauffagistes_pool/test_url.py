from src.apis.chauffagistes_pool.url import build_shares_url


def test_build_shares_url_without_worker_matches_current_format():
    """Non-régression : sans worker ciblé, l'URL reste identique au format actuel (mode Pool vs Pool)."""
    url = build_shares_url("ws://localhost:8765", "bc1_address", None)
    assert url == "ws://localhost:8765/shares?address=bc1_address"


def test_build_shares_url_with_worker_appends_worker_param():
    url = build_shares_url("ws://localhost:8765", "bc1_address", "rig1")
    assert url == "ws://localhost:8765/shares?address=bc1_address&worker=rig1"


def test_build_shares_url_quotes_worker_with_special_characters():
    url = build_shares_url("ws://localhost:8765", "bc1_address", "rig one/two")
    assert url == "ws://localhost:8765/shares?address=bc1_address&worker=rig%20one%2Ftwo"


def test_build_shares_url_with_empty_worker_omits_worker_param():
    """Une chaîne vide est traitée comme 'aucun worker ciblé' (falsy), pas comme worker=""."""
    url = build_shares_url("ws://localhost:8765", "bc1_address", "")
    assert url == "ws://localhost:8765/shares?address=bc1_address"
