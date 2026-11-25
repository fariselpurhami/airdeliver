"""Production packaging must ship the targets of root maintenance wrappers."""
from pathlib import Path
import ast
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[3]
API=ROOT/'backend/api'

def test_production_copy_includes_tools_and_every_wrapper_target(tmp_path):
 docker=(API/'Dockerfile').read_text().split('FROM runtime-base AS production')[1]
 assert 'COPY --chown=$APP_UID:$APP_GID tools ./tools' in docker
 assert 'COPY --chown=$APP_UID:$APP_GID *.py .' in docker
 # Mirror the production source boundary without running service/maintenance calls.
 shutil.copytree(API/'app',tmp_path/'app')
 shutil.copytree(API/'tools',tmp_path/'tools')
 for source in API.glob('*.py'):shutil.copyfile(source,tmp_path/source.name)
 for name in ['create_db','create_db_and_tables','fix_milvus','hash_password','init_data','nuke_milvus_v2','reset_db','seed_ultra_scale','sync_search']:
  assert (tmp_path/'tools'/(name+'.py')).is_file()
  ast.parse((tmp_path/'tools'/(name+'.py')).read_text())
 result=subprocess.run([sys.executable,'-c','import seed_ultra_scale; from tools import seed_ultra_scale as c; assert seed_ultra_scale is c; from tools import hash_password; assert callable(hash_password.hash_my_password)'],cwd=tmp_path,capture_output=True,text=True)
 assert result.returncode==0,result.stderr
