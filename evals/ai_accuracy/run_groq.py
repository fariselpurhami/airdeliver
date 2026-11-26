"""Run product-answer cases through the real FreeLLMService on the free Groq tier.

Guards: only api.groq.com chat completions over https; request ceiling and a
persistent ledger; stops on the first HTTP error or exception; a case already
recorded is never replayed. Covers grounding and comparison cases only (the
product writer + reviewer path). Other categories need the full service path.
Usage: GROQ_API_KEY from the vault file named below; python run_groq.py LEDGER_DIR CEILING [MAX_CASES]
"""
import asyncio,fcntl,json,os,pathlib,sys,time,logging
import httpx
HERE=pathlib.Path(__file__).parent
API=pathlib.Path(os.environ.get('EVAL_API_ROOT','/tmp/adl-eval-suite/backend/api'))
sys.path.insert(0,str(API));sys.path.insert(0,str(HERE.parents[1]));os.chdir(API)
import runpy;runpy.run_path(str(API/'tests/conftest.py'))
os.environ.update(TAVILY_API_KEY='',USE_REDIS='false',PROVIDER_CAPACITY_PLAN='free')
os.environ['GROQ_API_KEY']=pathlib.Path(os.environ['GROQ_KEY_FILE']).read_text().strip()
logging.disable(logging.CRITICAL)
DIR=pathlib.Path(sys.argv[1]);DIR.mkdir(mode=0o700,exist_ok=True);CEIL=int(sys.argv[2]);MAXC=int(sys.argv[3]) if len(sys.argv)>3 else 10**9
LEDGER=DIR/'calls.json'
if not LEDGER.exists():LEDGER.write_text(json.dumps({'ceiling':CEIL,'attempts':0,'stopped':False,'events':[],'limits':{}}));os.chmod(LEDGER,0o600)
def mutate(cb):
    with LEDGER.open('r+') as f:
        fcntl.flock(f,fcntl.LOCK_EX);s=json.load(f);cb(s);f.seek(0);f.truncate();json.dump(s,f);f.flush();os.fsync(f.fileno());return s
class Guard(httpx.AsyncBaseTransport):
    def __init__(self):self.inner=httpx.AsyncHTTPTransport(retries=0)
    async def handle_async_request(self,r):
        if r.url.scheme!='https' or r.url.host!='api.groq.com' or r.method!='POST' or not r.url.path.endswith('/chat/completions'):raise RuntimeError('unapproved_destination')
        def reserve(s):
            if s['stopped'] or s['attempts']>=s['ceiling']:raise RuntimeError('stopped_or_ceiling')
            s['attempts']+=1;s['events'].append({'n':s['attempts'],'t':time.time()})
        mutate(reserve)
        try:
            resp=await self.inner.handle_async_request(r)
            def rec(s):
                s['events'][-1]['status']=resp.status_code
                s['limits']={k:v for k,v in resp.headers.items() if k.lower().startswith('x-ratelimit')}
                if resp.status_code>=400:s['stopped']=True
            mutate(rec);return resp
        except BaseException:
            mutate(lambda s:s.update(stopped=True));raise
    async def aclose(self):await self.inner.aclose()
async def main():
    from groq import AsyncGroq
    from app.services.free_llm_service import FreeLLMService
    sys.path.insert(0,str(HERE));from fixtures import cards
    svc=FreeLLMService()
    svc._client=AsyncGroq(api_key=os.environ['GROQ_API_KEY'],base_url='https://api.groq.com',max_retries=0,http_client=httpx.AsyncClient(transport=Guard(),trust_env=False,timeout=30))
    cs=cards();cases=[c for c in json.load(open(HERE/'cases.json'))['cases'] if c['cat'] in ('grounding','comparison') and c['id'].split('-')[1].isdigit() and int(c['id'].split('-')[1])>=100][:MAXC]
    out=DIR/'responses.json';resp=json.loads(out.read_text()) if out.exists() else {}
    for c in cases:
        if c['id'] in resp:continue
        if json.loads(LEDGER.read_text())['stopped']:print('stopped');break
        names=c.get('products') or [c['product']]
        try:
            r=await svc.filter_and_recommend(c['question'],[cs[n] for n in names])
            resp[c['id']]={'text':(r.intro_message or '')+' '+' '.join((r.reasoning or {}).values()),'product_ids':list(r.selected_ids)}
        except BaseException as e:
            resp[c['id']]={'text':'','product_ids':[],'error':type(e).__name__}
            mutate(lambda s:s.update(stopped=True))
        out.write_text(json.dumps(resp,indent=1));os.chmod(out,0o600)
    await svc._client.close()
try:asyncio.run(main())
finally:os.environ.pop('GROQ_API_KEY',None)
