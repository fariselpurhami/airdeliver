"""Actual bus input parser never rounds/coerces another customer's identity."""
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from app.services.ai_nlu_service import AINLUService

@pytest.mark.parametrize('uid',[True,False,7.0,7.9,0,-1,2147483648,None,'0','-1','+7',' 7','7 ','07','7.0','7e0','٧',[],{}])
def test_actual_parser_rejects_noncanonical_owner_id_before_any_work(uid):
    svc=AINLUService(SimpleNamespace(),SimpleNamespace(),SimpleNamespace(),SimpleNamespace(),SimpleNamespace())
    with pytest.raises(ValueError):svc._parse_incoming_message({'user_id':uid,'message':'chair'})

@pytest.mark.parametrize('uid,expected',[(7,7),('7',7),(2147483647,2147483647),('2147483647',2147483647)])
def test_canonical_bus_integer_and_decimal_string_compatibility(uid,expected):
    svc=AINLUService(SimpleNamespace(),SimpleNamespace(),SimpleNamespace(),SimpleNamespace(),SimpleNamespace())
    assert svc._parse_incoming_message({'user_id':uid,'message':'chair'}).user_id==expected

@pytest.mark.asyncio
async def test_actual_process_invalid_owner_never_reads_history_or_sends_ui():
    svc=AINLUService(SimpleNamespace(),SimpleNamespace(),SimpleNamespace(),SimpleNamespace(),SimpleNamespace())
    svc._append_to_memory=AsyncMock();svc._send_to_ui=AsyncMock();svc.intent_engine.analyze_intent=AsyncMock()
    with pytest.raises(ValueError):await svc.process_message({'user_id':True,'message':'chair'})
    svc._append_to_memory.assert_not_awaited();svc._send_to_ui.assert_not_awaited();svc.intent_engine.analyze_intent.assert_not_awaited()
