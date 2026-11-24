"""Versioned shopping brief and auditable catalog presentation boundary.

No inference output supplies price, stock, product identity or seller evidence.
"""
from decimal import Decimal, InvalidOperation
from typing import Literal
from pydantic import BaseModel, Field
from app.schemas.ai_actions import CatalogResult


class ShoppingBrief(BaseModel):
    version: Literal[1] = 1
    recipient: str | None = Field(default=None,max_length=80)
    occasion: str | None = Field(default=None,max_length=80)
    category: str | None = Field(default=None,max_length=128)
    budget: str | None = Field(default=None,max_length=80)
    budget_max: str | None = Field(default=None,max_length=24)
    budget_currency: str | None = Field(default=None,max_length=3)
    preference: str | None = Field(default=None,max_length=256)
    excluded_terms: list[str] = Field(default_factory=list,max_length=8)
    required_features: list[str] = Field(default_factory=list,max_length=8)

    def grounded(self, message: str) -> 'ShoppingBrief':
        """Retain only literal customer-provided spans, not inferred tastes."""
        haystack=' '.join(message.casefold().split())
        fields={key:value for key,value in self.model_dump().items()
            if key not in {'version','budget_max','budget_currency'} and isinstance(value,str) and value.strip() and ' '.join(value.casefold().split()) in haystack}
        for key in ('excluded_terms','required_features'):
            fields[key]=list(dict.fromkeys(value.strip() for value in getattr(self,key)
                if isinstance(value,str) and 1<len(value)<=128 and ' '.join(value.casefold().split()) in haystack))
        if fields.get('budget') and self.budget_max and self.budget_currency:
            try:
                value=Decimal(self.budget_max)
                source=fields['budget']
                import re
                tokens=re.findall(r'(?<![\w.])\d+(?:\.\d+)?(?![\w.])',source)
                currency=self.budget_currency
                if value.is_finite() and value>0 and any(Decimal(t)==value for t in tokens) and (
                    currency in source or (currency=='USD' and ('$' in source or re.search(r'\b(?:us\s+dollars?|dollars?|usd)\b',source,re.I)))):
                    fields.update(budget_max=str(value),budget_currency=currency)
            except InvalidOperation:pass
        return ShoppingBrief(**fields)

    def permits(self,card: CatalogResult) -> bool:
        import re
        # Allow typographic spaces between literal characters, but require
        # lexical boundaries. 'red' is not 'infrared',16GB is not116GB.
        evidence=' '.join([card.name,card.category or '',*card.catalog_specs.keys(),*card.catalog_specs.values()]).casefold()
        def present(term):
            from app.services.capacity_evidence import supported_capacity
            capacity=supported_capacity(term,card.catalog_specs,card.name)
            if capacity is not None:return capacity
            chars=re.sub(r'\s+','',str(term).casefold())
            return bool(chars and re.search(r'(?<!\w)'+r'\s*'.join(re.escape(c) for c in chars)+r'(?!\w)',evidence))
        if any(present(term) for term in self.excluded_terms):return False
        # No semantic unit/magnitude or attribute inference.
        if any(not present(term) for term in self.required_features):return False
        if self.budget_max is None:return True
        return (card.currency==self.budget_currency and card.price is not None and
                Decimal(card.price)<=Decimal(self.budget_max))



def catalog_result(product) -> CatalogResult | None:
    pid=getattr(product,'id',None)
    name=getattr(product,'name',None)
    if type(pid) is not int or pid<=0 or not isinstance(name,str) or not name.strip():return None
    if not getattr(product,'is_active',False):return None
    attrs=getattr(product,'attributes',{}) or {}
    if not isinstance(attrs,dict):attrs={}
    sku=getattr(product,'sku','') or ''
    demo=(attrs.get('_seed_dataset')=='airdeliver-demo-v1' or sku.startswith('ADL-DEMO-v1-'))
    try:
        cost=Decimal(str(product.price));currency=product.currency
        valid=cost.is_finite() and cost>=0 and isinstance(currency,str) and len(currency)==3 and currency.isalpha() and currency.isupper()
    except (AttributeError,InvalidOperation,TypeError,ValueError):valid=False
    quantity=getattr(product,'inventory',None)
    stock=('demo' if demo else 'local_in_stock' if type(quantity) is int and quantity>0 else
           'local_out_of_stock' if quantity==0 else 'unverified')
    return CatalogResult(id=pid,name=name,sku=sku,category=getattr(product,'category','uncategorized'),
        price=str(cost) if valid else None,currency=currency if valid else None,
        price_status='listed' if valid else 'unknown',image=getattr(product,'image',None),
        attributes={'_seed_dataset':'airdeliver-demo-v1'} if demo else {},
        catalog_specs={str(k)[:64]:str(v)[:256] for k,v in list(attrs.items())[:32] if isinstance(k,str) and not k.startswith('_') and isinstance(v,(str,int,float,bool))},
        evidence_kind='seeded_demo' if demo else 'local_catalog',stock_status=stock,
        availability_note=('Demo catalog. Price and stock are synthetic, not a merchant offer.' if demo else
            'Local catalog lists stock. Merchant availability, reservation and delivery are not verified.' if stock=='local_in_stock' else
            'Local catalog lists no stock. Merchant availability is not verified.' if stock=='local_out_of_stock' else
            'Stock and merchant availability are not verified.'))
