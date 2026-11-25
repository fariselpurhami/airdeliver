"""Currency-separated order payment records, never settlement or net revenue.

Amounts originate in historical float columns. Cast each order to decimal cents
before aggregation; do not claim recovery of precision already lost on write.
"""
from datetime import datetime,timedelta,timezone
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel
from sqlalchemy import Numeric,cast,func,select,literal,union_all,DateTime
from app.models.order import Order

Range=Literal['1H','24H','7D','30D']
WINDOWS={'1H':timedelta(hours=1),'24H':timedelta(hours=24),'7D':timedelta(days=7),'30D':timedelta(days=30)}
class AmountBucket(BaseModel):
    starts_at:datetime
    amount:str
    order_count:int
class CurrencyPayments(BaseModel):
    currency:str
    amount:str
    order_count:int
    buckets:list[AmountBucket]
class PaymentMetrics(BaseModel):
    generated_at:datetime
    from_at:datetime
    to_at:datetime
    timezone:Literal['UTC']='UTC'
    range:Range
    definition:Literal['recorded_paid_order_gross']='recorded_paid_order_gross'
    complete:bool=True
    source:Literal['orders_paid_at']='orders_paid_at'
    currencies:list[CurrencyPayments]
    paid_without_timestamp:int
    paid_invalid_amount_or_currency:int
    note:str='Recorded paid order totals, not settled funds, net revenue or refunds. Historical amounts were stored as floats; decimal aggregation cannot restore earlier precision.'

async def payment_metrics(db,range:Range,*,now=None):
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None:raise ValueError('UTC-aware metric instant required')
    now=now.astimezone(timezone.utc);start=now-WINDOWS[range]
    # Currency is never guessed, converted or replaced with USD.
    currency=func.upper(Order.currency)
    valid_currency=currency.op('~')('^[A-Z]{3}$')
    valid_amount=(Order.total_price>=0)&(Order.total_price<Decimal('1000000000000000000'))
    valid=valid_currency&valid_amount
    # One grouped query covers the complete window, not the last page of orders.
    # PostgreSQL timestamptz truncation is explicitly UTC, independent of session TZ.
    unit='minute' if range=='1H' else 'hour' if range=='24H' else 'day'
    bucket=func.date_trunc(unit,Order.paid_at,'UTC')
    amount=func.sum(cast(Order.total_price,Numeric(38,2)))
    grouped=select(currency.label('currency'),bucket.label('bucket'),amount.label('amount'),func.count(Order.id).label('count')).where(
        Order.is_paid.is_(True),Order.paid_at>=start,Order.paid_at<now,valid
    ).group_by(currency,bucket)
    def counter(tag,conditions):
        return select(literal(tag),cast(literal(None),DateTime(timezone=True)),cast(literal(None),Numeric(38,2)),func.count(Order.id)).where(*conditions)
    # One SQL statement gives groups and exclusion counters the same MVCC
    # snapshot, even when webhooks commit during this report. No transaction
    # isolation change is applied to the caller's authentication session.
    statement=union_all(grouped,
        counter('__missing__',[Order.is_paid.is_(True),Order.paid_at.is_(None)]),
        counter('__invalid__',[Order.is_paid.is_(True),Order.paid_at>=start,Order.paid_at<now,~valid]))
    rows=(await db.execute(statement)).all()
    groups={};missing=invalid=0
    for code,instant,value,count in rows:
        if code=='__missing__':missing=count;continue
        if code=='__invalid__':invalid=count;continue
        entry=groups.setdefault(code,{'currency':code,'amount':Decimal('0.00'),'order_count':0,'buckets':[]})
        entry['amount']+=value;entry['order_count']+=count
        entry['buckets'].append(AmountBucket(starts_at=instant,amount=format(value,'.2f'),order_count=count))
    for entry in groups.values():entry['buckets'].sort(key=lambda b:b.starts_at)
    groups=dict(sorted(groups.items()))
    currencies=[CurrencyPayments(**{**entry,'amount':format(entry['amount'],'.2f')}) for entry in groups.values()]
    return PaymentMetrics(generated_at=now,from_at=start,to_at=now,range=range,currencies=currencies,paid_without_timestamp=missing,paid_invalid_amount_or_currency=invalid)
