"""Test tooling must refuse non-test databases before attempting a connection."""
from pathlib import Path
import runpy
import pytest

@pytest.mark.parametrize('dsn', ['', 'postgresql+asyncpg://localhost/airdeliver', 'sqlite:///airdeliver_test_db'])
def test_verification_tool_requires_disposable_postgres_database(monkeypatch, dsn):
    monkeypatch.setenv('TEST_POSTGRES_DSN', dsn)
    module = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'scripts/verify_postgres_integration.py'))
    with pytest.raises(SystemExit):
        module['main']()
