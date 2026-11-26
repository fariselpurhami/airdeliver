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
    assert voice_tells('- Battery: not specified in the data\n- Weight: 1 kg')
    assert not voice_tells('- Battery: 12 hours\n- Weight: 1 kg')
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

def test_opening_copy_is_never_rewritten():
    text,seen=run([draft(ROBOTIC),OK],{'sales_intent':'OPENING_INSIGHT'})
    assert text==ROBOTIC and len(seen)==2

FOUR_ROBOTIC=("Studio Headphones are in stock locally, but the catalog does not list battery life.\n\n- Battery: not specified in the data.\n- Stock: local.\n\n"
    "Since I can't confirm battery life, I can't say it fits an all-day need.\n\nWant me to look at other headphones?")
FOUR_FRIEND=("Studio Headphones are in stock locally, but I don't have their battery life.\n\nThat is the one gap: stock is local and nothing else is missing.\n\n"
    "So I can't say if it lasts you all day.\n\nWant me to look at other headphones?")

def test_four_phase_answers_are_repaired_keeping_four_sections():
    text,seen=run([draft(FOUR_ROBOTIC),draft(FOUR_FRIEND),OK],{'product_answer_shape':'four_phase'})
    assert text==FOUR_FRIEND and len(seen)==3
    assert 'same number of sections' in seen[1][0]['content']
    assert '\n\n' in text

def test_four_phase_rewrite_that_collapses_sections_keeps_original():
    text,seen=run([draft(FOUR_ROBOTIC),draft(FRIEND),OK],{'product_answer_shape':'four_phase'})
    assert text==FOUR_ROBOTIC and len(seen)==3

def test_non_four_phase_rules_do_not_mention_sections():
    text,seen=run([draft(ROBOTIC),draft(FRIEND),OK])
    assert 'same number of sections' not in seen[1][0]['content']

def test_answers_that_declare_no_product_are_never_rewritten():
    seen=[]
    async def infer(messages):
        seen.append(1);return json.dumps({'text':'Explore these catalog designs.','product_ids':[],'claims':[]} if len(seen)==1 else OK)
    text=asyncio.run(write_shopping_copy(infer,'ideas?',[catalog_result(row())],{},'catalog_results',20))
    assert text=='Explore these catalog designs.' and len(seen)==2

LEAKY="Studio Headphones are in stock locally (ID 1), status local_in_stock. I don't have the battery life for this pair."

def test_id_and_status_leak_is_repaired_by_the_voice_rewrite_instead_of_withholding():
    text,seen=run([draft(LEAKY),draft(FRIEND),OK])
    assert text==FRIEND and len(seen)==3

def test_leak_that_the_rewrite_does_not_fix_is_still_withheld_with_the_original_reason():
    from app.services.shopping_copy import ShoppingCopyError
    with pytest.raises(ShoppingCopyError) as caught:
        run([draft(LEAKY),draft(LEAKY),OK])
    assert caught.value.reason=='unsupported_numeric_or_link_claim'

def test_leak_tells_are_detected():
    assert voice_tells('Stock status: local_in_stock (ID 10).')
    assert voice_tells('spec.weight is 650 g')


def test_product_name_containing_a_tell_word_is_not_a_tell():
    assert voice_tells('Catalog headphones are wired.',['Catalog headphones'])==[]
    assert voice_tells('Catalog headphones are wired, per the catalog.',['Catalog headphones'])==['catalog']


LONG_ROBOTIC=("The Smart Watch is in stock locally.\n- Battery life: not listed in the catalog.\n- Sleep tracking: not mentioned in the specifications.\n"
    "Given the lack of these details, we can't confirm either feature for this watch. Would you like to look at other wearables?")
LONG_FLAT=("I have the Smart Watch in stock locally. I don't have the battery life for this one. I don't have sleep tracking details either. "
    "If those matter, we could look at another wearable that lists them. Would you like to explore alternatives?")
LONG_SPACED=("I have the Smart Watch in stock locally.\n\nI don't have its battery life, and I have nothing on sleep tracking either, so I won't guess on those.\n\n"
    "If they matter to you, we could look at another wearable that lists them.")

def test_long_answer_rewritten_into_one_flat_block_keeps_original():
    text,seen=run([draft(LONG_ROBOTIC),draft(LONG_FLAT),OK])
    assert text==LONG_ROBOTIC and len(seen)==3

def test_long_answer_rewritten_into_spaced_paragraphs_is_used():
    text,seen=run([draft(LONG_ROBOTIC),draft(LONG_SPACED),OK])
    assert text==LONG_SPACED

def test_cannot_confirm_forms_are_tells_and_rules_ban_them():
    assert voice_tells('We cannot confirm that.') and voice_tells('I am unable to confirm it.')
    text,seen=run([draft(ROBOTIC),draft(FRIEND),OK])
    assert 'blank line' in seen[1][0]['content'] and 'bullet' in seen[1][0]['content'] and 'unable to confirm' in seen[1][0]['content']


LONG_BULLETED=("I have the Smart Watch in stock locally, but two things are missing.\n\n- Battery life: I don't have it\n- Sleep tracking: I have nothing on it\n\n"
    "If those matter, we could look at another wearable that lists them.")

def test_rewrite_with_tidy_bullets_is_accepted_and_bullets_alone_do_not_trigger_repair():
    text,seen=run([draft(LONG_ROBOTIC),draft(LONG_BULLETED),OK])
    assert text==LONG_BULLETED and '- Battery life' in text
    text,seen=run([draft(LONG_BULLETED),OK])
    assert text==LONG_BULLETED and len(seen)==2


def test_rewrite_with_greeting_or_exclamation_keeps_original():
    chatty="Hey there! I have the Smart Watch in stock locally.\n\n- Battery life: I don't have it\n- Sleep tracking: I have nothing on it\n\nIf those matter, we could look at another wearable that lists them."
    text,seen=run([draft(LONG_ROBOTIC),draft(chatty),OK])
    assert text==LONG_ROBOTIC and len(seen)==3
    assert 'no greeting' in seen[1][0]['content'] and 'no exclamation' in seen[1][0]['content']
