"""Recommendation task-fit is independently reviewed, not inferred from valid IDs."""
import json
from copy import deepcopy
from unittest.mock import AsyncMock
import pytest
from tests.test_llm_execution_limits import service,completion
from tests.test_reviewed_recommendation import P,D,V

QUALITY={"answers_actual_decision":True,"respects_requested_selection":True,"handles_decisive_unknowns":True,"useful_next_step":True}

@pytest.mark.asyncio
async def test_writer_and_reviewer_receive_decision_contract_before_publishing():
    llm=service();calls=[]
    async def respond(**kwargs):
        calls.append(kwargs)
        schema=kwargs['response_format']['json_schema']['name']
        return completion(json.dumps({**V,**QUALITY} if schema=='RecommendationReview' else D))
    llm._chat_completion=AsyncMock(side_effect=respond)
    result=await llm.filter_and_recommend('Choose one shirt based on the listed material; ask only if fit prevents a responsible choice',[deepcopy(P)])
    assert result.selected_ids==[7]
    assert len(calls)==2
    writer=' '.join(m['content'] for m in calls[0]['messages'])
    reviewer=' '.join(m['content'] for m in calls[1]['messages'])
    assert 'DECISION VALUE' in writer
    assert 'do not turn every answer into a question' in writer
    assert calls[1]['response_format']['json_schema']['name']=='RecommendationReview'
    assert 'requested selection' in reviewer

@pytest.mark.asyncio
@pytest.mark.parametrize('field',list(QUALITY))
async def test_quality_rejection_withholds_without_fallback_cards(field):
    llm=service()
    async def respond(**kwargs):
        schema=kwargs['response_format']['json_schema']['name']
        return completion(json.dumps({**V,**QUALITY,field:False} if schema in {'RecommendationReview','GroundingReview'} else D))
    llm._chat_completion=AsyncMock(side_effect=respond)
    result=await llm.filter_and_recommend('Choose only one shirt',[deepcopy(P)])
    assert result.selected_ids==[]
    assert result.reasoning=={}
    assert result.intro_message.startswith('System notice:')
