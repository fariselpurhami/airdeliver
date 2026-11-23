"""Single models-list diagnostic, inherited eight-request budget, no completions.

Never deletes or changes the original acceptance ledger. Run once after owner
approval for the diagnostic. A model-list entry does not prove completion access.
"""
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

SUCCESSOR = LEDGER.with_name(LEDGER.stem + '-models-v2.json')


def validate_original(data):
    if (not isinstance(data, dict) or data.get('approval') != APPROVAL
            or type(data.get('calls_reserved')) is not int or data['calls_reserved'] != 1
            or not any(isinstance(row, dict) and row.get('leg') == 'groq'
                       and row.get('case') == 1 and row.get('stopped_error') == 'NotFoundError'
                       and row.get('calls_reserved') == 1 for row in data.get('events', []))
            or not any(isinstance(row, dict) and row.get('test_user_deactivated') is True
                       for row in data.get('events', []))):
        raise AcceptanceStopped('original_ledger_does_not_match_reviewed_single_failed_attempt')
    return data


class Successor:
    def __init__(self, source=LEDGER, destination=SUCCESSOR):
        # Validate and hash immutable source before creating a successor.
        raw = source.read_bytes()
        original = validate_original(json.loads(raw))
        self.source = source
        self.source_digest = hashlib.sha256(raw).hexdigest()
        destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        self.file = os.fdopen(fd, 'w', encoding='utf-8')
        self.state = {'approval': APPROVAL, 'schema_version': 2,
                      'source_sha256': self.source_digest,
                      'inherited_calls': original['calls_reserved'],
                      'calls_reserved_total': original['calls_reserved'],
                      'purpose': 'one models-list diagnostic only', 'events': []}
        self.save()

    def save(self):
        self.file.seek(0); self.file.truncate()
        json.dump(self.state, self.file); self.file.flush(); os.fsync(self.file.fileno())

    def reserve(self):
        if hashlib.sha256(self.source.read_bytes()).hexdigest() != self.source_digest:
            raise AcceptanceStopped('original_ledger_changed')
        if self.state['calls_reserved_total'] != 1:
            raise AcceptanceStopped('one_diagnostic_only')
        self.state['calls_reserved_total'] += 1
        self.save()

    def record(self, row):
        self.state['events'].append(row); self.save()
        print(json.dumps(row), flush=True)

    def close(self):
        self.file.close()


def error_metadata(exc):
    code = getattr(exc, 'code', None)
    # Only fixed public provider error codes, not arbitrary returned strings.
    allowed = {'model_not_found', 'model_decommissioned', 'invalid_api_key',
               'rate_limit_exceeded', 'insufficient_quota', 'permission_denied',
               'organization_restricted', 'not_found'}
    status = getattr(exc, 'status_code', None)
    return {'error_class': type(exc).__name__,
            'http_status': status if type(status) is int else None,
            'provider_code': code if isinstance(code, str) and code in allowed else 'not_in_allowlist'}


async def list_once(ledger, client):
    ledger.reserve()  # Includes failures, no SDK/service retry.
    try:
        result = await client.models.list()
        ids = sorted(set(row.id for row in result.data if isinstance(row.id, str)
                         and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:/-]{0,199}', row.id)
                         and getattr(row, 'active', True) is not False))
        ledger.record({'leg': 'models_list', 'active_model_ids': ids,
                       'calls_reserved_total': ledger.state['calls_reserved_total'],
                       'requests_remaining': 8 - ledger.state['calls_reserved_total'],
                       'scope': 'list visibility only; no completion, access or free-plan billing certification'})
    except Exception as exc:
        ledger.record({'leg': 'models_list', 'stopped': True, **error_metadata(exc),
                       'calls_reserved_total': ledger.state['calls_reserved_total'],
                       'requests_remaining': 8 - ledger.state['calls_reserved_total']})


async def run(ledger):
    if os.getenv('APP_ENV') != 'development':
        raise AcceptanceStopped('development_only')
    key = os.getenv('GROQ_API_KEY', '').strip()
    if not key: raise AcceptanceStopped('missing_groq_key')
    import httpx
    from groq import AsyncGroq
    async with AsyncGroq(api_key=key, max_retries=0,
                         base_url='https://api.groq.com/openai/v1', timeout=20,
                         http_client=httpx.AsyncClient(trust_env=False)) as client:
        await list_once(ledger, client)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--confirm-free-tier-only', action='store_true', required=True)
    parser.parse_args()
    logging.disable(logging.CRITICAL)
    ledger = None
    try:
        ledger = Successor()
        asyncio.run(run(ledger))
    except FileExistsError:
        print(json.dumps({'stopped': 'successor_already_exists; do not delete/reset or rerun'}))
    except Exception as exc:
        reason = str(exc) if isinstance(exc, AcceptanceStopped) else type(exc).__name__
        print(json.dumps({'stopped': reason, 'scope': 'no automatic retries or reset'}))
    finally:
        if ledger: ledger.close()


if __name__ == '__main__': main()
