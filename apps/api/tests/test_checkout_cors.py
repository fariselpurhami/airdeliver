from fastapi.testclient import TestClient
from app.main import app


def test_checkout_preflight_allows_real_browser_origin_and_required_headers():
    response=TestClient(app).options('/api/v1/ai-ordering/checkout/confirm',headers={
        'Origin':'http://localhost:3000','Access-Control-Request-Method':'POST',
        'Access-Control-Request-Headers':'authorization,content-type,idempotency-key,x-requested-with'})
    assert response.status_code==200
    assert response.headers['access-control-allow-origin']=='http://localhost:3000'
