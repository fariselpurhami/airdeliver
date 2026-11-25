"""Currency-separated order payment records, never settlement or net revenue.

Amounts originate in historical float columns. Cast each order to decimal cents
before aggregation; do not claim recovery of precision already lost on write.
"""
from datetime import datetime,timedelta,timezone
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel
from sqlalchemy import Numeric,cast,func,select
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
    rows=(await db.execute(select(currency.label('currency'),bucket.label('bucket'),amount.label('amount'),func.count(Order.id).label('count')).where(
        Order.is_paid.is_(True),Order.paid_at>=start,Order.paid_at<now,valid
    ).group_by(currency,bucket).order_by(currency,bucket))).all()
    groups={}
    for code,instant,value,count in rows:
        entry=groups.setdefault(code,{'currency':code,'amount':Decimal('0.00'),'order_count':0,'buckets':[]})
        entry['amount']+=value;entry['order_count']+=count
        entry['buckets'].append(AmountBucket(starts_at=instant,amount=format(value,'.2f'),order_count=count))
    # Missing timestamps cannot be assigned to a chosen window, so report them as
    # all-time excluded records explicitly, never put them under created_at.
    missing=(await db.execute(select(func.count(Order.id)).where(Order.is_paid.is_(True),Order.paid_at.is_(None)))).scalar_one()
    invalid=(await db.execute(select(func.count(Order.id)).where(Order.is_paid.is_(True),Order.paid_at>=start,Order.paid_at<now,~valid))).scalar_one()
    currencies=[CurrencyPayments(**{**entry,'amount':format(entry['amount'],'.2f')}) for entry in groups.values()]
    return PaymentMetrics(generated_at=now,from_at=start,to_at=now,range=range,currencies=currencies,paid_without_timestamp=missing,paid_invalid_amount_or_currency=invalid)
