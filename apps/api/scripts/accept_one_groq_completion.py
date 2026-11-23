"""One approved request5 completion, no cart/account mutation or ledger reset."""
import argparse
import asyncio
import hashlib
import json
import logging
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.accept_dev_cart import APPROVAL, LEDGER, AcceptanceStopped, make_bounded_service, MODEL
from scripts.reconcile_groq_acceptance import SUCCESSOR
from scripts.diagnose_groq_route import THIRD
from scripts.verify_corrected_groq_route import FOURTH, validate_chain

FIFTH=LEDGER.with_name(LEDGER.stem+'-one-completion-v5.json')
QUESTION='I removed the first listed product from my cart. Suggest an alternative only from the other listed products, in the same category. Do not invent compatibility, price, warranty or delivery facts. If none is suitable say so.'


def validate_four(original,second,third,fourth):
    hashes=validate_chain(original,second,third)
    raw=fourth.read_bytes();row=json.loads(raw)
    if (row.get('approval')!=APPROVAL or row.get('schema_version')!=4
        or type(row.get('calls_reserved_total')) is not int or row['calls_reserved_total']!=4
        or row.get('prior_sha256')!=hashes
        or not any(isinstance(e,dict) and e.get('leg')=='corrected_models_route'
            and e.get('success') is True and e.get('calls_reserved_total')==4
            and MODEL in e.get('active_model_ids',[]) for e in row.get('events',[]))):
        raise AcceptanceStopped('prior_four_ledgers_do_not_match_reviewed_success')
    return hashes+[hashlib.sha256(raw).hexdigest()]


class FifthLedger:
    def __init__(self,original=LEDGER,second=SUCCESSOR,third=THIRD,fourth=FOURTH,destination=FIFTH):
        self.paths=(original,second,third,fourth);self.hashes=validate_four(*self.paths)
        fd=os.open(destination,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        self.file=os.fdopen(fd,'w',encoding='utf-8')
        self.state={'approval':APPROVAL,'schema_version':5,'prior_sha256':self.hashes,
                    'inherited_calls':4,'calls_reserved_total':4,'calls_reserved':4,'events':[]}
        self.save()
    def save(self):
        self.file.seek(0);self.file.truncate();json.dump(self.state,self.file,ensure_ascii=False)
        self.file.flush();os.fsync(self.file.fileno())
    def reserve_call(self):
        if validate_four(*self.paths)!=self.hashes:raise AcceptanceStopped('prior_ledger_changed')
        if self.state['calls_reserved_total']!=4:raise AcceptanceStopped('one_fifth_request_only')
        self.state['calls_reserved_total']=5;self.state['calls_reserved']=5;self.save()
    def record(self,row):
        self.state['events'].append(row);self.save();print(json.dumps(row,ensure_ascii=False),flush=True)
    def close(self):self.file.close()


async def completion_once(ledger,service,context):
    ledger.record({'leg':'completion_context','question':QUESTION,'products':context,
                   'scope':'current synthetic/demo catalog facts; not a merchant offer'})
    service.acceptance_raw=None;service.acceptance_error=None
    result=await service.filter_and_recommend(QUESTION,context)
    if service.acceptance_error:
        ledger.record({'leg':'completion5','stopped':True,'error_class':service.acceptance_error,
                       'calls_reserved_total':ledger.state['calls_reserved_total'],'requests_remaining':3})
        return
    raw=service.acceptance_raw
    if raw is None:raise AcceptanceStopped('no_provider_response')
    ledger.record({'leg':'completion5','calls_reserved_total':ledger.state['calls_reserved_total'],
        'requests_remaining':3,'model':MODEL,'completion_tokens':getattr(raw.usage,'completion_tokens',None),
        'finish_reason':raw.choices[0].finish_reason,'raw_text':(raw.choices[0].message.content or '')[:4000],
        'parsed':result.model_dump(mode='json') if result else None,
        'scope':'one production recommendation method; human review raw versus parsed for fallback/truncation, not full chat/UI quality'})


async def run(ledger):
    if os.getenv('APP_ENV')!='development':raise AcceptanceStopped('development_only')
    if not os.getenv('GROQ_API_KEY','').strip():raise AcceptanceStopped('missing_groq_key')
    from sqlalchemy import text
    from app.db.session import AsyncSessionFactory
    async with AsyncSessionFactory() as db:
        await db.execute(text('SET TRANSACTION READ ONLY'))
        rows=(await db.execute(text("SELECT id,name,category,price,currency,rating FROM products WHERE is_active=true AND inventory>0 AND currency='USD' AND category=(SELECT category FROM products WHERE is_active=true AND inventory>0 AND currency='USD' ORDER BY id LIMIT 1) ORDER BY id LIMIT 4"))).mappings().all()
        context=[{**dict(row),'price':str(row['price']),'price_status':'listed'} for row in rows]
        await db.rollback()
    if len(context)<2:raise AcceptanceStopped('need_anchor_and_same_category_alternative')
    service=make_bounded_service(ledger)
    try:await completion_once(ledger,service,context)
    finally:
        if service._client is not None:await service._client.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--confirm-free-tier-only',action='store_true',required=True);parser.parse_args()
    logging.disable(logging.CRITICAL);ledger=None
    try:ledger=FifthLedger();asyncio.run(run(ledger))
    except FileExistsError:print(json.dumps({'stopped':'fifth_ledger_already_exists; do not delete/reset or rerun'}))
    except Exception as exc:print(json.dumps({'stopped':str(exc) if isinstance(exc,AcceptanceStopped) else type(exc).__name__}))
    finally:
        if ledger:ledger.close()


if __name__=='__main__':main()
