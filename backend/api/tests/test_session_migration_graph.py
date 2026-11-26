"""Static AST migration graph only, never imports Alembic or executes DDL."""
import ast
from pathlib import Path

def test_prepared_session_migration_extends_current_single_head():
 directory=Path(__file__).resolve().parents[1]/'alembic/versions'
 revisions={}
 for path in directory.glob('*.py'):
  values={}
  for node in ast.parse(path.read_text()).body:
   if isinstance(node,ast.Assign):
    for target in node.targets:
     if isinstance(target,ast.Name) and target.id in {'revision','down_revision'}:
      values[target.id]=ast.literal_eval(node.value)
  if 'revision' in values:
   assert values['revision'] not in revisions
   revisions[values['revision']]=values.get('down_revision')
 parents=set()
 for revision,parent in revisions.items():
  if parent is not None:
   assert isinstance(parent,str) and parent in revisions
   parents.add(parent)
 assert set(revisions)-parents=={'a07cd546f987'}
 assert revisions['a07cd546f987']=='1b8de657a098'
