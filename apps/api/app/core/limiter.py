# file: apps/api/app/core/limiter.py
"""Native asyncio Redis admission, preserved decorator API, explicit proxy trust."""
import asyncio
from functools import wraps
import inspect
import time
from weakref import WeakKeyDictionary
from types import SimpleNamespace
from fastapi import Request
from fastapi.responses import JSONResponse
from limits import parse
from redis.asyncio import Redis
from redis.asyncio.retry import Retry
from redis.backoff import NoBackoff
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.routing import Match
from app.core.config import get_core_settings

SCRIPT="""local n=redis.call('INCR',KEYS[1]); if n==1 then redis.call('EXPIRE',KEYS[1],ARGV[1]) end; return n"""


class AdmissionUnavailable(Exception):pass


class AsyncLimiter:
    def __init__(self,settings):
        self.enabled=True
        self.default=parse(settings.RATE_LIMIT_DEFAULT)
        self.uri=settings.REDIS_URL
        self._loops=WeakKeyDictionary()

    def _state(self):
        loop=asyncio.get_running_loop()
        if loop not in self._loops:
            client=Redis.from_url(self.uri,socket_timeout=.5,socket_connect_timeout=.5,
                # Never retry a potentially applied quota increment.
                max_connections=1,decode_responses=True,protocol=2,retry=Retry(NoBackoff(),0)) if self.uri else None
            self._loops[loop]=(client,asyncio.Semaphore(1),{})
        return self._loops[loop]

    async def close(self):
        state=self._loops.pop(asyncio.get_running_loop(),None)
        if state and state[0]:await state[0].aclose()

    async def check(self,request,value,scope):
        if not self.enabled:return
        client,slots,memory=self._state()
        item=parse(value) if isinstance(value,str) else value
        # request.client is server-established. Never parse arbitrary forwarding headers.
        import hashlib
        identifier=hashlib.sha256((get_remote_address(request)+'|'+scope).encode()).hexdigest()
        key=f'airdeliver:http:v2:{item.amount}:{item.get_expiry()}:{identifier}'
        started=time.monotonic();stage='queue'
        try:
            async with asyncio.timeout(1.0):
                async with slots:
                    if client:
                        stage='redis_eval'
                        count=await client.eval(SCRIPT,1,key,item.get_expiry())
                    else:
                        now=time.monotonic();count,expiry=memory.get(key,(0,0))
                        if expiry<=now:count,expiry=0,now+item.get_expiry()
                        if len(memory)>=10000 and key not in memory:
                            for old in [k for k,v in memory.items() if v[1]<=now]:memory.pop(old,None)
                            if len(memory)>=10000:raise AdmissionUnavailable()
                        count+=1;memory[key]=(count,expiry)
        except asyncio.CancelledError:raise
        except Exception as exc:
            import logging
            logging.getLogger('airdeliver.admission').warning('admission_unavailable type=%s cause=%s stage=%s elapsed_ms=%d',type(exc).__name__,type(exc.__cause__).__name__,stage,round((time.monotonic()-started)*1000))
            raise AdmissionUnavailable() from exc
        if count>item.amount:
            request.state.view_rate_limit=None
            raise RateLimitExceeded(SimpleNamespace(error_message=None,limit=item))

    def _inject_headers(self,response,current_limit):
        # Legacy SlowAPI429 handler compatibility; quota headers were disabled.
        return response

    def limit(self,value):
        parse(value)
        def decorator(function):
            @wraps(function)
            async def wrapped(*args,**kwargs):
                request=kwargs.get('request') or next((v for v in args if isinstance(v,Request)),None)
                if request is None:raise RuntimeError('Rate-limited route requires Request')
                await self.check(request,value,function.__module__+'.'+function.__name__)
                return await function(*args,**kwargs)
            wrapped.__signature__=inspect.signature(function,eval_str=True)
            wrapped._airdeliver_limit=value
            return wrapped
        return decorator

    def exempt(self,function):
        function._airdeliver_exempt=True
        return function


class AsyncRateLimitMiddleware:
    def __init__(self,app):self.app=app
    async def __call__(self,scope,receive,send):
        if scope['type']=='lifespan':
            try:await self.app(scope,receive,send)
            finally:await scope['app'].state.limiter.close()
            return
        if scope['type']!='http':return await self.app(scope,receive,send)
        request=Request(scope,receive=receive);instance=scope['app'].state.limiter
        endpoint=None
        for route in scope['app'].routes:
            match,_=route.matches(scope)
            if match==Match.FULL and hasattr(route,'endpoint'):endpoint=route.endpoint;break
        if endpoint and not getattr(endpoint,'_airdeliver_exempt',False) and not getattr(endpoint,'_airdeliver_limit',None):
            try:await instance.check(request,instance.default,endpoint.__module__+'.'+endpoint.__name__)
            except AdmissionUnavailable:
                return await storage_unavailable(request,None)(scope,receive,send)
            except RateLimitExceeded as exc:
                return await JSONResponse(status_code=429,content={'error':f'Rate limit exceeded: {exc.detail}'})(scope,receive,send)
        return await self.app(scope,receive,send)


def build_limiter(settings):return AsyncLimiter(settings)
limiter=build_limiter(get_core_settings())


def storage_unavailable(request,exc):
    return JSONResponse(status_code=503,content={'detail':'Rate limit storage unavailable'},headers={'Retry-After':'1'})


def install_rate_limiting(app,instance=None):
    app.state.limiter=instance if instance is not None else limiter
    app.add_exception_handler(AdmissionUnavailable,storage_unavailable)
    app.add_middleware(AsyncRateLimitMiddleware)
