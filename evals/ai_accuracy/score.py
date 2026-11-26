"""Score recorded responses against cases.json. No model judge, no network.
Usage: python score.py responses.json  (map case id -> {text, product_ids})
Reports pass rate per category and overall with Wilson 95% interval and n."""
import json,re,sys,math,collections
def wilson(k,n,z=1.96):
    if n==0:return (0.0,0.0)
    p=k/n;d=1+z*z/n;c=p+z*z/(2*n);m=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))
    return ((c-m)/d,(c+m)/d)
def is_withheld(resp):return resp.get('text','').lstrip().startswith('System notice:')
def check(case,resp):
    t=resp.get('text','');low=t.lower();fails=[]
    ma=case.get('must_any')
    if ma and not any(re.search(p,low) for p in ma):fails.append('missing_required')
    for p in case.get('must_not',[]):
        if re.search(p,low):fails.append('forbidden:'+p)
    if 'max_words' in case and len(t.split())>case['max_words']:fails.append('too_long')
    if 'max_questions' in case and t.count('?')>case['max_questions']:fails.append('too_many_questions')
    if case.get('expects_products') is False and resp.get('product_ids'):fails.append('unexpected_products')
    return fails
def main(path):
    cases=json.load(open(__file__.replace('score.py','cases.json')))['cases'];resp=json.load(open(path))
    by=collections.defaultdict(lambda:[0,0]);missing=0;errs=0;withheld=collections.Counter()
    for c in cases:
        r=resp.get(c['id'])
        if r is None:missing+=1;continue
        if r.get('error'):errs+=1;continue
        if is_withheld(r):withheld[c['cat']]+=1;continue
        by[c['cat']][1]+=1
        if not check(c,r):by[c['cat']][0]+=1
    tk=sum(v[0] for v in by.values());tn=sum(v[1] for v in by.values())
    for cat,(k,n) in sorted(by.items()):print(f'{cat}: {k}/{n} lo,hi={wilson(k,n)[0]:.2f},{wilson(k,n)[1]:.2f}')
    print(f'withheld by safety path (not counted as pass or fail): {dict(withheld)}; runner errors: {errs}')
    print(f'overall: {tk}/{tn} = {100*tk/max(tn,1):.1f}% CI95 {100*wilson(tk,tn)[0]:.1f}-{100*wilson(tk,tn)[1]:.1f}; unscored(missing)={missing}')
if __name__=='__main__':main(sys.argv[1])
