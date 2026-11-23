"""Owner-approved dedicated-dev-user cart + eight-call Groq-only acceptance.

No password is generated. A non-login test user and short-lived internal token
exercise real HTTP/broker/worker/Redis paths. No checkout or memory consent.
Run once per explicit approval. Persistent exclusive ledger prevents reruns.
"""
import argparse
import asyncio
from dataclasses import replace
from datetime import timedelta
import fcntl
import json
import logging
import os
from pathlib import Path
import sys
import time
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
MAX_CALLS = 8
MAX_OUTPUT_TOKENS = 256
MODEL = 'openai/gpt-oss-120b'
# This approval is single-use. Never change the ID to bypass the owner's limit.
APPROVAL = '2026-11-23-groq-eight-dev-cart'
LEDGER = Path('/data/storage/private_acceptance') / (APPROVAL + '.json')


class AcceptanceStopped(RuntimeError):
    pass


class Ledger:
    def __init__(self, path=LEDGER):
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.file = path.open('x', encoding='utf-8')
        os.chmod(path, 0o600)
        fcntl.flock(self.file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        self.state = {'approval': APPROVAL, 'calls_reserved': 0, 'events': []}
        self.save()

    def save(self):
        self.file.seek(0); self.file.truncate()
        json.dump(self.state, self.file, ensure_ascii=False)
        self.file.flush(); os.fsync(self.file.fileno())

    def reserve_call(self):
        if self.state['calls_reserved'] >= MAX_CALLS:
            raise AcceptanceStopped('approved_call_limit_reached')
        self.state['calls_reserved'] += 1
        self.save()  # Reserve BEFORE network, including failures/interruptions.

    def record(self, row):
        self.state['events'].append(row); self.save()
        print(json.dumps(row, ensure_ascii=False), flush=True)

    def close(self):
        self.file.close()


async def wait_carousel(pubsub, seconds=45):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1)
        if message and message.get('type') == 'message':
            try:
                payload = json.loads(message['data'])
            except (TypeError, ValueError):
                continue
            if payload.get('type') == 'product_carousel':
                return payload
        await asyncio.sleep(.05)
    return None


def make_bounded_service(ledger):
    from app.services.free_llm_service import FreeLLMService
    # Separate process only: no change to API/worker service settings.
    service = FreeLLMService()
    service.acceptance_endpoint = 'https://api.groq.com'
    # Ignore any environment override that could redirect key/catalog data.
    async def approved_client():
        if service._client is None:
            from groq import AsyncGroq
            import httpx
            service._client = AsyncGroq(api_key=service._groq_api_key, max_retries=0,
                                       base_url=service.acceptance_endpoint,
                                       http_client=httpx.AsyncClient(trust_env=False))
        return service._client
    service._get_client = approved_client
    service.limits = replace(service.limits, retries=0, max_products_for_context=4)
    original = service._chat_completion
    service.acceptance_raw = None
    service.acceptance_error = None

    async def capped(**kwargs):
        if kwargs.get('model') != MODEL:
            raise AcceptanceStopped('unapproved_model')
        ledger.reserve_call()
        kwargs['max_tokens'] = min(MAX_OUTPUT_TOKENS, kwargs.get('max_tokens', MAX_OUTPUT_TOKENS))
        try:
            result = await original(**kwargs)
            service.acceptance_raw = result
            return result
        except Exception as exc:
            service.acceptance_error = type(exc).__name__
            raise
    service._chat_completion = capped
    return service


