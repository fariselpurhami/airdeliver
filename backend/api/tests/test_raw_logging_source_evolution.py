"""Verify that S07 source evolution changes diagnostics, not business syntax."""
import ast
import hashlib
import json
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
        later=json.loads((ROOT/"docs/verification/legacy-intent-budget-source-evolution-v1.json").read_text()).get(path)
        if later:
            # Later reviewed additive block: original receipt must still match the
            # block-free source, and the block must be the only difference.
            assert later["baseline_sha256"]==row["current_sha256"],path
            assert hashlib.sha256(source).hexdigest()==later["current_sha256"],path
            source=source.decode().replace(later["inserted_block"],"").encode()
        later_gw=json.loads((ROOT/"docs/verification/worker-gateway-log-source-evolution-v1.json").read_text()).get(path)
        if later_gw:
            # Later reviewed log-level change: original receipt must still match once
            # the recorded replacements are reversed, and nothing else may differ.
            assert later_gw["baseline_sha256"]==row["current_sha256"],path
            assert hashlib.sha256(source).hexdigest()==later_gw["current_sha256"],path
            text=source.decode()
            for edit in later_gw["replacements"]:
                assert text.count(edit["new"])==1,path
                text=text.replace(edit["new"],edit["old"])
            source=text.encode()
        later_wr=json.loads((ROOT/"docs/verification/withheld-reason-source-evolution-v1.json").read_text()).get(path)
        if later_wr:
            # Later reviewed diagnostic-only change (fixed reason code in a log line
            # plus its helper import): reversing it must restore the previous receipt.
            assert later_wr["baseline_sha256"]==row["current_sha256"],path
            assert hashlib.sha256(source).hexdigest()==later_wr["current_sha256"],path
            text=source.decode()
            for edit in later_wr["replacements"]:
                assert text.count(edit["new"])==edit["count"],path
                text=text.replace(edit["new"],edit["old"])
            source=text.encode()
        assert hashlib.sha256(source).hexdigest()==row["current_sha256"],path
        assert business_digest(source)==row["baseline_business_sha256"],path
        assert len(row["baseline_source_sha256"])==64
