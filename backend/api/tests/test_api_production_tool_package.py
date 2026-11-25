"""Production packaging must ship the targets of root maintenance wrappers."""
from pathlib import Path
import ast
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[3]
API=ROOT/'backend/api'

def test_production_copy_includes_tools_and_canonical_runtime_targets(tmp_path):
 docker=(API/'Dockerfile').read_text().split('FROM runtime-base AS production')[1]
 assert 'COPY --chown=$APP_UID:$APP_GID tools ./tools' in docker
 assert 'COPY --chown=$APP_UID:$APP_GID app ./app' in docker
 # Mirror the production source boundary without running service/maintenance calls.
 shutil.copytree(API/'app',tmp_path/'app')
 shutil.copytree(API/'tools',tmp_path/'tools')
 assert not list(API.glob('*.py'))
 for name in ['create_db','create_db_and_tables','fix_milvus','hash_password','init_data','nuke_milvus_v2','reset_db','seed_ultra_scale','sync_search']:
  assert (tmp_path/'tools'/(name+'.py')).is_file()
  ast.parse((tmp_path/'tools'/(name+'.py')).read_text())
 result=subprocess.run([sys.executable,'-c','from tools import seed_ultra_scale; from tools import hash_password; assert callable(hash_password.hash_my_password); import importlib.util; assert importlib.util.find_spec("app.services.orchestration.worker_entrypoint") is not None'],cwd=tmp_path,capture_output=True,text=True)
 assert result.returncode==0,result.stderr
