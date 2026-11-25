"""Shopping-only memory with explicit opt-in and canonical PostgreSQL reads.

No inferred personality, financial tier, health, identity or life-event records.
"""
import hashlib
import re
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert
from app.core.config import get_core_settings
from app.models.customer_memory import CustomerMemoryConsent, CustomerShoppingMemory

POLICY_VERSION = 'shopping-v2'
READ_POLICIES=('shopping-v1',POLICY_VERSION)
LONG_TERM_EXPIRY=datetime(9999,12,31,tzinfo=timezone.utc)
RETENTION_DAYS = None
# Deliberately narrow v1 categories. Expanding these requires policy review.
VALUES = {
    'color': {'black','white','blue','red','green','yellow','orange','purple','pink','brown','gray','grey','silver','gold','beige','navy'},
    'material': {'cotton','linen','wool','leather','denim','silk','steel','aluminum','wood','glass','ceramic'},
    'style': {'minimalist','classic','casual','formal','sporty','vintage','modern'},
}


class PreferenceCandidate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    category: Literal['color','material','style']
    value: str = Field(min_length=1,max_length=120)
    evidence: str = Field(min_length=3,max_length=300)


def valid_candidate(raw, source):
    try:
        item=PreferenceCandidate.model_validate(raw)
    except Exception:
        return None
    value=item.value.casefold().strip()
    evidence=item.evidence.casefold().strip()
    if value not in VALUES[item.category] or evidence not in source.casefold():
        return None
    # Exact affirmative statement only; generated inference is not durable fact.
    if not re.search(r'\b(i prefer|i like|i always choose|my favorite|my favourite)\b', evidence):
        return None
    if re.search(r'\b(not|never|don.t|avoid|hate|dislike)\b', evidence):
        return None
    if not re.search(r'\b'+re.escape(value)+r'\b',evidence):
        return None
    return item.category,value


