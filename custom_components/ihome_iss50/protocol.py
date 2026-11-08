"""Direct-IP HAP transport. No multicast discovery or Apple Home required."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from aiohomekit.characteristic_cache import CharacteristicCacheMemory
from aiohomekit.controller.ip.controller import IpController
from aiohomekit.controller.ip.discovery import IpDiscovery
from aiohomekit.model import Categories
from aiohomekit.model.feature_flags import FeatureFlags
from aiohomekit.model.status_flags import StatusFlags
from aiohomekit.zeroconf import HomeKitService

# Standard HAP characteristics; proprietary sound data is deliberately not guessed.
KINDS = {
    "11": "temperature",
    "10": "humidity",
    "6B": "illuminance",
    "22": "motion",
    "71": "occupancy",
}


@dataclass(frozen=True)
class Reading:
    aid: int
    iid: int
    kind: str
    events: bool

    @property
    def key(self):
        return (self.aid, self.iid)


def parse_readings(accessories: list[dict]) -> tuple[list[Reading], dict]:
    readings, values = [], {}
    for accessory in accessories:
        for service in accessory.get("services", []):
            for char in service.get("characteristics", []):
                raw = str(char.get("type", "")).upper().split("-")[0].lstrip("0")
                if raw not in KINDS or "pr" not in char.get("perms", []):
                    continue
                item = Reading(
                    accessory["aid"], char["iid"], KINDS[raw], "ev" in char.get("perms", [])
                )
                readings.append(item)
                if "value" in char:
                    values[item.key] = {"value": char["value"]}
    return readings, values


def make_controller():
    # Do not start ZeroconfController: direct IP pairing has no dependency on mDNS.
    return IpController(CharacteristicCacheMemory(), None)


def load_pairing(host: str, port: int, data: dict):
    """Restore keys using the currently configured endpoint."""
    updated = dict(data)
    updated.update(AccessoryIP=host, AccessoryIPs=[host], AccessoryPort=port)
    pairing = make_controller().load_pairing("iss50", updated)
    if pairing is None:
        raise ValueError("Invalid stored pairing")
    return pairing


async def validate_connection(host: str, port: int, data: dict):
    """Authenticate the new endpoint with existing keys, without re-pairing."""
    pairing = load_pairing(host, port, data)
    try:
        async with asyncio.timeout(20):
            await pairing.list_accessories_and_characteristics()
    finally:
        await pairing.shutdown()


async def unpair_direct(host: str, port: int, data: dict):
    """Remove only the controller represented by these saved credentials."""
    pairing = load_pairing(host, port, data)
    try:
        async with asyncio.timeout(15):
            await pairing.remove_pairing(data["iOSPairingId"])
    finally:
        await pairing.shutdown()


def make_discovery(controller, host: str, port: int):
    return IpDiscovery(
        controller,
        HomeKitService(
            name="iHome iSS50",
            id="00:00:00:00:00:00",
            model="iSS50",
            feature_flags=FeatureFlags(0),
            status_flags=StatusFlags.UNPAIRED,
            config_num=1,
            state_num=1,
            category=Categories.SENSOR,
            protocol_version="1.1",
            type="_hap._tcp.local.",
            address=host,
            addresses=[host],
            port=port,
        ),
    )


async def is_hap_port(host: str, port: int, connect_timeout: float = 0.5) -> bool:
    """Read-only probe. Never submit a pairing request during port detection."""
    writer = None
    try:
        async with asyncio.timeout(connect_timeout):
            reader, writer = await asyncio.open_connection(host, port)
        async with asyncio.timeout(2):
            writer.write(
                f"GET /accessories HTTP/1.1\r\nHost: {host}:{port}\r\nConnection: close\r\n\r\n".encode()
            )
            await writer.drain()
            header = await reader.readuntil(b"\r\n\r\n")
            lower = header.lower()
            # HAP's authentication-required response is HTTP 470, rather than 401.
            if header.split(b"\r\n", 1)[0].split()[1:2] == [b"470"]:
                return True
            if b"application/hap+json" in lower:
                return True
    except OSError, TimeoutError, asyncio.IncompleteReadError, asyncio.LimitOverrunError:
        pass
    finally:
        if writer is not None:
            writer.close()
            try:
                await writer.wait_closed()
            except OSError:
                pass
    return False


async def find_port(host: str) -> int:
    """Probe only the supplied device. Common ports first, then remaining TCP ports."""
    preferred = [80, 8080, 51826, 5000, 5556]
    for port in preferred:
        if await is_hap_port(host, port):
            return port
    ports = iter(p for p in range(1, 65536) if p not in preferred)
    found = asyncio.get_running_loop().create_future()

    async def worker():
        for port in ports:
            if found.done():
                return
            if await is_hap_port(host, port):
                if not found.done():
                    found.set_result(port)
                return

    workers = [asyncio.create_task(worker()) for _ in range(128)]
    group = asyncio.gather(*workers, return_exceptions=True)
    try:
        done, _ = await asyncio.wait([found, group], return_when=asyncio.FIRST_COMPLETED)
        if found in done:
            return found.result()
        await group
        raise ConnectionError("No HomeKit TCP endpoint responded on this IP address")
    finally:
        for task in workers:
            task.cancel()
        await asyncio.gather(*workers, return_exceptions=True)
        if not found.done():
            found.cancel()
        await group


async def pair_direct(host: str, port: int, pin: str) -> dict[str, Any]:
    controller = make_controller()
    discovery = make_discovery(controller, host, port)
    pairing = None
    try:
        async with asyncio.timeout(60):
            finish = await discovery.async_start_pairing("iss50")
            pairing = await finish(pin)
            # This ID is the authenticated device ID returned by HAP, not the
            # placeholder description used solely to open the TCP connection.
            return dict(pairing.pairing_data)
    finally:
        await discovery.close()
        if pairing is not None:
            await pairing.shutdown()
