"""C01 migration guard tests invoke no Alembic/DDL or database connection."""
import importlib.util
from pathlib import Path
from unittest.mock import Mock
import pytest
P=Path(__file__).resolve().parents[1]/'alembic/versions/a07cd546f987_prepare_auth_sessions.py'

def module():
 spec=importlib.util.spec_from_file_location('prepared_session_migration',P)
 value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value

@pytest.mark.parametrize('env,url',[
 ({},'postgresql://postgres:postgres@localhost/airdeliver_test_ci'),
 ({'GITHUB_ACTIONS':'true'},'postgresql://postgres:postgres@localhost/airdeliver_test_ci'),
 ({'GITHUB_ACTIONS':'true','RUNNER_ENVIRONMENT':'self-hosted'},'postgresql://postgres:postgres@localhost/airdeliver_test_ci'),
 ({'GITHUB_ACTIONS':'true','RUNNER_ENVIRONMENT':'github-hosted'},'postgresql://postgres:postgres@db.example/airdeliver_test_ci'),
 ({'GITHUB_ACTIONS':'true','RUNNER_ENVIRONMENT':'github-hosted'},'postgresql://postgres:postgres@localhost/production'),
])
def test_upgrade_refuses_outside_exact_disposable_scope_before_ddl(monkeypatch,env,url):
 from sqlalchemy.engine import make_url
 m=module()
 for k in ['GITHUB_ACTIONS','RUNNER_ENVIRONMENT']:monkeypatch.delenv(k,raising=False)
 for k,v in env.items():monkeypatch.setenv(k,v)
 op=Mock();op.get_bind.return_value.engine.url=make_url(url);monkeypatch.setattr(m,'op',op)
 with pytest.raises(RuntimeError,match='authorized_disposable_ci_required'):m.upgrade()
 op.create_table.assert_not_called();op.create_index.assert_not_called()


def test_exact_hosted_scope_reaches_only_additive_expected_ddl(monkeypatch):
 from sqlalchemy.engine import make_url
 m=module();monkeypatch.setenv('GITHUB_ACTIONS','true');monkeypatch.setenv('RUNNER_ENVIRONMENT','github-hosted')
 op=Mock();op.get_bind.return_value.engine.url=make_url('postgresql://postgres:postgres@localhost/airdeliver_test_ci');monkeypatch.setattr(m,'op',op)
 m.upgrade()
 assert [c.args[0] for c in op.create_table.call_args_list]==['auth_sessions','refresh_credentials']
 assert op.create_index.call_count==2 and not op.drop_table.called
