"""One approved fourth GET /models, corrected Groq1.7 origin, no completion."""
import argparse
import asyncio
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.accept_dev_cart import APPROVAL, LEDGER, AcceptanceStopped
from scripts.reconcile_groq_acceptance import SUCCESSOR, validate_original, error_metadata
from scripts.diagnose_groq_route import THIRD

FOURTH = LEDGER.with_name(LEDGER.stem + '-corrected-route-v4.json')


def validate_chain(original, second, third):
    raws=[p.read_bytes() for p in (original,second,third)]
    rows=[json.loads(raw) for raw in raws]
    hashes=[hashlib.sha256(raw).hexdigest() for raw in raws]
    validate_original(rows[0])
    two,three=rows[1:]
    if (two.get('approval') != APPROVAL or two.get('schema_version') != 2
            or type(two.get('calls_reserved_total')) is not int or two['calls_reserved_total'] != 2
            or two.get('source_sha256') != hashes[0]
            or three.get('approval') != APPROVAL or three.get('schema_version') != 3
            or type(three.get('calls_reserved_total')) is not int or three['calls_reserved_total'] != 3
            or three.get('prior_sha256') != hashes[:2]
            or not any(isinstance(e,dict) and e.get('leg')=='third_models_route'
                       and e.get('stopped') is True and e.get('http_status')==404
                       and e.get('calls_reserved_total')==3 for e in three.get('events',[]))):
        raise AcceptanceStopped('prior_chain_does_not_match_reviewed_three_attempts')
    return hashes


class FourthLedger:
    def __init__(self, original=LEDGER, second=SUCCESSOR, third=THIRD, destination=FOURTH):
        self.paths=(original,second,third)
        self.hashes=validate_chain(*self.paths)
        fd=os.open(destination,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        self.file=os.fdopen(fd,'w',encoding='utf-8')
        self.state={'approval':APPROVAL,'schema_version':4,'prior_sha256':self.hashes,
                    'inherited_calls':3,'calls_reserved_total':3,'events':[]}
        self.save()

    def save(self):
        self.file.seek(0);self.file.truncate();json.dump(self.state,self.file)
        self.file.flush();os.fsync(self.file.fileno())

    def reserve(self):
        if validate_chain(*self.paths) != self.hashes:
            raise AcceptanceStopped('prior_ledger_changed')
        if self.state['calls_reserved_total'] != 3:raise AcceptanceStopped('fourth_request_only')
        self.state['calls_reserved_total']=4;self.save()

    def record(self,row):
        self.state['events'].append(row);self.save();print(json.dumps(row),flush=True)

    def close(self):self.file.close()


async def list_once(ledger,client):
    from datetime import datetime,timezone
    ledger.reserve()
    row={'leg':'corrected_models_route','at_utc':datetime.now(timezone.utc).isoformat(),
         'method':'GET','endpoint':'https://api.groq.com/openai/v1/models',
         'calls_reserved_total':4,'requests_remaining':4}
    try:
        result=await client.models.list()
        ids=sorted(set(m.id for m in result.data if isinstance(m.id,str)
            and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:/-]{0,199}',m.id)
            and getattr(m,'active',True) is not False))
        row.update({'success':True,'active_model_ids':ids,
                    'scope':'list visibility only; no model completion or switch'})
    except Exception as exc:row.update({'stopped':True,**error_metadata(exc)})
    ledger.record(row)


async def run(ledger):
    if os.getenv('APP_ENV')!='development':raise AcceptanceStopped('development_only')
    key=os.getenv('GROQ_API_KEY','').strip()
    if not key:raise AcceptanceStopped('missing_groq_key')
    import httpx
    from groq import AsyncGroq
    async with AsyncGroq(api_key=key,max_retries=0,timeout=20,base_url='https://api.groq.com',
        http_client=httpx.AsyncClient(trust_env=False)) as client:
        await list_once(ledger,client)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--confirm-free-tier-only',action='store_true',required=True);parser.parse_args()
    logging.disable(logging.CRITICAL)
    ledger=None
    try:ledger=FourthLedger();asyncio.run(run(ledger))
    except FileExistsError:print(json.dumps({'stopped':'fourth_ledger_already_exists; do not delete/reset or rerun'}))
    except Exception as exc:print(json.dumps({'stopped':str(exc) if isinstance(exc,AcceptanceStopped) else type(exc).__name__}))
    finally:
        if ledger:ledger.close()


if __name__=='__main__':main()
