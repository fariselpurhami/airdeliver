"""Installed SDK over real local HTTP sockets, not recorded provider responses."""
import asyncio
import json
from types import SimpleNamespace

import pytest
from groq import AsyncGroq, BadRequestError
from app.services.structured_output import strict_schema, response_format, infer_schema
from app.services.neural_core_service import NeuralCoreService, RouterDecision
from app.services.product_knowledge_service import SpecDraft, SourceReview
from app.services.shopping_copy import ShoppingDraft, GroundingReview
from app.services.query_rewrite import QueryReview
from app.services.constraint_continuity import ReplacementReview
from app.services.discovery_planner import SetupReview, SetupPlan
from app.services.target_constraint_scope import ScopeReview, TargetScope
from app.services.legacy_setup_boundary import BriefReview
from app.services.shopping_discovery import ShoppingBrief

SCHEMAS = [RouterDecision, SpecDraft, SourceReview, ShoppingDraft, GroundingReview,
           QueryReview, ReplacementReview, SetupReview, ScopeReview, BriefReview,
           ShoppingBrief]


@pytest.mark.parametrize('model', SCHEMAS)
def test_provider_schema_closes_every_object_and_requires_properties(model):
    schema = strict_schema(model)

    def check(node):
        if isinstance(node, dict):
            assert 'default' not in node
            if node.get('type') == 'object':
                assert node['additionalProperties'] is False
                assert set(node['required']) == set(node['properties'])
            for value in node.values():
                check(value)
        elif isinstance(node, list):
            for value in node:
                check(value)

    check(schema)
    assert response_format('openai/gpt-oss-120b', model)['json_schema']['strict'] is True
    assert response_format('unverified-model', model) == {'type': 'json_object'}


@pytest.mark.parametrize('model', [SetupPlan, TargetScope])
def test_open_maps_are_not_silently_closed_or_advertised_constrained(model):
    with pytest.raises(ValueError, match='Open dictionary'):
        strict_schema(model)


@pytest.mark.asyncio
@pytest.mark.parametrize('schema', SCHEMAS)
@pytest.mark.parametrize('status', [200, 400])
async def test_installed_sdk_real_http_stage_schema_no_silent_400_fallback(schema, status):
    requests = []

    async def handle(reader, writer):
        try:
            headers = await reader.readuntil(b'\r\n\r\n')
            size = int(next(line.split(b':', 1)[1] for line in headers.split(b'\r\n')
                            if line.lower().startswith(b'content-length:')))
            requests.append(json.loads(await reader.readexactly(size)))
            payload = ({'id': 'local-contract', 'object': 'chat.completion',
                        'created': 1, 'model': 'openai/gpt-oss-120b',
                        'choices': [{'index': 0, 'message': {'role': 'assistant',
                                     'content': '{"local_contract":true}'},
                                     'finish_reason': 'stop'}]}
                       if status == 200 else {'error': {'message': 'local failure',
                                               'type': 'invalid_request_error'}})
            body = json.dumps(payload).encode()
            writer.write(f'HTTP/1.1 {status} Contract\r\nContent-Type: application/json\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n'.encode() + body)
            await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    server = await asyncio.start_server(handle, '127.0.0.1', 0)
    port = server.sockets[0].getsockname()[1]
    async with server:
        async with AsyncGroq(api_key='local-not-a-secret', max_retries=0,
                             base_url=f'http://127.0.0.1:{port}') as client:
            svc = object.__new__(NeuralCoreService)
            svc.client = client
            svc.profile = SimpleNamespace(support_model='openai/gpt-oss-120b')
            call = infer_schema(svc._execute_llm_inference,
                                [{'role': 'user', 'content': 'local contract'}], schema)
            if status == 400:
                with pytest.raises(BadRequestError):
                    await call
            else:
                assert await call == '{"local_contract":true}'
    assert len(requests) == 1
    wire = requests[0]['response_format']
    assert wire['type'] == 'json_schema' and wire['json_schema']['strict'] is True
    assert wire['json_schema']['name'] == schema.__name__


@pytest.mark.asyncio
async def test_legacy_sales_adapter_preserves_schema_through_real_http():
    from app.services.free_llm_service import FreeLLMService
    requests = []

    async def handle(reader, writer):
        try:
            headers = await reader.readuntil(b'\r\n\r\n')
            size = int(next(line.split(b':', 1)[1] for line in headers.split(b'\r\n')
                            if line.lower().startswith(b'content-length:')))
            requests.append(json.loads(await reader.readexactly(size)))
            body = json.dumps({'id': 'local-legacy', 'object': 'chat.completion',
                               'created': 1, 'model': 'openai/gpt-oss-120b',
                               'choices': [{'index': 0, 'message': {'role': 'assistant',
                                'content': '{"supported":true,"exact_model":true,"product_information_only":true}'},
                                'finish_reason': 'stop'}]}).encode()
            writer.write(f'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n'.encode() + body)
            await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    server = await asyncio.start_server(handle, '127.0.0.1', 0)
    async with server:
        async with AsyncGroq(api_key='local-not-a-secret', max_retries=0,
                             base_url=f'http://127.0.0.1:{server.sockets[0].getsockname()[1]}') as client:
            # Test the unchanged production completion method with its actual
            # config fields, no injected inference implementation.
            service = object.__new__(FreeLLMService)
            service.models = SimpleNamespace(brain_model='openai/gpt-oss-120b')
            service._client = client
            service.limits = SimpleNamespace(llm_timeout_seconds=5, retries=0)
            service._execution_semaphore = asyncio.Semaphore(1)
            output = await infer_schema(service.infer_sales_json,
                                       [{'role': 'user', 'content': 'local'}], SourceReview)
            assert SourceReview.model_validate_json(output).supported
    assert requests[0]['response_format']['json_schema']['name'] == 'SourceReview'
