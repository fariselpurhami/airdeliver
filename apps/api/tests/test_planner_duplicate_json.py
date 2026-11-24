import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from app.services.strict_planner_json import planner_object
from app.services.target_constraint_scope import parse_scope,assign_target_scope
from app.services.discovery_planner import parse_setup,plan_setup
from app.services.constraint_continuity import replacement_is_explicit
from app.services.query_rewrite import review_query

@pytest.mark.parametrize('raw',['{"a":1,"a":2}','{"a":{"b":1,"b":2}}','{"a":NaN}','[]','null','x'*32769,'['*2000])
def test_untrusted_planner_json_is_bounded_duplicate_free_and_object_only(raw):
    with pytest.raises(ValueError):planner_object(raw)

@pytest.mark.parametrize('parser,raw',[
 (parse_scope,'{"assignments":{"laptop":["16GB RAM"],"laptop":[]}}'),
 (parse_setup,'{"components":["laptop"],"component_requirements":{"laptop":["16GB RAM"],"laptop":[]}}'),
])
def test_legacy_dynamic_map_duplicates_cannot_erase_hard_scope(parser,raw):
    with pytest.raises(ValueError):parser(raw)

@pytest.mark.asyncio
async def test_duplicate_true_after_false_cannot_authorize_scope_or_setup():
    infer=AsyncMock(side_effect=['{"assignments":{}}','{"explicit_scope":false,"explicit_scope":true}'])
    with pytest.raises(ValueError):await assign_target_scope(infer,'laptop',['laptop'],['black'])
    infer=AsyncMock(side_effect=['{"components":["laptop"]}','{"appropriate":false,"appropriate":true,"no_invented_products":true}'])
    with pytest.raises(ValueError):await plan_setup(infer,'laptop')

@pytest.mark.asyncio
async def test_duplicate_reviewer_key_does_not_clear_constraints_or_authorize_rewrite():
    infer=AsyncMock(return_value='{"explicit_replacement":false,"explicit_replacement":true}')
    assert not await replacement_is_explicit(infer,'replace RAM','replace RAM')
    infer=AsyncMock(return_value='{"preserves_request":false,"preserves_request":true,"no_invented_identity":true,"preserves_constraints":true}')
    assert await review_query(infer,'laptop','laptop',[SimpleNamespace(product_name='laptop')]) is None
