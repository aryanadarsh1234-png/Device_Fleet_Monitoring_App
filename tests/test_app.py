import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from app import FleetStore, create_app  # noqa: E402


class FakeClock:
    """A controllable clock so tests can move time without sleeping."""

    def __init__(self):
        self.now = datetime(2026, 9, 21, 10, 30, 0, tzinfo=timezone.utc)

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += timedelta(seconds=seconds)


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def client(clock):
    app = create_app(FleetStore(clock=clock))
    return app.test_client()


def register(client, did="device-01", name="Lab Device 01"):
    return client.post("/devices", json={"id": did, "name": name})


def beat(client, did="device-01", **extra):
    return client.post(f"/devices/{did}/heartbeat", json={"status": "OK", **extra})


# --- registration ---
def test_register_device(client):
    r = register(client)
    assert r.status_code == 201
    assert r.get_json()["id"] == "device-01"
    assert r.get_json()["status"] == "OFFLINE"  # no heartbeat yet


def test_register_duplicate_returns_409(client):
    register(client)
    assert register(client).status_code == 409


@pytest.mark.parametrize("body", [{}, {"id": "x"}, {"name": "x"}, {"id": "", "name": "x"}, {"id": 1, "name": "x"}])
def test_register_validation(client, body):
    assert client.post("/devices", json=body).status_code == 400


def test_register_non_json(client):
    assert client.post("/devices", data="nope").status_code == 400


# --- heartbeat ---
def test_heartbeat_makes_device_online(client):
    register(client)
    r = beat(client, cpu_usage=42)
    assert r.status_code == 200
    body = r.get_json()
    assert body["status"] == "ONLINE"
    assert body["last_heartbeat"] == "2026-09-21T10:30:00Z"
    assert body["metrics"] == {"cpu_usage": 42}


def test_heartbeat_unknown_device(client):
    assert beat(client, "ghost").status_code == 404


def test_heartbeat_validation(client):
    register(client)
    assert client.post("/devices/device-01/heartbeat", json={}).status_code == 400
    assert client.post("/devices/device-01/heartbeat", json={"status": "OK", "timestamp": "bad"}).status_code == 400


def test_latest_heartbeat_wins(client, clock):
    register(client)
    beat(client)
    clock.advance(10)
    beat(client)
    assert client.get("/devices/device-01").get_json()["last_heartbeat"] == "2026-09-21T10:30:10Z"