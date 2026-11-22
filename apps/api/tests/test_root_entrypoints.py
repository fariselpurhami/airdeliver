from pathlib import Path
import subprocess
import pytest

ROOT=Path(__file__).resolve().parents[3]


@pytest.mark.parametrize('target',['up','down','restart','logs'])
def test_make_shortcuts_dry_run_use_combined_dev_stack(target):
    result=subprocess.run(['make','--dry-run',target],cwd=ROOT,text=True,capture_output=True,check=True)
    assert 'docker compose -f docker-compose.yml -f docker-compose.dev.yml -p airdeliver_dev' in result.stdout
    assert '--volumes' not in result.stdout


def test_auto_watch_uses_combined_stack_and_actual_lockfile():
    text=(ROOT/'dev-auto-watch.sh').read_text()
    assert '"./pnpm-lock.yaml"' in text
    assert 'docker compose -f docker-compose.dev.yml' not in text
    subprocess.run(['bash','-n',str(ROOT/'dev-auto-watch.sh')],check=True)
