"""Packed excerpt provenance is application-owned, not source page metadata."""
import json
from unittest.mock import AsyncMock
import pytest
from app.services.research_evidence_budget import pack_sources
from app.services.product_knowledge_service import answer_product_question

@pytest.mark.parametrize('text,budget',[('Alpha OLED.',100),('noise '*100+' Alpha OLED. '+'tail '*100,80),('سياق '*100+' Alpha OLED. '+'سياق '*100,90)])
def test_packed_window_records_exact_input_slice_and_bounded_bytes(text,budget):
 original={'url':'https://maker.example/a','text':text,'evidence_window':{'input_chars':1,'truncated':False}}
 row=pack_sources([original],'Alpha OLED',byte_budget=budget)[0]
 info=row['evidence_window']
 assert set(info)=={'input_chars','start_char','end_char','truncated'}
 assert info['input_chars']==len(text)
 assert row['text']==text[info['start_char']:info['end_char']]
 assert info['truncated']==(row['text']!=text)
 assert len(row['text'].encode())<=budget
 assert original['evidence_window']=={'input_chars':1,'truncated':False}

@pytest.mark.asyncio
async def test_both_product_passes_receive_packed_scope_without_absence_proof():
 text='noise '*400+' Alpha uses wood. '+'tail '*400
 calls=[]
 async def infer(messages):
  calls.append((messages[0]['content'],json.loads(messages[1]['content'])))
  if len(calls)==1:return json.dumps({'covered_targets':['Alpha'],'facts':[{'label':'Material','quote':'Alpha uses wood.','source':0}]})
  return json.dumps({'supported':True,'exact_model':True,'product_information_only':True})
 result=await answer_product_question(infer,'Alpha material',targets=('Alpha',),lookup=AsyncMock(return_value=[{'url':'https://maker.example/a','text':text}]))
 assert result.confidence>0 and len(calls)==2
 row=calls[0][1]['untrusted_sources'][0]
 assert row['evidence_window']['truncated'] is True
 assert row['evidence_window']['input_chars']==len(text)
 assert calls[1][1]['input']==calls[0][1]
 assert all('An omitted excerpt is not evidence of absence' in policy for policy,_ in calls)
