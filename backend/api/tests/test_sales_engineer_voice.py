"""The writer contract asks for a consultative sales-engineer voice without loosening any evidence rule."""
import pytest
from app.services.compact_copy_contracts import contracts

@pytest.mark.parametrize('mode,ctx',[('catalog_results',{}),('catalog_results',{'gift_browse':True}),('catalog_results',{'product_answer_shape':'four_phase'})])
def test_writer_contract_carries_the_sales_engineer_voice_and_keeps_every_guard(mode,ctx):
    writer,reviewer=contracts(mode,ctx)
    low=writer.lower()
    for phrase in ('consultative sales engineer','one clear pick','at most one alternative','one focused question'):
        assert phrase in low
    for guard in ('never from superiority, urgency, scarcity, social proof','only supplied cards prove product facts','never invented certainty','low-pressure'):
        assert guard in low
    assert 'reject any violation of evidence' in reviewer.lower()

def test_reviewer_contract_is_not_loosened_by_the_voice():
    _,reviewer=contracts('catalog_results',{})
    assert 'sales engineer' not in reviewer.lower()
