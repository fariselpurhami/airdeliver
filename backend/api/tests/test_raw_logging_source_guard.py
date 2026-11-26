"""Source guard for application-owned raw diagnostic records.

This is a regression tripwire for known unsafe constructs, not taint analysis or
proof that every possible private value is absent from every runtime logger.
"""
import ast
from pathlib import Path

PRIVATE_FIELDS = {"error", "error_details", "query", "clean_query", "query_product",
                  "filter", "content_preview", "cart_preview", "key", "lock_key",
                  "product_name", "argument", "session_id", "admin_email", "original_query", "core_query", "broad_query", "command_text", "category_filter"}
EXCEPTION_NAMES = {"e", "exc", "err", "error", "ctx_exc", "ve", "close_exc"}


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
    safe_calls = {"type", "quota_metadata", "provider_error_shape", "failed_json_diagnostics", "withheld_reason"}  # returns fixed codes only; see test_withheld_reason_code
    for arg in call.args:
        for node in ast.walk(arg):
            if isinstance(node,ast.Name) and node.id in EXCEPTION_NAMES:
                parents={child:parent for parent in ast.walk(arg) for child in ast.iter_child_nodes(parent)}
                parent=parents.get(node)
                safe=False
                while parent is not None:
                    if isinstance(parent,ast.Call) and isinstance(parent.func,ast.Name) and parent.func.id in safe_calls:
                        safe=True;break
                    if isinstance(parent,ast.Attribute) and parent.attr=="code":
                        safe=True;break
                    # Existing numeric status/code access, not the error object.
                    if isinstance(parent,ast.Call) and isinstance(parent.func,ast.Name) and parent.func.id=="getattr" and len(parent.args)>1 and isinstance(parent.args[1],ast.Constant) and parent.args[1].value in {"code","status_code"}:
                        safe=True;break
                    parent=parents.get(parent)
                if not safe: reasons.append("exception value")
    return reasons


def test_application_log_calls_exclude_known_private_record_constructs():
    root=Path(__file__).parents[1]/"app"
    violations=[]
    for path in root.rglob("*.py"):
        for call in log_calls(ast.parse(path.read_text())):
            reasons=unsafe_reasons(call)
            if reasons: violations.append(f"{path.relative_to(root)}:{call.lineno}: {', '.join(reasons)}")
    assert not violations,"\n".join(violations)
