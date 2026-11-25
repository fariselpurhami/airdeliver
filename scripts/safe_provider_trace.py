#!/usr/bin/env python3
"""Read existing JSON application logs. Never call a provider or echo raw input."""
import ast
import collections
import json
import re
import sys

NUMERIC={'prompt_tokens','completion_tokens','total_tokens','characters','parse_position','limit_requests','remaining_requests','limit_tokens','remaining_tokens'}
BOOL={'output_cap_reached','parse_near_end','duplicate_keys','nested_error','has_code','has_type','has_generation'}
ENUMS={'generation':{'absent','present'},'finish':{'length','stop','content_filter'},'json':{'oversize','invalid','invalid_or_complex','valid'},'schema':{'not_supplied','violation','no_detected_violation'},'body_type':{'dict','list','str','NoneType','other'},'quota_unit':{'TPM','TPD','RPM','RPD','ITPM','OTPM'}}
CODES={'unclassified','json_validate_failed','model_decommissioned','model_not_found','rate_limit_exceeded','context_length_exceeded','invalid_request_error','invalid_api_key'}
CATEGORIES={'complexity_limit','value_type','missing_required','unexpected_field','array_too_long','array_too_short','inspection_partial','text_too_long','text_too_short','enum_mismatch'}

def metadata(raw):
    try:value=ast.literal_eval(raw)
    except (ValueError,SyntaxError,RecursionError,MemoryError):return {}
    if not isinstance(value,dict):return {}
    out={}
    for key,v in value.items():
        if key in NUMERIC and type(v) is int and 0<=v<=10**12:out[key]=v
        elif key in BOOL and type(v) is bool:out[key]=v
        elif key in ENUMS and isinstance(v,str) and v in ENUMS[key]:out[key]=v
        elif key in {'code','type'} and isinstance(v,str) and v in CODES:out[key]=v
        elif key in {'retry_after','reset_requests','reset_tokens'} and isinstance(v,str) and re.fullmatch(r'[0-9.hms]{1,32}',v):out[key]=v
        elif key=='categories' and isinstance(v,list):out[key]=sorted({x for x in v if isinstance(x,str) and x in CATEGORIES})
    return out

def event(row):
    if not isinstance(row,dict):return None
    msg=row.get('message');name=row.get('name')
    if not isinstance(msg,str) or len(msg)>16000:return None
    if name=='airdeliver.provider_budget':
        m=re.fullmatch(r'provider.usage model=([^\s]{1,128}) stage=([A-Za-z_]{1,64}) input_bytes_upper=(\d{1,12}) output_cap=(\d{1,12}) usage=(\{.*\})',msg)
        if m:
            # Never emit an unknown model/stage supplied by log input.
            stage=m[2] if m[2] in {'inference','RouterDecision','ShoppingDraft','GroundingReview','SpecDraft','SourceReview','cognitive_core'} else 'other'
            return {'event':'provider.usage','stage':stage,'input_bytes_upper':int(m[3]),'output_cap':int(m[4]),'usage':metadata(m[5])}
        m=re.fullmatch(r'provider.input_withheld stage=[A-Za-z_]{1,64}(?: reason=([a-z_]{1,80}))? (?:estimated_tokens|input_token_upper)=(\d{1,12}) (?:limit|output_cap)=(\d{1,12})',msg)
        if m:return {'event':'provider.input_withheld','reason':m[1] if m[1] in {'single_request_reservation_exceeds_budget','rolling_budget_or_cooldown_exhausted'} else 'other','estimated_tokens':int(m[2]),'bound':int(m[3])}
        m=re.fullmatch(r'provider.quota stage=[A-Za-z_]{1,64} input_token_upper=(\d{1,12}) output_cap=(\d{1,12}) metadata=(\{.*\})',msg)
        if m:return {'event':'provider.quota','input_token_upper':int(m[1]),'output_cap':int(m[2]),'metadata':metadata(m[3])}
    if name=='airdeliver.services.cognitive_core':
        for prefix in ('llm_provider_error_shape','llm_provider_json_diagnostics'):
            if msg.startswith(prefix+' metadata='):return {'event':prefix,'metadata':metadata(msg[len(prefix)+10:])}
        m=re.fullmatch(r'llm_provider_quota model=[^\s]{1,128} metadata=(\{.*\})',msg)
        if m:return {'event':'llm_provider_quota','metadata':metadata(m[1])}
        m=re.fullmatch(r'llm_provider_failure_code model=[^\s]{1,128} code=([a-z_]{1,80})',msg)
        if m:return {'event':'llm_provider_failure_code','code':m[1] if m[1] in CODES else 'unclassified'}
        m=re.fullmatch(r'llm_chat_completion_failure model=[^\s]{1,128} error_type=[A-Za-z_]{1,80} status_code=(None|\d{3})',msg)
        if m:return {'event':'llm_chat_completion_failure','status_code':None if m[1]=='None' else int(m[1])}
        if msg=='llm_chat_completion_timeout':return {'event':msg}
    return None

def main():
    counts=collections.Counter();emitted=0
    for line in sys.stdin:
        if len(line)>32768:counts['oversize_skipped']+=1;continue
        counts['lines']+=1
        try:row=json.loads(line)
        except (ValueError,RecursionError):counts['non_json_skipped']+=1;continue
        result=event(row)
        if result:
            counts[result['event']]+=1
            if emitted<1000:print(json.dumps(result,sort_keys=True));emitted+=1
    print(json.dumps({'summary':dict(counts),'emitted':emitted,'events_capped':emitted==1000},sort_keys=True))
if __name__=='__main__':main()
