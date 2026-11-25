"""Source guard for application-owned raw diagnostic records.

This is a regression tripwire for known unsafe constructs, not taint analysis or
proof that every possible private value is absent from every runtime logger.
"""
import ast
from pathlib import Path

PRIVATE_FIELDS = {"error", "error_details", "query", "clean_query", "query_product",
                  "filter", "content_preview", "cart_preview", "key", "lock_key",
                  "product_name", "argument", "session_id"}
EXCEPTION_NAMES = {"e", "exc", "err", "error", "ctx_exc"}


def log_calls(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            owner=ast.unparse(node.func.value).lower()
            if ("logger" in owner or owner=="logging") and node.func.attr in {"log","debug","info","warning","error","exception","critical"}:
                yield node


def unsafe_reasons(call):
    reasons=[]
    if call.func.attr=="exception": reasons.append("traceback method")
    for keyword in call.keywords:
        if keyword.arg in {"exc_info","stack_info"} and not (isinstance(keyword.value,ast.Constant) and not keyword.value.value):
            reasons.append("traceback keyword")
        if keyword.arg=="extra" and isinstance(keyword.value,ast.Dict):
            for key in keyword.value.keys:
                if isinstance(key,ast.Constant) and key.value in PRIVATE_FIELDS: reasons.append("private extra "+key.value)
    # Exception names passed directly, stringified, or interpolated retain bodies.
    # Class-name expressions are permitted, with no exception object in record.
    for arg in call.args:
        for node in ast.walk(arg):
            if isinstance(node,ast.Name) and node.id in EXCEPTION_NAMES:
                parents={child:parent for parent in ast.walk(arg) for child in ast.iter_child_nodes(parent)}
                parent=parents.get(node)
                if not (isinstance(parent,ast.Call) and isinstance(parent.func,ast.Name) and parent.func.id=="type"):
                    reasons.append("exception value")
    return reasons


def test_application_log_calls_exclude_known_private_record_constructs():
    root=Path(__file__).parents[1]/"app"
    violations=[]
    for path in root.rglob("*.py"):
        for call in log_calls(ast.parse(path.read_text())):
            reasons=unsafe_reasons(call)
            if reasons: violations.append(f"{path.relative_to(root)}:{call.lineno}: {', '.join(reasons)}")
    assert not violations,"\n".join(violations)
