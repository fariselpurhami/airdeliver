"""Voice repair: when a validated draft carries robotic tells, one extra low-effort call rewrites only the text.

User voice note (8:37 PM): the reply should read like a tactful, sharp friend, not an AI. Real draft (n=1, bait-02): "the catalog
does not list its battery life ... I can't confirm". The rewrite keeps the draft's own ids and claims, is re-validated and reviewed,
and the original draft is the fallback. Scripted model, no provider call.
"""
import asyncio,json
import pytest
from decimal import Decimal
from tests.test_shopping_discovery_contract import row
from app.services.shopping_discovery import catalog_result
from app.services.shopping_copy import write_shopping_copy, voice_tells

OK={'supported':True,'all_product_mentions_declared':True,'no_unsupported_commercial_claims':True,'fulfills_discovery_task':True}
ROBOTIC="Studio Headphones are in stock locally, but the catalog does not list battery life. I can't confirm sleep tracking either."
FRIEND="Studio Headphones are in stock locally. I don't have the battery life for this pair, so I won't guess."

def draft(text):
    return {'text':text,'product_ids':[1],'claims':[{'product_id':1,'field':'name','value':'Studio Headphones'},{'product_id':1,'field':'stock_status','value':'local_in_stock'}]}

def run(replies,ctx=None):
    seen=[]
    async def infer(messages):
        seen.append(messages);return json.dumps(replies[len(seen)-1])
    card=catalog_result(row())
    text=asyncio.run(write_shopping_copy(infer,'battery life?',[card],{},'catalog_results',20,ctx))
    return text,seen

def test_tells_are_detected():
    assert voice_tells(ROBOTIC)
    assert voice_tells('- Battery: not specified\n- Weight: 1 kg')
    assert voice_tells('Not mentioned in the specifications.')
    assert not voice_tells(FRIEND)

def test_rewrite_replaces_text_keeps_claims_and_is_reviewed():
    text,seen=run([draft(ROBOTIC),draft(FRIEND),OK])
    assert text==FRIEND and len(seen)==3
    assert 'rewrite' in seen[1][0]['content'].casefold()
    assert 'Independently review' in seen[2][0]['content']
    reviewed=json.loads(seen[2][1]['content'])['draft']
    assert reviewed['text']==FRIEND and reviewed['claims'][1]['field']=='stock_status'

def test_no_tells_means_no_extra_call():
    text,seen=run([draft(FRIEND),OK])
    assert text==FRIEND and len(seen)==2

def test_rewrite_that_invalidates_falls_back_to_original():
    bad="Studio Headphones are the best choice, in stock locally."
    text,seen=run([draft(ROBOTIC),draft(bad),OK])
    assert text==ROBOTIC and len(seen)==3

def test_rewrite_that_drops_the_product_name_or_a_number_falls_back():
    text,_=run([draft(ROBOTIC),draft("It is in stock locally. I don't have the battery life."),OK])
    assert text==ROBOTIC

def test_rewrite_that_still_has_as_many_tells_falls_back():
    text,_=run([draft(ROBOTIC),draft("Studio Headphones are in stock locally, but the catalog does not list battery life. I can't confirm it."),OK])
    assert text==ROBOTIC

def test_provider_failure_in_rewrite_falls_back_without_withholding():
    calls=[]
    async def infer(messages):
        calls.append(1)
        if len(calls)==2:raise RuntimeError('provider down')
        return json.dumps(draft(ROBOTIC) if len(calls)==1 else OK)
    text=asyncio.run(write_shopping_copy(infer,'battery life?',[catalog_result(row())],{},'catalog_results',20))
    assert text==ROBOTIC and len(calls)==3

@pytest.mark.parametrize('ctx',[{'sales_intent':'OPENING_INSIGHT'},{'product_answer_shape':'four_phase'}])
def test_opening_copy_and_four_phase_are_never_rewritten(ctx):
    text,seen=run([draft(ROBOTIC),OK],ctx)
    assert text==ROBOTIC and len(seen)==2

def test_answers_that_declare_no_product_are_never_rewritten():
    seen=[]
    async def infer(messages):
        seen.append(1);return json.dumps({'text':'Explore these catalog designs.','product_ids':[],'claims':[]} if len(seen)==1 else OK)
    text=asyncio.run(write_shopping_copy(infer,'ideas?',[catalog_result(row())],{},'catalog_results',20))
    assert text=='Explore these catalog designs.' and len(seen)==2
