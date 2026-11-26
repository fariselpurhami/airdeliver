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
FRIEND="I don't have the battery life for Studio Headphones, so I won't guess."

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
FOUR_FRIEND=("I don't have the battery life for Studio Headphones.\n\nThat is the one gap I can see.\n\n"
    "So I can't say if it lasts you all day.\n\nWant me to look at other headphones?")

def test_four_phase_answers_are_repaired_keeping_four_sections():
    text,seen=run([draft(FOUR_ROBOTIC),draft(FOUR_FRIEND),OK],{'product_answer_shape':'four_phase'})
    assert text==FOUR_FRIEND and len(seen)==3
    assert 'exactly four' in seen[1][0]['content']
    assert '\n\n' in text

def test_four_phase_rewrite_that_collapses_sections_keeps_original():
    text,seen=run([draft(FOUR_ROBOTIC),draft(FRIEND),OK],{'product_answer_shape':'four_phase'})
    assert text==FOUR_ROBOTIC and len(seen)==3

def test_non_four_phase_rules_do_not_mention_sections():
    text,seen=run([draft(ROBOTIC),draft(FRIEND),OK])
    assert 'exactly four' not in seen[1][0]['content']

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
LONG_FLAT=("I have the Smart Watch you asked about. I don't have the battery life for this one. I don't have sleep tracking details either. "
    "If those matter, we could look at another wearable that lists them. Would you like to explore alternatives?")
LONG_SPACED=("I have the Smart Watch you asked about.\n\nI don't have its battery life, and I have nothing on sleep tracking either, so I won't guess on those.\n\n"
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


LONG_BULLETED=("I have the Smart Watch you asked about, but two things are missing.\n\n- Battery life: I don't have it\n- Sleep tracking: I have nothing on it\n\n"
    "If those matter, we could look at another wearable that lists them.")

def test_rewrite_with_tidy_bullets_is_accepted_and_bullets_alone_do_not_trigger_repair():
    text,seen=run([draft(LONG_ROBOTIC),draft(LONG_BULLETED),OK])
    assert text==LONG_BULLETED and '- Battery life' in text
    text,seen=run([draft(LONG_BULLETED),OK])
    assert text==LONG_BULLETED and len(seen)==2


def test_rewrite_with_greeting_or_exclamation_keeps_original():
    chatty="Hey there! I have the Smart Watch you asked about.\n\n- Battery life: I don't have it\n- Sleep tracking: I have nothing on it\n\nIf those matter, we could look at another wearable that lists them."
    text,seen=run([draft(LONG_ROBOTIC),draft(chatty),OK])
    assert text==LONG_ROBOTIC and len(seen)==3
    assert 'no greeting' in seen[1][0]['content'] and 'no exclamation' in seen[1][0]['content']


def test_rules_ask_for_warm_voiced_bullets_and_closing():
    text,seen=run([draft(ROBOTIC),draft(FRIEND),OK])
    assert 'never bare fragments' in seen[1][0]['content'] and 'thoughtful friend' in seen[1][0]['content']


STOCKY="Studio Headphones are in stock locally and wired. Nothing else is missing for your question."

def test_stock_and_place_phrase_is_a_tell_unless_the_customer_asked_about_availability():
    seen=[]
    def go(msg,replies):
        calls=[]
        async def infer(m):
            calls.append(m);return json.dumps(replies[len(calls)-1])
        text=asyncio.run(write_shopping_copy(infer,msg,[catalog_result(row())],{},'catalog_results',20))
        return text,calls
    text,calls=go('is it wired?',[draft(STOCKY),draft("Studio Headphones are wired. Nothing else is missing for your question."),OK])
    assert text.startswith('Studio Headphones are wired') and len(calls)==3
    text,calls=go('is it in stock?',[draft(STOCKY),OK])
    assert text==STOCKY and len(calls)==2

def test_writer_contract_says_not_to_state_stock_unless_asked():
    text,seen=run([draft(FRIEND),OK])
    assert 'Do not state stock or availability' in seen[0][0]['content']


def test_rules_ask_for_one_connected_thread_without_outside_facts():
    text,seen=run([draft(ROBOTIC),draft(FRIEND),OK])
    assert 'one connected thread' in seen[1][0]['content'] and 'Add no outside facts' in seen[1][0]['content']


def test_four_phase_rewrite_that_merges_into_three_blocks_keeps_original_and_rules_name_four_blocks():
    three="I don't have the battery life for Studio Headphones.\n\n- Battery: I don't have it\n- Sleep: I don't have it\n\nWant me to look at other headphones?"
    text,seen=run([draft(FOUR_ROBOTIC),draft(three),OK],{'product_answer_shape':'four_phase'})
    assert text==FOUR_ROBOTIC and len(seen)==3
    assert 'keep exactly four' in seen[1][0]['content']


def test_rewrite_rejected_by_review_falls_back_to_reviewed_original_instead_of_withholding():
    bad={'supported':True,'all_product_mentions_declared':True,'no_unsupported_commercial_claims':True,'fulfills_discovery_task':False}
    text,seen=run([draft(ROBOTIC),draft(FRIEND),bad,OK])
    assert text==ROBOTIC and len(seen)==4

def test_original_rejected_by_review_is_still_withheld_after_fallback():
    import pytest
    from app.services.shopping_copy import ShoppingCopyError
    bad={'supported':True,'all_product_mentions_declared':True,'no_unsupported_commercial_claims':True,'fulfills_discovery_task':False}
    with pytest.raises(ShoppingCopyError):
        run([draft(ROBOTIC),draft(FRIEND),bad,bad])

def test_rules_vary_shape_and_limit_bullets_to_multiple_precise_items():
    text,seen=run([draft(FOUR_ROBOTIC),draft(FOUR_FRIEND),OK],{'product_answer_shape':'four_phase'})
    c=seen[1][0]['content']
    assert 'rather than a fixed pattern' in c and 'two or more precise' in c and 'never reuse a stock opening' in c


BESTY="Studio Headphones are wired. I can suggest the best fit once you tell me what you listen to."

def test_superiority_wording_gets_the_rewrite_and_is_withheld_only_if_the_rewrite_keeps_it():
    text,seen=run([draft(BESTY),draft("Studio Headphones are wired. Tell me what you listen to and I will narrow it down."),OK])
    assert 'best' not in text.casefold() and len(seen)==3
    import pytest
    from app.services.shopping_copy import ShoppingCopyError
    with pytest.raises(ShoppingCopyError):
        run([draft(BESTY),draft("Studio Headphones are the best choice for you."),OK])


def test_same_amount_in_a_different_format_has_the_same_key():
    from app.services.shopping_copy import _num_key
    assert _num_key('300')==_num_key('300.00')==_num_key('300.0')
    assert _num_key('1,024')==_num_key('1024')
    assert _num_key('100.68')!=_num_key('100') and _num_key('99')!=_num_key('9')


def test_rewrite_with_a_single_bullet_keeps_original():
    one="I don't have the battery life for Studio Headphones.\n\n- Battery: I don't have it\n\nWant me to look at other headphones?\n\nI can check a few."
    text,seen=run([draft(FOUR_ROBOTIC),draft(one),OK],{'product_answer_shape':'four_phase'})
    assert text==FOUR_ROBOTIC and len(seen)==3
