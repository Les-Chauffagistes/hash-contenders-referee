import pytest

from src.utils.shares import get_worker_name
from tests.factories import make_share


def test_returns_worker_without_address_prefix():
    assert get_worker_name(make_share("bc1_address", 400, worker="Hugo")) == "Hugo"


def test_preserves_dots_inside_worker_name():
    assert get_worker_name(make_share("bc1_address", 400, worker="rig.1")) == "rig.1"


def test_workername_equal_to_address_gives_empty_worker():
    share = make_share("bc1_address", 400)
    share.workername = "bc1_address"
    assert get_worker_name(share) == ""


def test_empty_worker_after_dot_gives_empty_worker():
    assert get_worker_name(make_share("bc1_address", 400, worker="")) == ""


@pytest.mark.parametrize("worker", ["bc1_address", "bc1_address.x"])
def test_worker_named_like_address_is_not_over_stripped(worker):
    share = make_share("bc1_address", 400, worker=worker)
    assert get_worker_name(share) == worker
