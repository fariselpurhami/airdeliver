"""The dev web container's .next directory lives on a named Docker volume."""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[3]
DEV=(ROOT/'docker-compose.dev.yml').read_text()

def web_block():
    start=DEV.index('\n  web:\n');end=DEV.index('\n  ',start+8)
    m=re.search(r'\n  [a-z0-9_-]+:\n',DEV[start+8:]);return DEV[start:start+8+(m.start() if m else len(DEV))]

def test_next_dir_is_a_named_volume_not_anonymous():
    block=web_block()
    assert 'web-next-cache:/workspace/frontend/web/.next' in block
    assert not re.search(r'^\s+- /workspace/frontend/web/\.next\s*$',block,re.M)

def test_named_volume_is_declared_and_existing_mounts_remain():
    assert re.search(r'^volumes:\n(?:.*\n)*?  web-next-cache:',DEV,re.M)
    block=web_block()
    assert './frontend/web:/workspace/frontend/web:delegated' in block
    assert re.search(r'^\s+- /workspace/frontend/web/node_modules\s*$',block,re.M)
