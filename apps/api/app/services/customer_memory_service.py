"""Shopping-only memory with explicit opt-in and canonical PostgreSQL reads.

No inferred personality, financial tier, health, identity or life-event records.
"""
import hashlib
import re
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert
from app.core.config import get_core_settings
from app.models.customer_memory import CustomerMemoryConsent, CustomerShoppingMemory

POLICY_VERSION = 'shopping-v3'
READ_POLICIES=('shopping-v1','shopping-v2',POLICY_VERSION)
LONG_TERM_EXPIRY=datetime(9999,12,31,tzinfo=timezone.utc)
RETENTION_DAYS = None
from app.services.shopping_memory_policy import SHOPPING_VALUES, CATEGORIES, DYNAMIC_CATEGORIES, AFFIRMATIVE, NEGATIVE, normalized_value
VALUES=SHOPPING_VALUES
MAX_TURN_CANDIDATES=8


class PreferenceCandidate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    category: str = Field(min_length=1,max_length=32)
    value: str = Field(min_length=1,max_length=120)
    evidence: str = Field(min_length=3,max_length=300)


def valid_candidate(raw, source, catalog_values=None):
    try:item=PreferenceCandidate.model_validate(raw)
    except Exception:return None
    value=normalized_value(item.value)
    evidence=item.evidence.casefold().strip()
    if item.category not in CATEGORIES or not value or not isinstance(source,str):return None
    if evidence not in source.casefold():return None
    allowed=(catalog_values or {}).get(item.category,set()) if item.category in DYNAMIC_CATEGORIES else VALUES.get(item.category,set())
    if value not in allowed:return None
    # A whole affirmative clause is required, not a selected phrase taken out
    # of a negation or somebody else's preference. Reject multi-clause evidence.
    clauses=re.split(r'[.!?;\n]',source.casefold())
    clause=next((c.strip() for c in clauses if evidence in c),None)
    if not clause or not re.match(r'^(i prefer|i like|i always choose|my favorite|my favourite)\b',clause) or not re.search(AFFIRMATIVE,evidence) or re.search(NEGATIVE,clause):return None
    if any(symbol in clause for symbol in ['\"',"'",'`','<','>']):return None
    if re.search(r'\b(ignore|instruction|pretend|system|password|secret|token|diagnosis|diabetes|religion|political|pregnant|disability|health|medicine)\b',clause):return None
    if not re.search(r'(?<!\w)'+re.escape(value)+r'(?!\w)',evidence):return None
    return item.category,value


class CustomerMemoryService:
    def __init__(self,db,engine=None,cache=None):
        self.db=db
        self.engine=engine
        self.cache=cache

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

    async def catalog_values(self):
        from app.models.product import Product
        from app.services.catalog_visibility import real_catalog_predicates
        # Bound extraction context. This is a supported vocabulary, not claims
        # of exhaustive merchant coverage. Hidden products supply no vocabulary.
        products=(await self.db.execute(select(Product.category,Product.attributes).where(*real_catalog_predicates(Product)).order_by(Product.id).limit(2000))).all()
        values={'brand':set(),'product_category':set()}
        for category,attributes in products:
            category=normalized_value(category)
            if category and not re.search(r'\b(health|medical|medicine|religion|political|pregnancy|disability|sexual|adult|therapy)\b',category):values['product_category'].add(category)
            if isinstance(attributes,dict):
                for key,value in attributes.items():
                    if str(key).casefold()=='brand':
                        brand=normalized_value(value)
                        if brand:values['brand'].add(brand)
        return {key:set(sorted(value)[:200]) for key,value in values.items()}

    async def collect(self,user_id,text,llm):
        if not isinstance(text,str) or not 1<=len(text)<=4000 or not await self.enabled(user_id):return False
        initial=await self.db.get(CustomerMemoryConsent,user_id,populate_existing=True)
        if not initial or not initial.enabled or initial.policy_version!=POLICY_VERSION:return False
        consent_generation=initial.changed_at
        if not re.search(AFFIRMATIVE,text,flags=re.IGNORECASE):return False
        catalog=await self.catalog_values()
        broad=getattr(llm,'extract_shopping_preferences_batch',None)
        raw=await broad(text,catalog) if callable(broad) else await llm.extract_shopping_preferences(text)
        if isinstance(raw,dict) and 'preferences' in raw and set(raw)!={'preferences'}:return False
        proposals=raw.get('preferences',[]) if isinstance(raw,dict) and 'preferences' in raw else [raw]
        if not isinstance(proposals,list) or len(proposals)>MAX_TURN_CANDIDATES:return False
        candidates=list(dict.fromkeys(c for item in proposals if (c:=valid_candidate(item,text,catalog))))
        if not candidates:return False
        now=datetime.now(timezone.utc)
        consent=(await self.db.execute(select(CustomerMemoryConsent).where(CustomerMemoryConsent.user_id==user_id).with_for_update().execution_options(populate_existing=True))).scalar_one_or_none()
        if not consent or not consent.enabled or consent.policy_version!=POLICY_VERSION or consent.changed_at!=consent_generation:return False
        if self.cache is not None:
            from app.services.personalization_fence import can_publish
            if not await can_publish(self.cache,user_id):return False
        await self.db.execute(delete(CustomerShoppingMemory).where(CustomerShoppingMemory.user_id==user_id,CustomerShoppingMemory.expires_at<=now))
        for category,value in candidates:
            fingerprint=hashlib.sha256(f'{category}:{value}'.encode()).hexdigest()
            statement=insert(CustomerShoppingMemory).values(user_id=user_id,category=category,value=value,fingerprint=fingerprint,created_at=now,expires_at=LONG_TERM_EXPIRY)
            await self.db.execute(statement.on_conflict_do_update(constraint='uq_customer_memory_fact',set_={'expires_at':LONG_TERM_EXPIRY,'created_at':now}))
        await self.db.commit()
        return True

    async def recall(self,user_id,limit=5):
        if not get_core_settings().CUSTOMER_MEMORY_ENABLED:return []
        now=datetime.now(timezone.utc)
        # Expired rows are never eligible, even before physical purge.
        rows=(await self.db.execute(select(CustomerShoppingMemory).join(CustomerMemoryConsent,CustomerMemoryConsent.user_id==CustomerShoppingMemory.user_id).where(CustomerShoppingMemory.user_id==user_id,CustomerShoppingMemory.expires_at>now,CustomerMemoryConsent.policy_version.in_(READ_POLICIES)).order_by(CustomerShoppingMemory.created_at.desc()).limit(min(max(limit,0),20)))).scalars().all()
        return [f'Customer explicitly prefers {row.category}: {row.value}' for row in rows if (row.value in VALUES.get(row.category,set()) or (row.category in DYNAMIC_CATEGORIES and normalized_value(row.value)==row.value))]

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

    async def _legacy_90_day_collect(self,user_id,text,llm):
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
        statement=insert(CustomerShoppingMemory).values(user_id=user_id,category=category,value=value,fingerprint=fingerprint,created_at=now,expires_at=now+timedelta(days=RETENTION_DAYS))
        await self.db.execute(statement.on_conflict_do_update(constraint='uq_customer_memory_fact',set_={'expires_at':now+timedelta(days=RETENTION_DAYS)}))
        await self.db.commit()
        return True

    async def _legacy_shopping_v2_collect(self,user_id,text,llm):
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
