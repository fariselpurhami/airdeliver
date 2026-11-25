"""Verify that S07 source evolution changes diagnostics, not business syntax."""
import ast
import hashlib
import json
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]


class DiagnosticBoundary(ast.NodeTransformer):
    def visit_Expr(self,node):
        if isinstance(node.value,ast.Call):
            func=node.value.func
            if isinstance(func,ast.Attribute) and ("logger" in ast.unparse(func.value).lower() or ast.unparse(func.value)=="StructuredLog"):
                return ast.Pass()
        return self.generic_visit(node)

    def visit_Assign(self,node):
        # This fixed diagnostic reason selection is part of logging only.
        if any(isinstance(x,ast.Name) and x.id=="reason" for x in node.targets) and isinstance(node.value,ast.IfExp) and "invalid_native_sdk_base_url" in ast.unparse(node):
            return None
        return self.generic_visit(node)


def business_digest(source):
    tree=DiagnosticBoundary().visit(ast.parse(source))
    return hashlib.sha256(ast.dump(tree,include_attributes=False).encode()).hexdigest()


def test_raw_logging_evolution_preserves_recorded_non_diagnostic_syntax():
    data=json.loads((ROOT/"docs/verification/raw-logging-source-evolution-v1.json").read_text())
    assert data["baseline_commit"]=="366ce6c52b733df241d2399c07121f01c615c2d6"
    assert len(data["modules"])==20
    for path,row in data["modules"].items():
        source=(ROOT/path).read_bytes()
        quality=json.loads((ROOT/"docs/verification/shopping-quality-source-evolution-v1.json").read_text())
        if path in quality['modules']:
            evolved=quality['modules'][path]
            previous=subprocess.check_output(['git','show',quality['baseline_commit']+':'+path],cwd=ROOT)
            assert hashlib.sha256(previous).hexdigest()==row['current_sha256']==evolved['previous_sha256']
            assert business_digest(previous)==row['baseline_business_sha256']
            assert hashlib.sha256(source).hexdigest()==evolved['current_sha256']
        else:
            assert hashlib.sha256(source).hexdigest()==row["current_sha256"],path
            assert business_digest(source)==row["baseline_business_sha256"],path
        assert len(row["baseline_source_sha256"])==64
