"""One approved request6, unchanged request5 model/settings, safe error fields."""
import argparse
import asyncio
import hashlib
import json
import logging
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.accept_dev_cart import APPROVAL, LEDGER, AcceptanceStopped
from scripts.reconcile_groq_acceptance import SUCCESSOR
from scripts.diagnose_groq_route import THIRD
from scripts.verify_corrected_groq_route import FOURTH
from scripts.accept_one_groq_completion import FIFTH, validate_four, run

SIXTH=LEDGER.with_name(LEDGER.stem+'-one-completion-v6.json')


def validate_five(original,second,third,fourth,fifth):
    hashes=validate_four(original,second,third,fourth)
    raw=fifth.read_bytes();row=json.loads(raw)
    if (row.get('approval')!=APPROVAL or row.get('schema_version')!=5
        or type(row.get('calls_reserved_total')) is not int or row['calls_reserved_total']!=5
        or row.get('prior_sha256')!=hashes
        or not any(isinstance(e,dict) and e.get('leg')=='completion5'
            and e.get('stopped') is True and e.get('error_class')=='BadRequestError'
            and e.get('calls_reserved_total')==5 and e.get('requests_remaining')==3
            for e in row.get('events',[]))):
        raise AcceptanceStopped('prior_five_ledgers_do_not_match_reviewed_failure')
    return hashes+[hashlib.sha256(raw).hexdigest()]


class SixthLedger:
    def __init__(self,original=LEDGER,second=SUCCESSOR,third=THIRD,fourth=FOURTH,fifth=FIFTH,destination=SIXTH):
        self.paths=(original,second,third,fourth,fifth);self.hashes=validate_five(*self.paths)
        fd=os.open(destination,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        self.file=os.fdopen(fd,'w',encoding='utf-8')
        self.state={'approval':APPROVAL,'schema_version':6,'prior_sha256':self.hashes,
                    'inherited_calls':5,'calls_reserved_total':5,'calls_reserved':5,'events':[]}
        self.save()
    def save(self):
        self.file.seek(0);self.file.truncate();json.dump(self.state,self.file,ensure_ascii=False)
        self.file.flush();os.fsync(self.file.fileno())
    def reserve_call(self):
        if validate_five(*self.paths)!=self.hashes:raise AcceptanceStopped('prior_ledger_changed')
        if self.state['calls_reserved_total']!=5:raise AcceptanceStopped('one_sixth_request_only')
        self.state['calls_reserved_total']=6;self.state['calls_reserved']=6;self.save()
    def record(self,row):
        self.state['events'].append(row);self.save();print(json.dumps(row,ensure_ascii=False),flush=True)
    def close(self):self.file.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--confirm-free-tier-only',action='store_true',required=True);parser.parse_args()
    logging.disable(logging.CRITICAL);ledger=None
    try:ledger=SixthLedger();asyncio.run(run(ledger,leg='completion6',remaining=2))
    except FileExistsError:print(json.dumps({'stopped':'sixth_ledger_already_exists; do not delete/reset or rerun'}))
    except Exception as exc:print(json.dumps({'stopped':str(exc) if isinstance(exc,AcceptanceStopped) else type(exc).__name__}))
    finally:
        if ledger:ledger.close()


if __name__=='__main__':main()
