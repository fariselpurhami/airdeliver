// tests/load/loadtest.k6.js
// AirDeliver API load test (k6). Covers the hot read path, auth, cart, and
// checkout-confirm rate-limit behavior.
//
// Usage:
//   k6 run -e BASE_URL=https://api.airdeliver.com \
//          -e TEST_EMAIL=load@example.com -e TEST_PASSWORD=... tests/load/loadtest.k6.js
//
// Without credentials it exercises only the public endpoints.
// Stages are conservative; raise VUS/duration for real capacity runs.

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const API = `${BASE_URL}/api/v1`;

const errorRate = new Rate('errors');
const productsTrend = new Trend('products_duration', true);

export const options = {
  scenarios: {
    // Hot read path: anonymous product browsing.
    browse: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '1m', target: 50 },
        { duration: '3m', target: 50 },
        { duration: '1m', target: 200 },
        { duration: '3m', target: 200 },
        { duration: '1m', target: 0 },
      ],
      exec: 'browse',
    },
    // Authenticated cart/checkout churn (only when creds are provided).
    checkout: {
      executor: 'constant-vus',
      vus: 20,
      duration: '5m',
      exec: 'checkoutFlow',
      startTime: '1m',
    },
  },
  thresholds: {
    // SLOs the platform should hold at this load.
    errors: ['rate<0.01'],
    products_duration: ['p(95)<800'],
    http_req_failed: ['rate<0.01'],
  },
};

export function browse() {
  const page = 1 + Math.floor(Math.random() * 5);
  const res = http.get(`${API}/products/?page=${page}&limit=20`, { tags: { name: 'products' } });
  productsTrend.add(res.timings.duration);
  const ok = check(res, { 'products 200': (r) => r.status === 200 });
  errorRate.add(!ok);
  sleep(0.5 + Math.random());
}

function login() {
  const payload = `username=${encodeURIComponent(__ENV.TEST_EMAIL)}&password=${encodeURIComponent(__ENV.TEST_PASSWORD)}`;
  const res = http.post(`${API}/auth/token`, payload, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    tags: { name: 'login' },
  });
  if (res.status !== 200) return null;
  return res.json('access_token');
}

export function checkoutFlow() {
  if (!__ENV.TEST_EMAIL || !__ENV.TEST_PASSWORD) {
    sleep(5);
    return;
  }
  const token = login();
  if (!token) {
    errorRate.add(1);
    sleep(5);
    return;
  }
  const auth = { headers: { Authorization: `Bearer ${token}` }, tags: { name: 'authed' } };

  const sync = http.post(`${API}/ai-ordering/cart/sync`, null, auth);
  check(sync, { 'cart sync accepted': (r) => r.status === 202 });

  const ticket = http.post(`${API}/ai-ordering/ticket`, null, auth);
  check(ticket, { 'ticket ok or limited': (r) => r.status === 200 || r.status === 429 });

  sleep(2 + Math.random() * 3);
}
