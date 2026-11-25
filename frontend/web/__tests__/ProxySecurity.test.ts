/** @jest-environment node */
import { NextRequest } from 'next/server';
import { proxy } from '@/proxy';
import { auth } from '@/auth';
jest.mock('@/auth',()=>({auth:jest.fn()}));

const session=jest.mocked(auth) as unknown as ReturnType<typeof jest.fn>;

beforeEach(()=>{session.mockReset();session.mockResolvedValue(null);});

it.each(['/', '/login', '/profile', '/admin', '/productivity'])('sets CSP and all security headers on %s',async(path)=>{
  const response=await proxy(new NextRequest('https://shop.test'+path));
  expect(response.headers.get('x-content-type-options')).toBe('nosniff');
  expect(response.headers.get('x-frame-options')).toBe('DENY');
  const csp=response.headers.get('content-security-policy')||'';
  expect(csp).toContain("object-src 'none'");
  expect(csp).toContain("base-uri 'self'");
  expect(csp).toContain("frame-ancestors 'none'");
  expect(csp).toMatch(/script-src[^;]*'nonce-[A-Za-z0-9+/=]+'/);
  expect(csp).not.toContain("'unsafe-eval'");
});

it('replaces client nonce/CSP and makes a fresh nonce on each document request',async()=>{
 const request=()=>new NextRequest('https://shop.test/',{headers:{'x-nonce':'attacker','Content-Security-Policy':"script-src *"}});
 const a=await proxy(request()),b=await proxy(request());
 const nonce=a.headers.get('x-middleware-request-x-nonce');
 expect(nonce).toBeTruthy();expect(nonce).not.toBe('attacker');
 expect(nonce).not.toBe(b.headers.get('x-middleware-request-x-nonce'));
 expect(a.headers.get('x-middleware-request-content-security-policy')).toBe(a.headers.get('content-security-policy'));
 expect(a.headers.get('cache-control')).toContain('no-store');
});

it('does not bypass authentication on client-selected prefetch header',async()=>{
 const response=await proxy(new NextRequest('https://shop.test/profile',{headers:{'x-middleware-prefetch':'1'}}));
 expect(session).toHaveBeenCalled();expect(response.status).toBe(307);
 expect(response.headers.get('content-security-policy')).toBeTruthy();
});

it.each(['/productivity','/products-secret','/legality'])('does not treat a similar prefix as public: %s',async(path)=>{
 const response=await proxy(new NextRequest('https://shop.test'+path));
 expect(session).toHaveBeenCalled();expect(response.status).toBe(307);
});

it('keeps public product subpaths and enforces administrator role',async()=>{
 expect((await proxy(new NextRequest('https://shop.test/products/7'))).status).toBe(200);
 expect(session).not.toHaveBeenCalled();
 session.mockResolvedValue({user:{role:'customer'}});
 const response=await proxy(new NextRequest('https://shop.test/admin'));
 expect(response.status).toBe(307);expect(response.headers.get('x-frame-options')).toBe('DENY');
});

it('keeps auth failure private and fails closed with security headers',async()=>{
 session.mockRejectedValue(new Error('PRIVATE_PROXY_MARKER'));
 const log=jest.spyOn(console,'error').mockImplementation(()=>{});
 try {
  const response=await proxy(new NextRequest('https://shop.test/profile'));
  expect(response.status).toBe(307);expect(response.headers.get('content-security-policy')).toBeTruthy();
  expect(JSON.stringify(log.mock.calls)).not.toContain('PRIVATE_PROXY_MARKER');
 } finally {log.mockRestore();}
});
