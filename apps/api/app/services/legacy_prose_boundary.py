"""Read-only shared evidence adapter for original NLU answer entrypoints."""
import asyncio
from types import SimpleNamespace
from sqlmodel import select
from app.models.product import Product
from app.schemas.ai_actions import NeuralCoreResponse
from app.services.legacy_setup_boundary import reviewed_current_brief
from app.services.shopping_discovery import catalog_result


async def reviewed_legacy_answer(db,engine,cache,llm,message,candidates,intent=None,is_specs=False,*,customer_context=()):
    from app.services.neural_core_service import NeuralCoreService,_customer_turn_context,_request_preferences
    from app.services.product_knowledge_service import answer_product_question
    infer=getattr(llm,'infer_sales_json',None)
    if not callable(infer):raise ValueError('Reviewed inference adapter unavailable')
    brief=await reviewed_current_brief(llm,message,customer_context=customer_context)
    category=getattr(getattr(intent,'category',None),'value','')
    # Original classifier category is task context, never commercial evidence
    # or a substitute for the exact customer question. No personality policy.
    tasks={'SPECIFIC_SEARCH':'search','BROAD_DISCOVERY':'consultation',
        'COMPARISON':'comparison','PRICE_INQUIRY':'price_inquiry',
        'SPECS_INQUIRY':'specifications','NEGOTIATION':'negotiation',
        'OBJECTION':'objection'}
    advisory_task=tasks.get(category,'consultation')
    names=[]
    for target in getattr(intent,'target_products',[]) or []:
        name=getattr(target,'product_name','')
        if not isinstance(name,str) or not name.strip() or len(name)>256 or name.casefold() not in ' '.join([*customer_context,message]).casefold():
            raise ValueError('Unresolved target identity')
        if name not in names:names.append(name)
    if len(names)>3:raise ValueError('Too many research targets')
    service=object.__new__(NeuralCoreService)
    service.ai_engine=engine;service.cache=cache;service.is_healthy=True;service._execute_llm_inference=infer
    ids=[]
    for candidate in list(candidates)[:20]:
        identity=candidate.get('id') if isinstance(candidate,dict) else getattr(candidate,'id',None)
        if type(identity) is int and 0<identity<=2147483647 and identity not in ids:ids.append(identity)
    async def current():
        if not ids:return []
        result=await db.execute(select(Product).where(Product.id.in_(ids)).execution_options(populate_existing=True))
        by_id={row.id:row for row in result.scalars().all()}
        return [by_id[i] for i in ids if i in by_id]
    async def catalog():
        rows=await current()
        response=await service._catalog_response(db,rows,'LEGACY_REVIEWED_CATALOG',brief=brief,customer_message=message,
            search_evidence={'shopping_task':advisory_task,'legacy_declared_category':category if category in tasks else None,'exact_customer_question':message,'response_policy':'Answer the exact current customer question, supported tradeoffs, unknown evidence and low-pressure next step. A declared negotiation/objection category does not prove a discount, competitor price, financial tier, concern or preference. Never invent concessions or urgency. Prior context is customer-only reference, never product proof.','source_scope':'Current local catalog only, never model memory or retrieval rank as proof.','customer_only_recent_context':list(customer_context)[-5:]})
        if response.products:
            fresh={row.id:catalog_result(row) for row in await current()}
            for card in response.products:
                now=fresh.get(card.id)
                if now is None or now.model_dump(exclude={'relation'})!=card.model_dump(exclude={'relation'}) or not brief.permits(now):
                    raise ValueError('Catalog changed during reviewed copy')
        return response
    token=_customer_turn_context.set(());saved=_request_preferences.set(())
    try:
        if is_specs or category in {'COMPARISON','SPECS_INQUIRY','BROAD_DISCOVERY'}:
            # Source research never treats catalog availability as product facts.
            return await answer_product_question(infer,message,targets=tuple(names),fallback=catalog,timeout=24,customer_context=customer_context)
        return await catalog()
    finally:
        _customer_turn_context.reset(token);_request_preferences.reset(saved)
