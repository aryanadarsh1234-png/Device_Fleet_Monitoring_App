# Mini Device Fleet Monitor

A small Flask service that tracks heartbeats from simulated devices and reports
each device as ONLINE for heartbeat within the last 30 seconds otherwise OFFLINE.

Each device periodically sends a heartbeat to the application. 
The application should track the latest heartbeat for every device and allow an operator to view the current status of the fleet.

## Design / Folder Structure

```
src/app.py              Flask API + FleetStore (in-memory, thread-safe)
simulator/simulate.py   Sends heartbeats for N simulated devices
tests/test_app.py       pytest suite
```

- **Status is computed on read** from `last_heartbeat` and the current time.
  There is no background thread, so status is always correct and nothing has
  to be kept in sync.
- `FleetStore` takes an injectable clock, so the 30s rule is tested
  deterministically with a fake clock instead of `sleep`.
- A `threading.Lock` guards the store, since Flask may handle requests on
  several threads.
- `last_heartbeat` is the **server receive time**, not the timestamp the device
  sends, so a device with a wrong clock cannot appear falsely online or offline.

## Prerequisites/ Technologies Used

Python
Flask Framework
pytest Test Framework
In-memory storage(Python Dictionary)

## Build / install

```bash
git clone <YOUR-REPO-URL>
cd Device_Fleet_Monitoring_App
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run the application

In First terminal
```bash
python src/app.py        # listens on http://localhost:8000
```

## Run the simulator

In a second terminal (with the venv active):

```bash
python simulator/simulate.py                                   # 5 devices, heartbeat every 5s
python simulator/simulate.py --stop device-03 --stop-after 20  # stop device-03 after 20s
```

About 30 seconds after `device-03` stops, it becomes OFFLINE. Watch for it with:

```bash
while true; do curl -s localhost:8000/summary; echo; sleep 2; done
```

## Run the tests

```bash
python -m pytest -v
```

## Example API requests

```bash
command to register a device:
curl -X POST localhost:8000/devices -H 'Content-Type: application/json' -d '{"id":"device-01","name":"Lab Device 01"}'

command to make a device ONLINE:
curl -X POST localhost:8000/devices/phone-01/heartbeat -H 'Content-Type: application/json' -d '{"status":"OK"}'

curl localhost:8000/devices
curl "localhost:8000/devices?status=online"
curl localhost:8000/devices/device-01
curl localhost:8000/summary
```

Errors return JSON like `{"error": "..."}` with status 400 (bad input), 404
(unknown device) or 409 (duplicate id).

## Assumptions

- A device that is registered but has never sent a heartbeat is OFFLINE.
- Exactly 30 seconds since the last heartbeat is still ONLINE; more than 30 is OFFLINE.
- Extra heartbeat fields (such as `cpu_usage`) are stored as `metrics`.
- The heartbeat `timestamp` is validated if present but not used to decide status.

## Known limitations

- Data is in memory and is lost when the server restarts.
- Uses Flask's development server, which is not meant for production.
- No authentication; any client can send a heartbeat for any device.
- Only the latest heartbeat is kept, with no history.
- The simulator does not re-register devices if the server restarts.

## With one more day I would

- Add SQLite or Postgres persistence and a heartbeat history.
- Add per-device auth tokens and rate limiting.
- Run under gunicorn, add Docker and configuration through environment variables.
- Make the simulator re-register devices after a server restart.

## AI Usage

- **Tools:** Claude, used to help scaffold the Flask app, simulator and tests, and to
  explain the design decisions.
- **Changed or rejected:** <<< WRITE THIS YOURSELF: one real thing you changed,
  rejected or improved from the generated code, and why >>>
- **Verified:** I ran the 19 tests and all passed. I ran the server with the
  simulator and confirmed that 5 devices were ONLINE, and that after stopping
  `device-03` the summary changed to 4 online and 1 offline after about 30 seconds.
  <<< add anything else you personally checked >>>