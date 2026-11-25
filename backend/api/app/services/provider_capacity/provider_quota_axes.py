"""Independent optional quota axes, atomically checked with the shared TPM guard.

Limits are owner configuration, never inferred from a plan or response text.
Sliding Redis windows are conservative; unknown attempts remain reserved.
"""
AXES=(('RPM',60,'requests'),('RPD',86400,'requests'),('TPD',86400,'total'),
      ('ITPM',60,'input'),('OTPM',60,'output'))

# Added to the original script before any debit/lock write. All keys share its
# model hash tag. Rejection never partly consumes another quota dimension.
CHECK_AXES="""
local requests=redis.call('GET',KEYS[5])
if requests and tonumber(requests)<1 then return -1 end
for i=1,5 do
 local k=KEYS[5+i]
 local limit=tonumber(ARGV[6+(i-1)*3])
 local window=tonumber(ARGV[7+(i-1)*3])
 local amount=tonumber(ARGV[8+(i-1)*3])
 if limit>0 then
  local sumkey=KEYS[10+i]
  local expired=redis.call('ZRANGEBYSCORE',k,'-inf',now-window,'LIMIT',0,128)
  local stored=redis.call('GET',sumkey)
  -- An evicted accumulator must never turn existing reservations into zero.
  if not stored and redis.call('ZCARD',k)>0 then return -1 end
  local total=tonumber(stored or '0')
  for _,v in ipairs(expired) do
   total=total-tonumber(string.match(v,':(%d+)$'))
   redis.call('ZREM',k,v)
  end
  redis.call('SET',sumkey,math.max(0,total),'EX',window+60)
  -- Bounded cleanup per request. A long idle backlog fails closed while
  -- later attempts drain it; never block Redis scanning a full day of traffic.
  if redis.call('ZCOUNT',k,'-inf',now-window)>0 then return -1 end
  if total<0 then return -1 end
  if total+amount>limit then return -1 end
 end
end
"""
DEBIT_AXES="""
if requests then redis.call('DECR',KEYS[5]) end
for i=1,5 do
 local limit=tonumber(ARGV[6+(i-1)*3])
 local window=tonumber(ARGV[7+(i-1)*3])
 local amount=tonumber(ARGV[8+(i-1)*3])
 if limit>0 then
  redis.call('ZADD',KEYS[5+i],now,ARGV[1]..':'..amount)
  redis.call('EXPIRE',KEYS[5+i],window+60)
  redis.call('INCRBY',KEYS[10+i],amount)
  redis.call('EXPIRE',KEYS[10+i],window+60)
 end
end
"""

def reservation_script(original):
    marker="if observed then redis.call('DECRBY',KEYS[4],ARGV[3]) end"
    assert original.count(marker)==1
    return original.replace(marker,CHECK_AXES+'\n'+marker+'\n'+DEBIT_AXES)


def axis_arguments(settings,input_amount,output_amount):
    values={'requests':1,'input':input_amount,'output':output_amount,'total':input_amount+output_amount}
    args=[]
    for axis,window,kind in AXES:
        limit=getattr(settings,'PROVIDER_'+axis+'_BUDGET',None)
        if limit is not None and (type(limit) is not int or limit<1 or limit>10**9):
            from app.services.shared_provider_admission import SharedProviderBudgetError
            raise SharedProviderBudgetError('invalid_quota_axis')
        args.extend([limit or 0,window,values[kind]])
    return args


async def reconcile_axes(reservation):
    """Actual successful usage replaces estimates only in enabled live entries."""
    if not getattr(reservation,'axis_keys',None):return
    actual={'requests':1,'total':reservation.actual,'input':reservation.usage.get('prompt_tokens'),
            'output':reservation.usage.get('completion_tokens')}
    script="""
local score=redis.call('ZSCORE',KEYS[1],ARGV[1])
if score then
 redis.call('ZREM',KEYS[1],ARGV[1]);redis.call('ZADD',KEYS[1],score,ARGV[2])
 redis.call('INCRBY',KEYS[2],tonumber(ARGV[4])-tonumber(ARGV[3]))
end
return 1
"""
    for (axis,window,kind),key,estimate in zip(AXES,reservation.axis_keys,reservation.axis_estimates):
        value=actual[kind]
        if key and type(value) is int and value>=0:
            await reservation.client.eval(script,2,key,key+':total',reservation.owner+':'+str(estimate),reservation.owner+':'+str(value),estimate,value)
