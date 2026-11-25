from types import SimpleNamespace
from unittest.mock import AsyncMock,Mock
import logging
import pytest
from worker_entrypoint import WorkerRuntime

def runtime(rows):
    rt=object.__new__(WorkerRuntime)
    rt.services=SimpleNamespace(behavior=SimpleNamespace(track_interaction=AsyncMock()),commerce=SimpleNamespace(milvus_client=SimpleNamespace(get=Mock(return_value=rows)),milvus_product_text_col='current'))
    return rt

@pytest.mark.asyncio
@pytest.mark.parametrize('pid',[True,'7',7.5,0,-1,2147483648,None])
async def test_worker_never_coerces_a_different_product_identity(pid):
    rt=runtime([{'id':7,'vector':[0.1]*384}])
    assert await rt._product_vector(pid) is None
    rt.services.commerce.milvus_client.get.assert_not_called()

@pytest.mark.asyncio
@pytest.mark.parametrize('rows',[
 [],[{'id':8,'vector':[0.1]}],[{'id':7,'vector':[0.1]},{'id':8,'vector':[0.2]}],
 [{'id':True,'vector':[0.1]}],[{'id':7,'vector':[float('nan')]}],
 [{'id':7,'vector':[float('inf')]}],[{'id':7,'vector':[True]}],
 [{'id':7,'vector':['0.1']}],[{'id':7,'vector':[]}],[{'id':7,'vector':[0.1]*4097}],
])
async def test_actual_milvus_return_must_match_exact_id_and_finite_vector(rows):
    assert await runtime(rows)._product_vector(7) is None

@pytest.mark.asyncio
async def test_worker_preserves_valid_product_and_does_not_mutate_input():
    rt=runtime([{'id':7,'vector':[0.1]*384}]);meta={'id':7,'action':'add'}
    await rt.track_behavior(9,'cart',meta)
    assert meta=={'id':7,'action':'add'}
    sent=rt.services.behavior.track_interaction.await_args.args
    assert sent[0:2]==(9,'cart') and sent[2]['vec']==[0.1]*384

@pytest.mark.asyncio
async def test_failure_diagnostics_do_not_log_backend_or_customer_payload(caplog):
    rt=runtime([]);rt.services.commerce.milvus_client.get.side_effect=RuntimeError('PRIVATE_SENTINEL')
    with caplog.at_level(logging.WARNING):assert await rt._product_vector(7) is None
    assert 'PRIVATE_SENTINEL' not in caplog.text and 'RuntimeError' in caplog.text
