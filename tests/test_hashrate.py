import unittest
from unittest.mock import AsyncMock, MagicMock

from src.rules.hashrate import HashratePoller, extract_hashrates, parse_hashrate


def payload():
    return {"globalStats": {"hashrate1m": "2 T"}, "workers": [
        {"workername": "addr.Rig1", "hashrate1m": "1.5 T"},
        {"workername": "rig2", "hashrate1m": "0"},
    ]}


class HashrateTests(unittest.IsolatedAsyncioTestCase):
    def test_units_and_invalid_values(self):
        self.assertEqual(parse_hashrate("1.5 T"), 1.5e12)
        self.assertEqual(parse_hashrate("0"), 0)
        for value in ("nan", "-1", None, "broken"):
            with self.assertRaises(ValueError):
                parse_hashrate(value)

    def test_address_and_worker_selection(self):
        rates = extract_hashrates(payload(), "addr")
        poller = HashratePoller("http://pool", "token")
        from time import monotonic
        poller.cache["addr"] = (rates, "timestamp", monotonic())
        self.assertEqual(poller.get("addr")["hashrate_hs"], 2e12)
        self.assertEqual(poller.get("addr", "RIG1")["hashrate_hs"], 1.5e12)
        self.assertEqual(poller.get("addr", "rig2")["hashrate_hs"], 0)
        self.assertFalse(poller.get("addr", "rig2")["hashrate_stale"])
        self.assertIsNone(poller.get("addr", "missing")["hashrate_hs"])
        self.assertTrue(poller.get("addr", "missing")["hashrate_stale"])
        self.assertNotIn("address", poller.get("addr"))
        poller.cache["addr"] = (rates, "timestamp", monotonic() - 61)
        self.assertTrue(poller.get("addr")["hashrate_stale"])

    async def test_refresh_deduplicates_and_preserves_last_success_on_failure(self):
        poller = HashratePoller("http://pool/", "token")
        response = MagicMock()
        response.json = AsyncMock(return_value=payload())
        context = MagicMock()
        context.__aenter__ = AsyncMock(return_value=response)
        context.__aexit__ = AsyncMock(return_value=False)
        session = MagicMock()
        session.get.return_value = context
        await poller.refresh(session, {"addr", "addr"})
        session.get.assert_called_once_with("http://pool/v1/stats/addr")
        previous = poller.cache["addr"]
        session.get.side_effect = OSError("offline")
        await poller.refresh(session, {"addr"})
        self.assertEqual(poller.cache["addr"], previous)
        await poller.refresh(session, set())
        self.assertEqual(poller.cache, {})


if __name__ == "__main__":
    unittest.main()
