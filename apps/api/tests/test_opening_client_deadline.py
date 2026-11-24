"""Cross-surface opening deadline contract, no services or provider calls."""
from pathlib import Path
import re
from app.services.ai_nlu_service import MatrixConfig


def test_opening_http_budget_outlasts_backend_matrix_without_changing_cart_budget():
    root=Path(__file__).resolve().parents[3]
    source=(root/'apps/web/hooks/useAIOrderingStore.ts').read_text()
    match=re.search(r"path === '/session/suggestions' \? (\d+) : (\d+)",source)
    assert match, 'Opening needs an explicit separate bounded HTTP deadline'
    opening,cart=map(int,match.groups())
    assert MatrixConfig().matrix_timeout_sec*1000 < opening <= 120000
    assert cart==30000
