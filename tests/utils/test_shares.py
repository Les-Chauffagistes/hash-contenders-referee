from types import SimpleNamespace

import pytest

from src.utils.shares import ShareStream, contender_streams, get_worker_name
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


def make_battle(a1="addr1", w1=None, a2="addr2", w2=None):
    return SimpleNamespace(
        contender_1_address=a1, contender_1_worker=w1, contender_2_address=a2, contender_2_worker=w2
    )


def test_pool_vs_pool_opens_one_stream_per_address():
    assert contender_streams(make_battle()) == [
        ShareStream("addr1", None, (1,)),
        ShareStream("addr2", None, (2,)),
    ]


def test_miner_vs_miner_on_same_address_opens_one_stream_per_worker():
    assert contender_streams(make_battle("a", "x", "a", "y")) == [
        ShareStream("a", "x", (1,)),
        ShareStream("a", "y", (2,)),
    ]


def test_identical_filters_share_one_stream_ignoring_worker_case():
    assert contender_streams(make_battle("a", "Rig", "a", "rig")) == [ShareStream("a", "Rig", (1, 2))]
    assert contender_streams(make_battle("a", None, "a", "")) == [ShareStream("a", None, (1, 2))]


def test_same_address_one_with_worker_one_without_are_distinct_streams():
    assert len(contender_streams(make_battle("a", "x", "a", None))) == 2


def test_mixed_pool_vs_miner():
    assert contender_streams(make_battle("a", None, "b", "x")) == [
        ShareStream("a", None, (1,)),
        ShareStream("b", "x", (2,)),
    ]
