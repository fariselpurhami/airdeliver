import json
import os
import pytest
from app.core import dev_lifecycle as module


def test_process_identity_matches_current_linux_process():
    assert int(module.process_start(os.getpid())) > 0


def test_dev_markers_follow_state_and_ignore_stale_pid(tmp_path, monkeypatch):
    monkeypatch.setenv('APP_ENV', 'development')
    monkeypatch.setattr(module, 'DIRECTORY', tmp_path)
    assert module.read_state() == 'unavailable'
    module.write_state('starting')
    assert module.read_state() == 'starting'
    module.write_state('ready')
    assert module.read_state() == 'ready'
    record = tmp_path / f'{os.getpid()}.json'
    row = json.loads(record.read_text()); row['start'] = '999999999999999999'
    record.write_text(json.dumps(row))
    assert module.read_state() == 'unavailable'


def test_production_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.setenv('APP_ENV', 'production')
    monkeypatch.setattr(module, 'DIRECTORY', tmp_path)
    module.write_state('starting')
    assert list(tmp_path.iterdir()) == []
    assert module.read_state() == 'unavailable'


def test_corrupt_marker_and_diagnostic_write_failure_are_nonfatal(tmp_path, monkeypatch):
    monkeypatch.setenv('APP_ENV', 'development')
    monkeypatch.setattr(module, 'DIRECTORY', tmp_path)
    (tmp_path / 'bad.json').write_text('{')
    assert module.read_state() == 'unavailable'
    monkeypatch.setattr(module, 'DIRECTORY', tmp_path / 'bad.json')
    module.write_state('starting')
