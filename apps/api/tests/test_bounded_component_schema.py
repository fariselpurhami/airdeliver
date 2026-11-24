"""Wire schemas retain dynamic target names only after validated conversion."""
import json
import pytest
from app.services.discovery_planner import SetupPlanWire,parse_setup
from app.services.target_constraint_scope import TargetScopeWire,parse_scope
from app.services.structured_output import strict_schema


def test_setup_wire_preserves_requirements_and_exclusions_without_open_maps():
    value={'components':['laptop','chair'],
           'component_requirements':[{'component':'laptop','features':['16GB RAM']}],
           'component_exclusions':[{'component':'chair','features':['red']}]}
    plan=parse_setup(json.dumps(value))
    assert plan.component_requirements=={'laptop':['16GB RAM']}
    assert plan.component_exclusions=={'chair':['red']}
    assert strict_schema(SetupPlanWire)['additionalProperties'] is False


def test_target_wire_preserves_negative_features_and_empty_assignments():
    assert parse_scope('{"assignments":[{"target":"chair","features":["red"]}]}').assignments=={'chair':['red']}
    assert parse_scope('{"assignments":[]}').assignments=={}
    assert strict_schema(TargetScopeWire)['additionalProperties'] is False


@pytest.mark.parametrize('raw,parser',[
    ({'assignments':[{'target':'chair','features':['red']},{'target':'chair','features':[]}]},parse_scope),
    ({'components':['chair'],'component_requirements':[{'component':'chair','features':[]},{'component':'chair','features':['red']}],'component_exclusions':[]},parse_setup),
    ({'assignments':[{'target':'chair','features':['red'],'unknown':1}]},parse_scope),
])
def test_duplicate_or_untyped_assignments_do_not_silently_overwrite(raw,parser):
    with pytest.raises(ValueError):parser(json.dumps(raw))


@pytest.mark.asyncio
@pytest.mark.parametrize('kind',['setup','target'])
async def test_actual_planner_and_review_use_native_sdk_schemas_over_local_http(kind):
    import asyncio
    from types import SimpleNamespace
    from groq import AsyncGroq
    from app.services.neural_core_service import NeuralCoreService
    from app.services.discovery_planner import plan_setup
    from app.services.target_constraint_scope import assign_target_scope
    requests=[]
    bodies=([
        {'components':['laptop','chair'],
         'component_requirements':[{'component':'laptop','features':['16GB RAM']}],
         'component_exclusions':[{'component':'chair','features':['red']}]},
        {'appropriate':True,'no_invented_products':True},
    ] if kind=='setup' else [
        {'assignments':[{'target':'chair','features':['red']}]},
        {'explicit_scope':True},
    ])
    async def handle(reader,writer):
        try:
            headers=await reader.readuntil(b'\r\n\r\n')
            size=int(next(line.split(b':',1)[1] for line in headers.split(b'\r\n') if line.lower().startswith(b'content-length:')))
            request=json.loads(await reader.readexactly(size));requests.append(request)
            body=json.dumps({'id':'local','object':'chat.completion','created':1,'model':'openai/gpt-oss-120b',
                             'choices':[{'index':0,'message':{'role':'assistant','content':json.dumps(bodies[len(requests)-1])},'finish_reason':'stop'}]}).encode()
            writer.write(f'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n'.encode()+body)
            await writer.drain()
        finally:
            writer.close();await writer.wait_closed()
    server=await asyncio.start_server(handle,'127.0.0.1',0)
    async with server:
        async with AsyncGroq(api_key='local-not-secret',max_retries=0,base_url=f'http://127.0.0.1:{server.sockets[0].getsockname()[1]}') as client:
            svc=object.__new__(NeuralCoreService);svc.client=client;svc.profile=SimpleNamespace(support_model='openai/gpt-oss-120b')
            if kind=='setup':
                result=await plan_setup(svc._execute_llm_inference,'laptop16GB RAM and chair not red',detailed=True)
                assert result.component_requirements=={'laptop':['16GB RAM']} and result.component_exclusions=={'chair':['red']}
            else:
                result=await assign_target_scope(svc._execute_llm_inference,'chair not red and laptop',['chair','laptop'],['red'],kind='excluded_terms')
                assert result=={'chair':['red']}
    assert len(requests)==2
    assert [r['response_format']['json_schema']['name'] for r in requests]==(['SetupPlanWire','SetupReview'] if kind=='setup' else ['TargetScopeWire','ScopeReview'])
    assert all(r['response_format']['json_schema']['strict'] is True for r in requests)
