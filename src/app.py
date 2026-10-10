
import threading
from datetime import datetime, timezone

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