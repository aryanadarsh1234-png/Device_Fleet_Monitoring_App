"""Mini Device Fleet Monitor."""
import threading
from datetime import datetime, timezone

from flask import Flask, jsonify, request

TIMEOUT_SECONDS = 30


def utcnow():
    return datetime.now(timezone.utc)


def fmt(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ") if dt else None


class FleetStore:
    def __init__(self, clock=utcnow, timeout=TIMEOUT_SECONDS):
        self._clock = clock
        self._timeout = timeout
        self._devices = {}
        self._lock = threading.Lock()

    def register(self, device_id, name):
        with self._lock:
            if device_id in self._devices:
                raise KeyError("exists")
            self._devices[device_id] = {
                "id": device_id, "name": name,
                "last_heartbeat": None, "device_status": None, "metrics": {},
            }

    def heartbeat(self, device_id, device_status, metrics):
        with self._lock:
            dev = self._devices.get(device_id)
            if dev is None:
                raise KeyError("missing")
            dev["last_heartbeat"] = self._clock()
            dev["device_status"] = device_status
            dev["metrics"] = metrics

    def _view(self, dev):
        last = dev["last_heartbeat"]
        online = last is not None and (self._clock() - last).total_seconds() <= self._timeout
        return {
            "id": dev["id"], "name": dev["name"],
            "status": "ONLINE" if online else "OFFLINE",
            "last_heartbeat": fmt(last),
            "device_status": dev["device_status"],
            "metrics": dev["metrics"],
        }

    def get(self, device_id):
        with self._lock:
            dev = self._devices.get(device_id)
            return self._view(dev) if dev else None


def _err(msg, code):
    return jsonify({"error": msg}), code


def create_app(store=None):
    app = Flask(__name__)
    store = store or FleetStore()

    @app.post("/devices")
    def register():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return _err("JSON body required", 400)
        device_id, name = data.get("id"), data.get("name")
        if not isinstance(device_id, str) or not device_id.strip():
            return _err("'id' must be a non-empty string", 400)
        if not isinstance(name, str) or not name.strip():
            return _err("'name' must be a non-empty string", 400)
        try:
            store.register(device_id, name)
        except KeyError:
            return _err(f"device '{device_id}' already exists", 409)
        return jsonify(store.get(device_id)), 201

    @app.post("/devices/<device_id>/heartbeat")
    def heartbeat(device_id):
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return _err("JSON body required", 400)
        status = data.get("status")
        if not isinstance(status, str) or not status.strip():
            return _err("'status' must be a non-empty string", 400)
        ts = data.get("timestamp")
        if ts is not None:
            try:
                datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            except ValueError:
                return _err("'timestamp' must be ISO-8601", 400)
        metrics = {k: v for k, v in data.items() if k not in ("status", "timestamp")}
        try:
            store.heartbeat(device_id, status, metrics)
        except KeyError:
            return _err(f"device '{device_id}' not found", 404)
        return jsonify(store.get(device_id)), 200

    @app.get("/devices/<device_id>")
    def get_device(device_id):
        dev = store.get(device_id)
        if dev is None:
            return _err(f"device '{device_id}' not found", 404)
        return jsonify(dev)

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=8000)