"""Best-effort process-bound development startup diagnostics, no customer data."""
import json
import os
from pathlib import Path

DIRECTORY = Path('/tmp/airdeliver-api-lifecycle')


def process_start(pid):
    # Linux /proc starttime distinguishes PID reuse. comm can contain spaces.
    return Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[19]


def write_state(state):
    if os.environ.get('APP_ENV') != 'development':
        return
    if state not in {'starting', 'ready', 'stopping', 'failed'}:
        return
    try:
        pid = os.getpid()
        DIRECTORY.mkdir(mode=0o700, parents=True, exist_ok=True)
        record = {'pid': pid, 'start': process_start(pid), 'state': state}
        target = DIRECTORY / f'{pid}.json'
        temporary = DIRECTORY / f'{pid}.tmp'
        temporary.write_text(json.dumps(record))
        temporary.replace(target)
    except (OSError, ValueError, IndexError):
        pass  # Diagnostics must never prevent app startup/shutdown.


def read_state():
    if os.environ.get('APP_ENV') != 'development':
        return 'unavailable'
    records = []
    try:
        for path in DIRECTORY.glob('*.json'):
            try:
                row = json.loads(path.read_text())
                pid = row['pid']
                if (type(pid) is int and pid > 0 and isinstance(row['start'], str)
                        and row['start'].isdigit() and process_start(pid) == row['start']
                        and row['state'] in {'starting', 'ready', 'stopping', 'failed'}):
                    records.append(row)
            except (OSError, ValueError, KeyError, TypeError, IndexError):
                continue
    except OSError:
        return 'unavailable'
    if not records:
        return 'unavailable'
    return max(records, key=lambda row: int(row['start']))['state']
