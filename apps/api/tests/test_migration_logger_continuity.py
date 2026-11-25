"""Migration setup must not disable existing service diagnostics."""
import ast
from pathlib import Path

def test_alembic_file_config_explicitly_preserves_existing_loggers():
 tree=ast.parse(Path('alembic/env.py').read_text())
 calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='fileConfig']
 assert len(calls)==1
 assert any(k.arg=='disable_existing_loggers' and isinstance(k.value,ast.Constant) and k.value.value is False for k in calls[0].keywords)
