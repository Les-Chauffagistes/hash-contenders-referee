import pytest
import zon
from src.server.handlers.v1.create import validator


def _valid_payload(**overrides):
    payload = {
        "contender_1_address": "addr1",
        "contender_1_name": "Contender 1",
        "contender_2_address": "addr2",
        "contender_2_name": "Contender 2",
        "contenders_pv": 10,
        "rounds": 5,
        "start_height": 100,
        "are_addresses_privates": False,
    }
    payload.update(overrides)
    return payload


def test_validator_accepts_payload_without_worker_fields():
    """Non-régression : le mode Pool vs Pool historique reste valide sans worker."""
    result = validator.validate(_valid_payload())
    assert "contender_1_worker" not in result
    assert "contender_2_worker" not in result


def test_validator_accepts_and_keeps_worker_fields_when_provided():
    result = validator.validate(
        _valid_payload(contender_1_worker="rig1", contender_2_worker="rig2")
    )
    assert result["contender_1_worker"] == "rig1"
    assert result["contender_2_worker"] == "rig2"


def test_validator_keeps_empty_worker_as_empty_string():
    """`zon.optional()` n'omet que les valeurs `None`/absentes du payload, pas les
    chaînes vides : celles-ci passent intactes. Sans incidence en pratique — le
    formulaire front n'envoie jamais de chaîne vide (il omet le champ), et le reste
    de la chaîne (`Referee._identify_contender`, `getBattleMode`) traite déjà `""`
    comme `None` (falsy) — mais documenté ici pour ne pas supposer le contraire par
    erreur."""
    result = validator.validate(_valid_payload(contender_1_worker=""))
    assert result["contender_1_worker"] == ""


def test_validator_still_rejects_missing_required_fields():
    with pytest.raises(zon.ZonError):
        validator.validate(_valid_payload(contender_1_address=None))
