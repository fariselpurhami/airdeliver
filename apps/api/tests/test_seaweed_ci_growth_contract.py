"""Keep disposable Seaweed allocation compatible with bounded CI slots."""
from pathlib import Path
import tomllib

def test_ci_growth_fits_two_slot_fixture_without_raising_capacity():
    root=Path(__file__).resolve().parents[3]
    config=tomllib.loads((root/'infra/storage-ci/seaweed-master.toml').read_text())
    assert config['master']['volume_growth']=={'copy_1':1,'copy_2':1,'copy_3':1,'copy_other':1}
    compose=(root/'docker-compose.storage-seaweed-ci.yml').read_text()
    assert "'-volume.max=2'" in compose
    assert "'-master.volumeSizeLimitMB=100'" in compose
    assert './infra/storage-ci/seaweed-master.toml:/etc/seaweedfs/master.toml:ro' in compose