class CustomerMemoryService:
    def __init__(self,db,engine=None):
        self.db=db
        self.engine=engine

    async def enabled(self,user_id):
        if not get_core_settings().CUSTOMER_MEMORY_ENABLED:
            return False
        record=await self.db.get(CustomerMemoryConsent,user_id,populate_existing=True)
        return bool(record and record.enabled and record.policy_version==POLICY_VERSION)

    async def set_consent(self,user_id,enabled):
        statement=insert(CustomerMemoryConsent).values(user_id=user_id,enabled=enabled,policy_version=POLICY_VERSION,changed_at=datetime.now(timezone.utc))
        await self.db.execute(statement.on_conflict_do_update(index_elements=['user_id'],set_={'enabled':enabled,'policy_version':POLICY_VERSION,'changed_at':datetime.now(timezone.utc)}))
        if enabled:
            # Explicit new-policy opt-in upgrades existing unexpired facts only.
            await self.db.execute(update(CustomerShoppingMemory).where(CustomerShoppingMemory.user_id==user_id,CustomerShoppingMemory.expires_at>datetime.now(timezone.utc)).values(expires_at=LONG_TERM_EXPIRY))
        await self.db.commit()

    async def collect(self,user_id,text,llm):
        if not await self.enabled(user_id):return False
        initial=await self.db.get(CustomerMemoryConsent,user_id,populate_existing=True)
        if not initial or not initial.enabled or initial.policy_version!=POLICY_VERSION:return False
        consent_generation=initial.changed_at
        # Provider extraction happens only after consent and never during opt-out.
        if not re.search(r"\b(i prefer|i like|i always choose|my favorite|my favourite)\b",text,flags=re.IGNORECASE):
            return False
        raw=await llm.extract_shopping_preferences(text)
        candidate=valid_candidate(raw,text)
        if not candidate:return False
        category,value=candidate
        fingerprint=hashlib.sha256(f'{category}:{value}'.encode()).hexdigest()
        now=datetime.now(timezone.utc)
        # Lock consent row so revocation cannot race with a late memory commit.
        consent=(await self.db.execute(select(CustomerMemoryConsent).where(CustomerMemoryConsent.user_id==user_id).with_for_update().execution_options(populate_existing=True))).scalar_one_or_none()
        if not consent or not consent.enabled or consent.policy_version!=POLICY_VERSION or consent.changed_at!=consent_generation:return False
        await self.db.execute(delete(CustomerShoppingMemory).where(CustomerShoppingMemory.user_id==user_id,CustomerShoppingMemory.expires_at<=now))
        statement=insert(CustomerShoppingMemory).values(user_id=user_id,category=category,value=value,fingerprint=fingerprint,created_at=now,expires_at=LONG_TERM_EXPIRY)
        await self.db.execute(statement.on_conflict_do_update(constraint='uq_customer_memory_fact',set_={'expires_at':LONG_TERM_EXPIRY}))
        await self.db.commit()
        return True

    async def recall(self,user_id,limit=5):
        if not get_core_settings().CUSTOMER_MEMORY_ENABLED:return []
        now=datetime.now(timezone.utc)
        # Expired rows are never eligible, even before physical purge.
        rows=(await self.db.execute(select(CustomerShoppingMemory).join(CustomerMemoryConsent,CustomerMemoryConsent.user_id==CustomerShoppingMemory.user_id).where(CustomerShoppingMemory.user_id==user_id,CustomerShoppingMemory.expires_at>now,CustomerMemoryConsent.policy_version.in_(READ_POLICIES)).order_by(CustomerShoppingMemory.created_at.desc()).limit(min(max(limit,0),20)))).scalars().all()
        return [f'Customer explicitly prefers {row.category}: {row.value}' for row in rows if row.value in VALUES.get(row.category,set())]

    async def export(self,user_id):
        consent=await self.db.get(CustomerMemoryConsent,user_id,populate_existing=True)
        rows=(await self.db.execute(select(CustomerShoppingMemory).where(CustomerShoppingMemory.user_id==user_id,CustomerShoppingMemory.expires_at>datetime.now(timezone.utc)))).scalars().all()
        return {'policy_version':POLICY_VERSION,'enabled':bool(consent and consent.enabled and consent.policy_version==POLICY_VERSION),'retention_days':RETENTION_DAYS,'retention':'Until you erase saved preferences. Older unrenewed records retain their original expiry.','learning_only_toggle':True,
                'preferences':[{'category':r.category,'value':r.value,'created_at':r.created_at.isoformat(),'expires_at':r.expires_at.isoformat()} for r in rows]}

    async def erase_preferences(self,user_id):
        now=datetime.now(timezone.utc)
        statement=insert(CustomerMemoryConsent).values(user_id=user_id,enabled=False,policy_version=POLICY_VERSION,changed_at=now)
        await self.db.execute(statement.on_conflict_do_update(index_elements=['user_id'],set_={'enabled':False,'policy_version':POLICY_VERSION,'changed_at':now}))
        await self.db.execute(delete(CustomerShoppingMemory).where(CustomerShoppingMemory.user_id==user_id))
        await self.db.commit()

    async def purge_expired(self):
        await self.db.execute(delete(CustomerShoppingMemory).where(CustomerShoppingMemory.expires_at<=datetime.now(timezone.utc)))
        await self.db.commit()

    # Historical source retained dormant for additive restoration review.
    async def _legacy_90_day_set_consent(self,user_id,enabled):
        statement=insert(CustomerMemoryConsent).values(user_id=user_id,enabled=enabled,policy_version=POLICY_VERSION,changed_at=datetime.now(timezone.utc))
        await self.db.execute(statement.on_conflict_do_update(index_elements=['user_id'],set_={'enabled':enabled,'policy_version':POLICY_VERSION,'changed_at':datetime.now(timezone.utc)}))
        if not enabled:
            await self.db.execute(delete(CustomerShoppingMemory).where(CustomerShoppingMemory.user_id==user_id))
        await self.db.commit()

    async def _legacy_90_day_recall(self,user_id,limit=5):
        if not await self.enabled(user_id):return []
        now=datetime.now(timezone.utc)
        # Expired rows are never eligible, even before physical purge.
        rows=(await self.db.execute(select(CustomerShoppingMemory).join(CustomerMemoryConsent,CustomerMemoryConsent.user_id==CustomerShoppingMemory.user_id).where(CustomerShoppingMemory.user_id==user_id,CustomerShoppingMemory.expires_at>now,CustomerMemoryConsent.enabled.is_(True),CustomerMemoryConsent.policy_version==POLICY_VERSION).order_by(CustomerShoppingMemory.created_at.desc()).limit(min(max(limit,0),20)))).scalars().all()
        return [f'Customer explicitly prefers {row.category}: {row.value}' for row in rows if row.value in VALUES.get(row.category,set())]

    async def _legacy_90_day_export(self,user_id):
        consent=await self.db.get(CustomerMemoryConsent,user_id,populate_existing=True)
        rows=(await self.db.execute(select(CustomerShoppingMemory).where(CustomerShoppingMemory.user_id==user_id,CustomerShoppingMemory.expires_at>datetime.now(timezone.utc)))).scalars().all()
        return {'policy_version':POLICY_VERSION,'enabled':bool(consent and consent.enabled),'retention_days':RETENTION_DAYS,
                'preferences':[{'category':r.category,'value':r.value,'created_at':r.created_at.isoformat(),'expires_at':r.expires_at.isoformat()} for r in rows]}
