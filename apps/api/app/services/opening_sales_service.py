"""Model-written opening and Insight, using the shared evidence/review boundary."""
from app.services.sales_response_service import SalesResponseService, SalesResponseRequest
from app.services.shopping_discovery import ShoppingBrief, catalog_result, opening_card_eligible, demo_preview_enabled


async def write_opening(llm, products, row_type, *, timeout=12.0):
    cards=[]
    for product in products[:5]:
        card=catalog_result(product)
        if opening_card_eligible(card):
            cards.append(card)
    if not cards:
        raise ValueError('No eligible current opening cards')
    result=await SalesResponseService(llm.infer_sales_json,provider_ready=True,timeout=timeout).respond(
        SalesResponseRequest(message='Introduce this catalog selection and provide a useful shopping Insight.',
            products=tuple(cards),brief=ShoppingBrief(),mode='catalog_results',intent='OPENING_INSIGHT',
            evidence={'sales_intent':'OPENING_INSIGHT','row_pool':row_type,
                'customer_preferences':'unknown','customer_language':'not recorded; use concise English',
                'row_labels_are_not_claims':True,'sales_or_trend_or_discount_evidence':False,
                'demo_preview':demo_preview_enabled(),
                'demo_rule':'Any seeded_demo card is synthetic test data, not an offer. Do not claim real stock, popularity, discounts or merchant availability.'}))
    if result.response_kind=='system_notice':
        raise ValueError('Opening copy withheld')
    parts=result.text.split('\n\n')
    if len(parts)!=2 or any(not p.strip() for p in parts):
        raise ValueError('Opening requires separate introduction and Insight')
    return tuple(p.strip() for p in parts)
