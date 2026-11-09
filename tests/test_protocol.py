"""Actual TCP and HAP interoperability tests, not just implementation mocks."""

import asyncio
import importlib.util
import socket
import sys
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "iss50_protocol", Path(__file__).parents[1] / "custom_components/ihome_iss50/protocol.py"
)
p = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = p
spec.loader.exec_module(p)


@pytest.mark.asyncio
async def test_probe_accepts_hap_rejects_normal_web_server():
    async def serve(reader, writer):
        await reader.readuntil(b"\r\n\r\n")
        writer.write(b"HTTP/1.1 470 Connection Authorization Required\r\nContent-Length: 0\r\n\r\n")
        await writer.drain()
        writer.close()

    async def normal(reader, writer):
        await reader.readuntil(b"\r\n\r\n")
        writer.write(b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n")
        await writer.drain()
        writer.close()

    for handler, expected in [(serve, True), (normal, False)]:
        server = await asyncio.start_server(handler, "127.0.0.1", 0)
        async with server:
            assert await p.is_hap_port("127.0.0.1", server.sockets[0].getsockname()[1]) is expected


def test_standard_uuid_mapping_and_missing_read_permission():
    chars = [
        {
            "iid": 1,
            "type": "00000011-0000-1000-8000-0026BB765291",
            "perms": ["pr", "ev"],
            "value": 22.5,
        },
        {"iid": 2, "type": "10", "perms": ["pr"], "value": 45},
        {"iid": 3, "type": "6B", "perms": ["pr"], "value": 50},
        {"iid": 4, "type": "22", "perms": ["pr", "ev"], "value": False},
        {"iid": 5, "type": "71", "perms": ["pr"], "value": 1},
        {"iid": 6, "type": "11", "perms": ["pw"]},
        {"iid": 7, "type": "FAKE-UUID", "perms": ["pr"]},
    ]
    readings, values = p.parse_readings([{"aid": 1, "services": [{"characteristics": chars}]}])
    assert [r.kind for r in readings] == [
        "temperature",
        "humidity",
        "illuminance",
        "motion",
        "occupancy",
    ]
    assert values[(1, 1)]["value"] == 22.5
    assert readings[0].events
    assert (1, 6) not in values


@pytest.mark.asyncio
async def test_scan_finds_nonstandard_port_without_leaking_tasks(monkeypatch):
    async def probe(host, port, connect_timeout=0.5):
        await asyncio.sleep(0)
        return port == 1234

    monkeypatch.setattr(p, "is_hap_port", probe)
    before = set(asyncio.all_tasks())
    assert await p.find_port("127.0.0.1") == 1234
    await asyncio.sleep(0)
    assert set(asyncio.all_tasks()) <= before


@pytest.mark.asyncio
async def test_full_scan_reports_no_endpoint(monkeypatch):
    async def probe(*args):
        return False

    monkeypatch.setattr(p, "is_hap_port", probe)
    with pytest.raises(ConnectionError):
        await p.find_port("127.0.0.1")


@pytest.mark.asyncio
async def test_real_srp_pairing_encrypted_read_and_credential_restore(tmp_path):
    from uuid import UUID

    from pyhap.accessory import Accessory
    from pyhap.accessory_driver import AccessoryDriver
    from pyhap.characteristic import Characteristic
    from pyhap.service import Service

    # Reserve an ephemeral port before the simulator binds.
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    driver = AccessoryDriver(
        address="127.0.0.1",
        listen_address="127.0.0.1",
        port=port,
        pincode=b"321-54-987",
        persist_file=str(tmp_path / "simulator.state"),
        loop=asyncio.get_running_loop(),
        advertise=False,
    )
    accessory = Accessory(driver, "Simulated iSS50")
    temp = accessory.add_preload_service("TemperatureSensor")
    temp.configure_char("CurrentTemperature", value=23.5)
    humidity = accessory.add_preload_service("HumiditySensor")
    humidity.configure_char("CurrentRelativeHumidity", value=47)
    # Synthetic vendor field tests the new discovery path without claiming a
    # hardware-derived iSS50 UUID. Pairing is performed once, before restoration.
    sound_service = Service(UUID("12345678-1234-5678-ABCD-123456789000"), "Sound Sensor")
    sound = Characteristic(
        "Sound Detected",
        UUID("12345678-1234-5678-ABCD-123456789001"),
        {
            "Format": "bool",
            "Permissions": ["pr", "ev"],
        },
    )
    sound_service.add_characteristic(sound)
    accessory.add_service(sound_service)
    driver.add_accessory(accessory)
    await driver.async_start()
    pairing = None
    try:
        assert await p.is_hap_port("127.0.0.1", port)
        data = await p.pair_direct("127.0.0.1", port, "321-54-987")
        assert data["AccessoryPairingID"] != "00:00:00:00:00:00"
        assert "321-54-987" not in str(data)
        # Reconstruct from persisted data, not the object used during pairing.
        pairing = p.make_controller().load_pairing("restored", data)
        database = await pairing.list_accessories_and_characteristics()
        readings, _ = p.parse_readings(database)
        by_kind = {r.kind: r for r in readings}
        key = by_kind["temperature"].key
        assert (await pairing.get_characteristics([key]))[key]["value"] == 23.5
        key = by_kind["humidity"].key
        assert (await pairing.get_characteristics([key]))[key]["value"] == 47
        # A real notification travels through the encrypted subscription.
        updates = asyncio.Queue()
        cancel = pairing.dispatcher_connect(updates.put_nowait)
        await pairing.subscribe([key])
        humidity.get_characteristic("CurrentRelativeHumidity").set_value(51)
        async with asyncio.timeout(5):
            while True:
                event = await updates.get()
                if event.get(key, {}).get("value") == 51:
                    break
        cancel()
        sound_key = by_kind["sound"].key
        assert (await pairing.get_characteristics([sound_key]))[sound_key]["value"] is False
        sound_updates = asyncio.Queue()
        cancel_sound = pairing.dispatcher_connect(sound_updates.put_nowait)
        await pairing.subscribe([sound_key])
        for detected in (True, False):
            sound.set_value(detected)
            async with asyncio.timeout(5):
                while True:
                    event = await sound_updates.get()
                    if event.get(sound_key, {}).get("value") is detected:
                        break
        cancel_sound()
        # Reconfiguration verifies the saved keys without a new pair-setup.
        await p.validate_connection("127.0.0.1", port, data)
        await pairing.shutdown()
        pairing = None
        # Removal clears the accessory's controller record, allowing re-pairing.
        await p.unpair_direct("127.0.0.1", port, data)
        replacement = await p.pair_direct("127.0.0.1", port, "321-54-987")
        assert replacement["iOSPairingId"] != data["iOSPairingId"]
        await p.unpair_direct("127.0.0.1", port, replacement)
    finally:
        if pairing:
            await pairing.shutdown()
        await driver.async_stop()
