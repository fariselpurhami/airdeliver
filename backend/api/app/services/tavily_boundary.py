"""Bounded async search transport. Results are untrusted source data, not facts."""
import asyncio
import json
import httpx

MAX_BYTES=131072

async def search(query, key, *, max_results=3, depth='advanced', raw=True, timeout=6):
    if not isinstance(query,str) or not query.strip() or len(query)>650:
        raise ValueError('invalid_search_query')
    if not isinstance(key,str) or not key.strip():raise ValueError('missing_search_key')
    if type(max_results) is not int or not 1<=max_results<=3:raise ValueError('invalid_result_limit')
    async with asyncio.timeout(timeout):
        async with httpx.AsyncClient(timeout=timeout,follow_redirects=False) as client:
            async with client.stream('POST','https://api.tavily.com/search',json={
                'api_key':key,'query':query,'max_results':max_results,'search_depth':depth,
                'include_answer':False,'include_raw_content':raw,'topic':'general'}) as response:
                response.raise_for_status()
                data=bytearray()
                async for chunk in response.aiter_bytes():
                    data.extend(chunk)
                    if len(data)>MAX_BYTES:raise ValueError('search_response_too_large')
    result=json.loads(data)
    if not isinstance(result,dict) or not isinstance(result.get('results',[]),list):
        raise ValueError('invalid_search_response')
    return result


def source_rows(result, *, limit=3, text_limit=6000):
    from app.services.product_knowledge_service import allowed_url
    rows=[];seen=set()
    if not isinstance(result,dict) or not isinstance(result.get('results',[]),list):
        raise ValueError('invalid_search_response')
    for item in result.get('results',[])[:limit]:
        if not isinstance(item,dict):continue
        url=item.get('url');text=item.get('raw_content') or item.get('content')
        if not isinstance(url,str) or not allowed_url(url) or url in seen:continue
        if not isinstance(text,str) or not text.strip():continue
        seen.add(url)
        rows.append({'url':url,'text':' '.join(text.split())[:text_limit]})
    return rows
