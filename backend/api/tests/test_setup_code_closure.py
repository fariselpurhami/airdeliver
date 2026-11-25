"""Finite setup plan and actual component-selection boundary."""
import asyncio,json
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from app.services.discovery_planner import parse_setup,select_setup_candidates,plan_setup
from app.services.shopping_discovery import ShoppingBrief

@pytest.mark.parametrize('components',[['desk','DESK'],['desk chair','desk  chair'],['desk','desk']])
def test_duplicate_component_identity_is_rejected_before_search(components):
    with pytest.raises(ValueError):parse_setup({'components':components})

def row(pid,price,currency='USD'):return SimpleNamespace(id=pid,price=price,currency=currency)

def test_one_suggestion_per_component_preserves_aggregate_cap_and_reports_gap():
    selected,coverage=select_setup_candidates([[row(1,70),row(2,20)],[row(3,40),row(4,25)],[row(5,10)]],['desk','chair','lamp'],ShoppingBrief(budget='USD 100',budget_max='100',budget_currency='USD'))
    assert [r.id for r in selected]==[1,4]
    assert [r['selected_ids'] for r in coverage]==[[1],[4],[]]
    assert coverage[-1]['status']=='no_candidate_selected_under_constraints'

def test_shared_row_cannot_impersonate_two_component_suggestions():
    selected,coverage=select_setup_candidates([[row(1,10)],[row(1,10)]],['desk','chair'],ShoppingBrief())
    assert [r.id for r in selected]==[1] and coverage[1]['selected_ids']==[]

def test_wrong_currency_is_not_converted_for_setup_budget():
    selected,coverage=select_setup_candidates([[row(1,10,'EUR'),row(2,20)]],['desk'],ShoppingBrief(budget='USD 100',budget_max='100',budget_currency='USD'))
    assert [r.id for r in selected]==[2]

@pytest.mark.asyncio
async def test_setup_planner_deadline_and_cancellation_propagate():
    async def slow(*a,**k):await asyncio.sleep(1)
    with pytest.raises(TimeoutError):await plan_setup(slow,'desk setup',timeout=.001)
    with pytest.raises(asyncio.CancelledError):await plan_setup(AsyncMock(side_effect=asyncio.CancelledError()),'desk setup')
