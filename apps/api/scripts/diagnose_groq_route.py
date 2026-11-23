"""One owner-approved third request, no inference or ledger reset."""
import argparse
import asyncio
import hashlib
import json
import logging
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.accept_dev_cart import APPROVAL, LEDGER, AcceptanceStopped
from scripts.reconcile_groq_acceptance import SUCCESSOR, validate_original, error_metadata

THIRD = LEDGER.with_name(LEDGER.stem + '-route-v3.json')


class ThirdLedger:
    def __init__(self, original=LEDGER, second=SUCCESSOR, destination=THIRD):
        first_bytes = original.read_bytes()
        validate_original(json.loads(first_bytes))
        second_bytes = second.read_bytes()
        prior = json.loads(second_bytes)
        if (not isinstance(prior, dict) or prior.get('approval') != APPROVAL
                or prior.get('schema_version') != 2
                or type(prior.get('inherited_calls')) is not int or prior['inherited_calls'] != 1
                or type(prior.get('calls_reserved_total')) is not int or prior['calls_reserved_total'] != 2
                or prior.get('source_sha256') != hashlib.sha256(first_bytes).hexdigest()
                or not any(isinstance(row, dict) and row.get('leg') == 'models_list'
                           and row.get('stopped') is True and row.get('http_status') == 404
                           and row.get('calls_reserved_total') == 2 for row in prior.get('events', []))):
            raise AcceptanceStopped('prior_ledgers_do_not_match_reviewed_two_attempts')
        self.paths = (original, second)
        self.hashes = [hashlib.sha256(blob).hexdigest() for blob in (first_bytes, second_bytes)]
        fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        self.file = os.fdopen(fd, 'w', encoding='utf-8')
        self.state = {'approval': APPROVAL, 'schema_version': 3, 'prior_sha256': self.hashes,
                      'inherited_calls': 2, 'calls_reserved_total': 2,
                      'purpose': 'one third-request sanitized models-route diagnostic', 'events': []}
        self.save()

    def save(self):
        self.file.seek(0); self.file.truncate(); json.dump(self.state, self.file)
        self.file.flush(); os.fsync(self.file.fileno())

    def reserve(self):
        if [hashlib.sha256(path.read_bytes()).hexdigest() for path in self.paths] != self.hashes:
            raise AcceptanceStopped('prior_ledger_changed')
        if self.state['calls_reserved_total'] != 2:
            raise AcceptanceStopped('third_request_only')
        self.state['calls_reserved_total'] = 3; self.save()

    def record(self, row):
        self.state['events'].append(row); self.save(); print(json.dumps(row), flush=True)

    def close(self): self.file.close()


async def diagnose_once(ledger, client):
    from datetime import datetime, timezone
    ledger.reserve()
    row = {'leg': 'third_models_route', 'at_utc': datetime.now(timezone.utc).isoformat(),
           'method': 'GET', 'endpoint': 'https://api.groq.com/openai/v1/models',
           'calls_reserved_total': 3, 'requests_remaining': 5}
    try:
        # Same SDK route, not a guessed alternate host or a model fallback.
        result = await client.models.list()
        row.update({'success': True, 'active_models_count': len(result.data),
                    'scope': 'models visibility only; no completion or model switch'})
    except Exception as exc:
        row.update({'stopped': True, **error_metadata(exc)})
    ledger.record(row)


async def run(ledger):
    if os.getenv('APP_ENV') != 'development': raise AcceptanceStopped('development_only')
    key = os.getenv('GROQ_API_KEY', '').strip()
    if not key: raise AcceptanceStopped('missing_groq_key')
    import httpx
    from groq import AsyncGroq
    async with AsyncGroq(api_key=key, max_retries=0, timeout=20,
                         base_url='https://api.groq.com/openai/v1',
                         http_client=httpx.AsyncClient(trust_env=False)) as client:
        await diagnose_once(ledger, client)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--confirm-free-tier-only', action='store_true', required=True)
    parser.parse_args()
    logging.disable(logging.CRITICAL)
    ledger = None
    try:
        ledger = ThirdLedger(); asyncio.run(run(ledger))
    except FileExistsError:
        print(json.dumps({'stopped': 'third_ledger_already_exists; do not delete/reset or rerun'}))
    except Exception as exc:
        print(json.dumps({'stopped': str(exc) if isinstance(exc, AcceptanceStopped) else type(exc).__name__}))
    finally:
        if ledger: ledger.close()


if __name__ == '__main__': main()
