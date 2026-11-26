"""Actual SDK/HTTP serialization against a loopback server, never a provider."""
import asyncio,json
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from threading import Thread
from unittest.mock import AsyncMock
import pytest
from groq import AsyncGroq
from tests.test_llm_execution_limits import service
from tests.test_sales_response_service import request

@pytest.mark.asyncio
@pytest.mark.parametrize('reject',[False,True])
async def test_native_sdk_composition_and_full_review_over_loopback_http(reject):
 captured=[];card=request().products[0]
 class Handler(BaseHTTPRequestHandler):
  def log_message(self,*args):pass
  def do_POST(self):
   data=json.loads(self.rfile.read(int(self.headers['Content-Length'])));captured.append(data)
   schema=data['response_format']['json_schema']['name']
   if schema=='DecisionBlocksDraft':
    refs=json.loads(data['messages'][1]['content'])['claim_reference_map'];key=next(k for k,v in refs.items() if v['field']=='name')
    result={'decision':'conditional','preferred_product_id':card.id,'decisive_unknown':'Rain protection.','blocks':[{'kind':'paragraph','text_template':'Conditionally prefer {{'+key+'}}.'},{'kind':'paragraph','text_template':'Verify rain protection first.'}]}
   else:
    assert schema=='GroundingReview'
    result={'supported':not reject,'all_product_mentions_declared':True,'no_unsupported_commercial_claims':True,'fulfills_discovery_task':True}
   body=json.dumps({'id':'loopback','object':'chat.completion','created':1,'model':'openai/gpt-oss-120b','choices':[{'index':0,'message':{'role':'assistant','content':json.dumps(result)},'finish_reason':'stop'}]}).encode()
   self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
 server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=Thread(target=server.serve_forever,daemon=True);thread.start()
 sdk=AsyncGroq(api_key='loopback-only',base_url=f'http://127.0.0.1:{server.server_port}/v1',max_retries=0)
 llm=service();llm._get_client=AsyncMock(return_value=sdk)
 try:
  result=await llm.consult_catalog(question='Choose one for rain.',cards=[card],evidence={'claim_binding':'decision_blocks_v1'})
  assert len(captured)==2
  assert [c['response_format']['json_schema']['name'] for c in captured]==['DecisionBlocksDraft','GroundingReview']
  assert all(c['response_format']['json_schema']['strict'] is True for c in captured)
  assert [c['max_tokens'] for c in captured]==[1200,256]
  assert captured[1]['reasoning_effort']=='low'
  review=json.loads(captured[1]['messages'][1]['content'])
  assert review['draft']['text']==f'Conditionally prefer {card.name}.\n\nVerify rain protection first.'
  assert review['decision_record']['preferred_product_id']==card.id
  assert result.response_kind==('system_notice' if reject else 'catalog_results')
  assert result.products==([] if reject else [card])
 finally:
  await sdk.close();await asyncio.to_thread(server.shutdown);server.server_close();thread.join(timeout=2)
