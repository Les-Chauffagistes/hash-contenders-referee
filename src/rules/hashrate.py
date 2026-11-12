"""Cached pool-api hashrates; no private identifiers are returned to clients."""
import asyncio
import logging
import math
import re
from datetime import datetime, timezone
from time import monotonic
from urllib.parse import quote

from aiohttp import ClientSession, ClientTimeout

log = logging.getLogger(__name__)


def parse_hashrate(value):
    match = re.fullmatch(r"(\d+(?:\.\d+)?)\s*([KMGTPEZ]?)", str(value).strip(), re.I)
    if not match:
        raise ValueError("Invalid pool hashrate")
    result = float(match[1]) * 1000 ** ("KMGTPEZ".index(match[2].upper()) + 1 if match[2] else 0)
    if not math.isfinite(result):
        raise ValueError("Invalid pool hashrate")
    return result


def extract_hashrates(data, address):
    rates = {None: parse_hashrate(data["globalStats"]["hashrate1m"])}
    for worker in data["workers"]:
        name = worker["workername"]
        # Some deployments expose the full address.workername identifier.
        if name.startswith(address + "."):
            name = name[len(address) + 1:]
        key = name.casefold()
        rates[key] = rates.get(key, 0) + parse_hashrate(worker["hashrate1m"])
    return rates


class HashratePoller:
    def __init__(self, base_url, token, interval=30):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.interval = interval
        self.cache = {}

    def get(self, address, worker=None):
        snapshot = self.cache.get(address)
        key = worker.casefold() if worker else None
        value = snapshot[0].get(key) if snapshot else None
        return {
            "hashrate_hs": value,
            "hashrate_fetched_at": snapshot[1] if snapshot else None,
            "hashrate_window_seconds": 60,
            "hashrate_stale": snapshot is None or value is None or monotonic() - snapshot[2] > self.interval * 2,
        }

    async def refresh(self, session, addresses):
        for address in set(self.cache) - addresses:
            del self.cache[address]
        for address in addresses:
            try:
                async with session.get(f"{self.base_url}/v1/stats/{quote(address, safe='')}") as response:
                    response.raise_for_status()
                    rates = extract_hashrates(await response.json(), address)
                self.cache[address] = (rates, datetime.now(timezone.utc).isoformat(), monotonic())
            except Exception:
                # Keep the last successful reading; never log URLs containing addresses.
                log.warning("Could not refresh contender hashrate")

    async def run(self, prisma):
        async with ClientSession(
            headers={"Authorization": f"Bearer {self.token}"},
            timeout=ClientTimeout(total=10),
        ) as session:
            while True:
                started = monotonic()
                try:
                    battles = await prisma.battles.find_many(where={"is_finished": False})
                    addresses = {address for b in battles for address in (b.contender_1_address, b.contender_2_address)}
                    await self.refresh(session, addresses)
                except Exception:
                    log.warning("Could not load active battles for hashrate polling")
                await asyncio.sleep(max(0.1, self.interval - (monotonic() - started)))