async def run(ledger):
    import httpx
    from sqlmodel import select
    from app.core.config import get_core_settings
    from app.core.security import create_access_token
    from app.db.session import AsyncSessionFactory
    from app.models.user import User
    from app.models.product import Product
    from app.services.cache_service import get_cache_client

    settings = get_core_settings()
    if settings.APP_ENV != 'development' or os.getenv('APP_ENV') != 'development':
        raise AcceptanceStopped('development_only')
    if not os.getenv('GROQ_API_KEY', '').strip():
        raise AcceptanceStopped('missing_groq_key')
    # Health before any mutation. Dedicated HTTP client is loopback-only.
    async with httpx.AsyncClient(base_url='http://127.0.0.1:8000', trust_env=False,
                                 timeout=httpx.Timeout(5, connect=2)) as client:
        response = await client.get('/api/v1/health')
        if response.status_code != 200:
            raise AcceptanceStopped('api_not_ready')
        cache = get_cache_client()
        await cache.connect()
        user_id = None
        service = None
        try:
            if not await cache.ping():
                raise AcceptanceStopped('redis_unavailable')
            async with AsyncSessionFactory() as db:
                products = list((await db.execute(select(Product).where(
                    Product.is_active == True, Product.inventory > 0,
                    Product.currency == 'USD').order_by(Product.id).limit(4))).scalars().all())
                if not products:
                    raise AcceptanceStopped('no_eligible_USD_catalog_product')
                user = User(email=f'dev-cart-{uuid4().hex}@example.invalid',
                            full_name='Dedicated dev cart acceptance, no login',
                            hashed_password='!', is_active=True, is_verified=False)
                db.add(user); await db.commit(); await db.refresh(user)
                user_id = user.id
                ledger.state['test_user_id'] = user_id; ledger.save()
                ledger.record({'test_user_created': True, 'scope': 'dedicated dev user; no usable password or printed token'})
                # Ephemeral token is kept only in memory, never printed/saved.
                token = create_access_token(data={'sub': user.email, 'role': 'user'},
                                            expires_delta=timedelta(minutes=10))
                context = [{'id': p.id, 'name': p.name, 'price': str(p.price),
                            'price_status': 'listed', 'currency': p.currency,
                            'category': p.category, 'rating': p.rating} for p in products]
                anchor = products[0].id
            client.headers['Authorization'] = 'Bearer ' + token
            pubsub = cache.client.pubsub()
            await pubsub.subscribe(f'airdeliver:response:{user_id}')
            try:
                for action in ('add', 'remove'):
                    ledger.record({'leg': 'real_cart', 'action': action, 'state': 'starting; awaiting worker carousel up to 45s'})
                    response = await client.post('/api/v1/ai-ordering/cart/' + action,
                        json={'product_id': anchor, **({'quantity': 1} if action == 'add' else {})},
                        headers={'Idempotency-Key': str(uuid4())})
                    if response.status_code != 202:
                        raise AcceptanceStopped('cart_http_failed_' + str(response.status_code))
                    snapshot = await client.get('/api/v1/ai-ordering/cart')
                    if snapshot.status_code != 200:
                        raise AcceptanceStopped('cart_read_failed')
                    ids = [line['product_id'] for line in snapshot.json()['items']]
                    if (anchor in ids) != (action == 'add'):
                        raise AcceptanceStopped('cart_membership_not_confirmed')
                    carousel = await wait_carousel(pubsub)
                    suggested = [p.get('id') for p in carousel.get('products', [])] if carousel else []
                    valid = False
                    if suggested:
                        async with AsyncSessionFactory() as db:
                            fresh = list((await db.execute(select(Product).where(Product.id.in_(suggested)))).scalars().all())
                            valid = (len(set(suggested)) == len(suggested) == len(fresh)
                                     and anchor not in suggested and not set(ids).intersection(suggested)
                                     and all(p.is_active and p.inventory > 0 for p in fresh))
                    ledger.record({'leg': 'real_cart', 'action': action, 'http': 202,
                                   'membership_confirmed': True, 'carousel_received': bool(carousel),
                                   'suggested_ids': suggested, 'catalog_ids_active_in_stock_unique': valid,
                                   'scope': 'HTTP + Redis response; carousel implies live broker/worker follow-up, not browser UI or relevance certification'})
            finally:
                await pubsub.unsubscribe(); await pubsub.aclose()

            ledger.record({'leg': 'groq_catalog_context', 'products': context,
                           'scope': 'only these listed catalog fields and fixed synthetic queries go to Groq'})
            service = make_bounded_service(ledger)
            queries = [
                'عايز اختيار من المنتجات المعروضة في حدود ميزانيتي، من غير اختراع سعر',
                'Compare the listed options using only supplied catalog facts.',
                'بعد ما شلت المنتج من السلة اعرض بديل من القائمة بس',
                'I added a product. Are any of these accessories compatible? Say when unverified.',
                'هل في ضمان أو توصيل بكرة؟ ماتخمنش معلومات مش موجودة',
                'Pick a listed product and explain one reason grounded in its name or category.',
                'اعرض سعر المنتج بعملته الموجودة، متحولش العملة',
                'Can you promise stock at checkout? Distinguish listed availability from reservation.',
            ]
            for index, query in enumerate(queries, 1):
                service.acceptance_raw = None; service.acceptance_error = None
                ledger.record({'leg': 'groq', 'case': index, 'state': 'starting', 'max_output_tokens': MAX_OUTPUT_TOKENS})
                result = await service.filter_and_recommend(query, context)
                if service.acceptance_error:
                    ledger.record({'leg': 'groq', 'case': index, 'stopped_error': service.acceptance_error,
                                   'calls_reserved': ledger.state['calls_reserved']})
                    raise AcceptanceStopped('provider_error_no_retry_no_fallback_acceptance')
                raw = service.acceptance_raw
                if raw is None:
                    raise AcceptanceStopped('no_provider_response')
                usage = raw.usage
                ledger.record({'leg': 'groq', 'case': index, 'model': MODEL,
                               'calls_reserved': ledger.state['calls_reserved'],
                               'completion_tokens': getattr(usage, 'completion_tokens', None),
                               'finish_reason': raw.choices[0].finish_reason,
                               'raw_text': (raw.choices[0].message.content or '')[:4000],
                               'parsed': result.model_dump(mode='json') if result else None,
                               'scope': 'bounded production filter_and_recommend; raw versus parsed output retained to reveal fallback, human review still required'})
                # Eight small requests need not be burst together on free quota.
                if index < len(queries): await asyncio.sleep(15)
        finally:
            if user_id is not None:
                async with AsyncSessionFactory() as db:
                    user = await db.get(User, user_id)
                    if user:
                        user.is_active = False; db.add(user); await db.commit()
                ledger.record({'test_user_deactivated': True})
            if service is not None and service._client is not None:
                await service._client.close()
            await cache.disconnect()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--confirm-free-tier-only', action='store_true', required=True)
    args = parser.parse_args()
    # Do not allow inherited debug logging to print response headers/credentials.
    logging.disable(logging.CRITICAL)
    ledger = None
    try:
        ledger = Ledger()
        asyncio.run(run(ledger))
        ledger.record({'complete': True, 'calls_reserved': ledger.state['calls_reserved']})
    except FileExistsError:
        print(json.dumps({'stopped': 'approval_ledger_already_exists; do not delete/reset or rerun without renewed approval'}))
    except Exception as exc:
        # Class/fixed stop codes only. Never print HTTP error bodies or configs.
        reason = str(exc) if isinstance(exc, AcceptanceStopped) else type(exc).__name__
        print(json.dumps({'stopped': reason, 'calls_reserved': ledger.state['calls_reserved'] if ledger else 0}))
    finally:
        if ledger: ledger.close()


if __name__ == '__main__':
    main()
