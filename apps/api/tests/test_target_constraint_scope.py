import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from app.services.target_constraint_scope import assign_target_scope
from app.services.neural_core_service import NeuralCoreService,SessionMemory,RouterDecision,SearchTarget
from app.services.shopping_discovery import ShoppingBrief

@pytest.mark.asyncio
@pytest.mark.parametrize('bad',['target','feature','review'])
async def test_scope_assignment_is_exact_and_independently_reviewed(bad):
    values={'assignments':{'other' if bad=='target' else 'laptop':['invented' if bad=='feature' else '16GB RAM']}}
    infer=AsyncMock(side_effect=[json.dumps(values),json.dumps({'explicit_scope':bad!='review'})])
    with pytest.raises(ValueError):await assign_target_scope(infer,'laptop16GB RAM and chair',['laptop','chair'],['16GB RAM'])

@pytest.mark.asyncio
async def test_scoped_target_state_preserves_omission_and_shared_constraints():
    memory=SessionMemory(user_name='Fixture',target_requirements={'laptop':['16GB RAM']})
    svc=NeuralCoreService(object(),object());svc._execute_llm_inference=AsyncMock(side_effect=['{"assignments":{}}','{"explicit_scope":true}'])
    svc._handle_staged_product_search=AsyncMock(return_value=SimpleNamespace(response_kind='text'))
    decision=RouterDecision(intent='PRODUCT_SEARCH',targets=[SearchTarget(product_name='laptop'),SearchTarget(product_name='chair')])
    await svc._handle_scoped_target_search(None,decision,ShoppingBrief(required_features=['16GB RAM','black']),'more laptop and chair',memory)
    _,scoped,brief,_=svc._handle_staged_product_search.await_args.args
    assert scoped.targets[0].required_features==['16GB RAM'] and scoped.targets[1].required_features==[]
    assert brief.required_features==['black'] and memory.target_requirements=={'laptop':['16GB RAM']}
