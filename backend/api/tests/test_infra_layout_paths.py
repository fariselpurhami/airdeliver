"""Path move must preserve exact file bytes and container mount targets."""
from pathlib import Path
import hashlib
import json
ROOT=Path(__file__).resolve().parents[3]

def test_moved_configuration_bytes_match_approved_baseline():
    manifest=json.loads((ROOT/'docs/verification/infra-layout-stage-v1.json').read_text())
    for row in manifest:
        assert hashlib.sha256((ROOT/row['to']).read_bytes()).hexdigest()==row['sha256']
        assert not (ROOT/row['from']).exists()

def test_compose_keeps_targets_readonly_and_new_source_paths_exist():
    base=(ROOT/'docker-compose.yml').read_text();dev=(ROOT/'docker-compose.dev.yml').read_text()
    sql='./infra/database/init/01-enable-vector.sql:/docker-entrypoint-initdb.d/01-enable-vector.sql:ro'
    assert sql in base and sql in dev
    assert './infra/observability/promtail/promtail.yaml:/etc/promtail/config.yml:ro' in base
    assert './infra/observability/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro' in base
    assert './monitoring/' not in base and './db_init/' not in base+dev
