"""Read-only extraction matches deployed formatter, never raw logs."""
import importlib.util,json,logging
from pathlib import Path
from app.core.logging_config import JsonFormatter
spec=importlib.util.spec_from_file_location('trace',Path(__file__).resolve().parents[3]/'scripts/safe_provider_trace.py')
trace=importlib.util.module_from_spec(spec);spec.loader.exec_module(trace)

def formatted(name,message):
 return json.loads(JsonFormatter().format(logging.LogRecord(name,logging.WARNING,'',1,message,(),None)))
def test_formatter_usage_and_private_unknown_fields():
 result=trace.event(formatted('airdeliver.provider_budget',"provider.usage model=openai/gpt-oss-120b stage=ShoppingDraft input_bytes_upper=4000 output_cap=640 usage={'prompt_tokens': 900, 'completion_tokens': 120, 'total_tokens': 1020, 'private': 'CUSTOMER_SECRET'}"))
 assert result['usage']=={'prompt_tokens':900,'completion_tokens':120,'total_tokens':1020}
 assert 'CUSTOMER_SECRET' not in json.dumps(result)
def test_formatter_structural_and_quota():
 result=trace.event(formatted('airdeliver.services.cognitive_core',"llm_provider_json_diagnostics metadata={'generation':'present','schema':'violation','categories':['missing_required','CUSTOMER_SECRET']}"))
 assert result['metadata']['categories']==['missing_required']
 result=trace.event(formatted('airdeliver.services.cognitive_core',"llm_provider_quota model=openai/gpt-oss-120b metadata={'quota_unit':'TPM','remaining_tokens':0,'retry_after':'60','message':'CUSTOMER_SECRET'}"))
 assert result['metadata']=={'quota_unit':'TPM','remaining_tokens':0,'retry_after':'60'}
def test_unsafe_and_unrelated_messages_omitted():
 for msg in ['raw CUSTOMER_SECRET',"llm_provider_error_shape metadata=__import__('os').system('false')"]:
  result=trace.event(formatted('airdeliver.services.cognitive_core',msg));assert not result or result['metadata']=={}
 assert trace.event(formatted('untrusted','llm_chat_completion_timeout')) is None
