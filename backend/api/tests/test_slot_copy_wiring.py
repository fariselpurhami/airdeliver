"""Slot copy wiring: default OFF, one extra attempt when ON, any failure falls back to the normal writer. Scripted, simulated (not Groq)."""
import asyncio,json
from decimal import Decimal
from tests.test_shopping_discovery_contract import row
from app.services.shopping_discovery import catalog_result
from app.services.shopping_copy import write_shopping_copy

OK={'supported':True,'all_product_mentions_declared':True,'no_unsupported_commercial_claims':True,'fulfills_discovery_task':True}
NORMAL={'text':'Studio Headphones cost 19.99 USD.','product_ids':[1],'claims':[{'product_id':1,'field':'name','value':'Studio Headphones'},{'product_id':1,'field':'price','value':'19.99'}]}
SLOT={'text':'The [[name:1]] is [[price:1]], and I do not have its battery life.\n\nIs battery life what decides it for you?'}

def go(replies,monkeypatch,flag):
    if flag:monkeypatch.setenv('AIRDELIVER_SLOT_COPY','1')
    else:monkeypatch.delenv('AIRDELIVER_SLOT_COPY',raising=False)
    seen=[]
    async def infer(messages):
        seen.append(messages);return json.dumps(replies[len(seen)-1])
    text=asyncio.run(write_shopping_copy(infer,'battery life?',[catalog_result(row())],{},'catalog_results',20,{'sales_intent':'CATALOG_CONSULTATION'}))
    return text,seen

def test_flag_off_is_the_unchanged_path(monkeypatch):
    text,seen=go([NORMAL,OK],monkeypatch,False)
    assert text==NORMAL['text'] and len(seen)==2 and 'slot' not in seen[0][0]['content'].casefold()

def test_flag_on_uses_the_rendered_slot_draft_and_the_normal_review(monkeypatch):
    text,seen=go([SLOT,OK],monkeypatch,True)
    assert text=='The Studio Headphones is $19.99, and I do not have its battery life.\n\nIs battery life what decides it for you?'
    assert len(seen)==2 and 'Never type a number' in seen[0][0]['content'] and 'Independently review' in seen[1][0]['content']

def test_flag_on_bad_slot_draft_falls_back_to_the_normal_writer(monkeypatch):
    text,seen=go([{'text':'The Studio Headphones (ID 1) cost 19 dollars.'},NORMAL,OK],monkeypatch,True)
    assert text==NORMAL['text'] and len(seen)==3

def test_flag_on_provider_failure_in_slot_call_falls_back(monkeypatch):
    monkeypatch.setenv('AIRDELIVER_SLOT_COPY','1')
    calls=[]
    async def infer(messages):
        calls.append(1)
        if len(calls)==1:raise RuntimeError('provider down')
        return json.dumps(NORMAL if len(calls)==2 else OK)
    text=asyncio.run(write_shopping_copy(infer,'battery life?',[catalog_result(row())],{},'catalog_results',20,{'sales_intent':'CATALOG_CONSULTATION'}))
    assert text==NORMAL['text'] and len(calls)==3

def test_opening_insight_never_uses_slots(monkeypatch):
    monkeypatch.setenv('AIRDELIVER_SLOT_COPY','1')
    calls=[]
    async def infer(messages):
        calls.append(messages);return json.dumps([NORMAL,OK][len(calls)-1])
    asyncio.run(write_shopping_copy(infer,'hi',[catalog_result(row())],{},'catalog_results',20,{'sales_intent':'OPENING_INSIGHT'}))
    assert len(calls)==2 and 'Never type a number' not in calls[0][0]['content']
