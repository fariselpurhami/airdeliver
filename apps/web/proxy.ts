import { createHmac, timingSafeEqual } from 'node:crypto';
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

const USER_GATE_COOKIE_NAME = '__Host-airdeliver-gate-user';
const ADMIN_GATE_COOKIE_NAME = '__Host-airdeliver-gate-admin';
const USER_ENTRY_PATH = '/enter';
const ADMIN_ENTRY_PATH = '/admin-enter';
const NOT_FOUND_PATH = '/404';
const TOKEN_QUERY_KEY = 'token';

const PUBLIC_EXACT_ROUTES = new Set<string>([
  USER_ENTRY_PATH,
  ADMIN_ENTRY_PATH,
  NOT_FOUND_PATH,
]);

const PUBLIC_PREFIX_ROUTES: readonly string[] = [
  '/_next',
  '/api/auth',
];

const SECURITY_HEADERS = {
  'x-airdeliver-guard': 'active',
  'x-frame-options': 'DENY',
  'x-content-type-options': 'nosniff',
  'referrer-policy': 'strict-origin-when-cross-origin',
  'strict-transport-security': 'max-age=31536000; includeSubDomains',
  'cross-origin-opener-policy': 'same-origin',
  'cross-origin-resource-policy': 'same-origin',
  'permissions-policy': 'accelerometer=(), autoplay=(), camera=(), display-capture=(), fullscreen=(self), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()',
} as const;

type GateKind = 'user' | 'admin';

type GatePayload = {
  sub: string;
  exp: number;
  kind: GateKind;
};

type VerificationResult =
  | {
      ok: true;
      payload: GatePayload;
    }
  | {
      ok: false;
    };

function applySecurityHeaders(response: NextResponse): NextResponse {
  for (const [key, value] of Object.entries(SECURITY_HEADERS)) {
    response.headers.set(key, value);
  }

  return response;
}

function isPublicRoute(pathname: string): boolean {
  if (PUBLIC_EXACT_ROUTES.has(pathname)) {
    return true;
  }

  for (let index = 0; index < PUBLIC_PREFIX_ROUTES.length; index += 1) {
    if (pathname.startsWith(PUBLIC_PREFIX_ROUTES[index])) {
      return true;
    }
  }

  return false;
}

function createNotFoundRewrite(req: NextRequest): NextResponse {
  const url = new URL(NOT_FOUND_PATH, req.url);
  return applySecurityHeaders(NextResponse.rewrite(url, { status: 404 }));
}

function base64UrlEncodeUtf8(value: string): string {
  return Buffer.from(value, 'utf8').toString('base64url');
}

function base64UrlDecodeUtf8(value: string): string {
  return Buffer.from(value, 'base64url').toString('utf8');
}

function signValue(payloadEncoded: string, secret: string): string {
  return createHmac('sha256', secret).update(payloadEncoded).digest('base64url');
}

function safeStringEqual(left: string, right: string): boolean {
  const leftBuffer = Buffer.from(left, 'utf8');
  const rightBuffer = Buffer.from(right, 'utf8');

  if (leftBuffer.length !== rightBuffer.length) {
    return false;
  }

  return timingSafeEqual(leftBuffer, rightBuffer);
}

function isValidGateKind(value: unknown): value is GateKind {
  return value === 'user' || value === 'admin';
}

function isValidGatePayload(value: unknown): value is GatePayload {
  if (!value || typeof value !== 'object') {
    return false;
  }

  const record = value as Record<string, unknown>;

  return (
    typeof record.sub === 'string' &&
    record.sub.length > 0 &&
    typeof record.exp === 'number' &&
    Number.isInteger(record.exp) &&
    isValidGateKind(record.kind)
  );
}

function parseAndVerifySignedToken(
  rawToken: string,
  secret: string,
  nowEpochSeconds: number,
  expectedKind: GateKind,
): VerificationResult {
  const parts = rawToken.split('.');

  if (parts.length !== 2) {
    return { ok: false };
  }

  const [payloadEncoded, signature] = parts;

  if (payloadEncoded.length === 0 || signature.length === 0) {
    return { ok: false };
  }

  const expectedSignature = signValue(payloadEncoded, secret);

  if (!safeStringEqual(signature, expectedSignature)) {
    return { ok: false };
  }

  let parsedPayload: unknown;

  try {
    parsedPayload = JSON.parse(base64UrlDecodeUtf8(payloadEncoded));
  } catch {
    return { ok: false };
  }

  if (!isValidGatePayload(parsedPayload)) {
    return { ok: false };
  }

  if (parsedPayload.kind !== expectedKind) {
    return { ok: false };
  }

  if (parsedPayload.exp <= nowEpochSeconds) {
    return { ok: false };
  }

  return {
    ok: true,
    payload: parsedPayload,
  };
}

function buildSignedToken(payload: GatePayload, secret: string): string {
  const payloadEncoded = base64UrlEncodeUtf8(JSON.stringify(payload));
  const signature = signValue(payloadEncoded, secret);
  return `${payloadEncoded}.${signature}`;
}

function issueGateCookie(
  response: NextResponse,
  cookieName: string,
  payload: GatePayload,
  secret: string,
): void {
  response.cookies.set({
    name: cookieName,
    value: buildSignedToken(payload, secret),
    httpOnly: true,
    secure: true,
    sameSite: 'lax',
    path: '/',
    expires: new Date(payload.exp * 1000),
  });
}

function createEntryRedirectResponse(
  req: NextRequest,
  payload: GatePayload,
  secret: string,
): NextResponse {
  const destination = new URL('/', req.url);
  const response = applySecurityHeaders(NextResponse.redirect(destination));

  if (payload.kind === 'admin') {
    issueGateCookie(response, ADMIN_GATE_COOKIE_NAME, payload, secret);
  }

  issueGateCookie(
    response,
    USER_GATE_COOKIE_NAME,
    {
      sub: payload.sub,
      exp: payload.exp,
      kind: 'user',
    },
    secret,
  );

  return response;
}

function hasValidGateCookie(
  req: NextRequest,
  cookieName: string,
  secret: string,
  nowEpochSeconds: number,
  expectedKind: GateKind,
): boolean {
  const rawCookie = req.cookies.get(cookieName)?.value;

  if (!rawCookie) {
    return false;
  }

  return parseAndVerifySignedToken(
    rawCookie,
    secret,
    nowEpochSeconds,
    expectedKind,
  ).ok;
}

function hasAdminAccess(
  req: NextRequest,
  secret: string,
  nowEpochSeconds: number,
): boolean {
  return hasValidGateCookie(
    req,
    ADMIN_GATE_COOKIE_NAME,
    secret,
    nowEpochSeconds,
    'admin',
  );
}

function hasUserAccess(
  req: NextRequest,
  secret: string,
  nowEpochSeconds: number,
): boolean {
  if (hasAdminAccess(req, secret, nowEpochSeconds)) {
    return true;
  }

  return hasValidGateCookie(
    req,
    USER_GATE_COOKIE_NAME,
    secret,
    nowEpochSeconds,
    'user',
  );
}

function resolveEntryExpectation(
  pathname: string,
): { allowed: true; kind: GateKind } | { allowed: false } {
  if (pathname === USER_ENTRY_PATH) {
    return { allowed: true, kind: 'user' };
  }

  if (pathname === ADMIN_ENTRY_PATH) {
    return { allowed: true, kind: 'admin' };
  }

  return { allowed: false };
}

function handleEntryRequest(
  req: NextRequest,
  pathname: string,
  secret: string,
  nowEpochSeconds: number,
): NextResponse {
  const entry = resolveEntryExpectation(pathname);

  if (!entry.allowed) {
    return createNotFoundRewrite(req);
  }

  const token = req.nextUrl.searchParams.get(TOKEN_QUERY_KEY);

  if (!token) {
    return createNotFoundRewrite(req);
  }

  const verification = parseAndVerifySignedToken(
    token,
    secret,
    nowEpochSeconds,
    entry.kind,
  );

  if (!verification.ok) {
    return createNotFoundRewrite(req);
  }

  return createEntryRedirectResponse(req, verification.payload, secret);
}

export async function proxy(req: NextRequest): Promise<NextResponse> {
  if (req.headers.get('x-middleware-prefetch')) {
    return applySecurityHeaders(NextResponse.next());
  }

  const secret = process.env.GATEKEEPER_SECRET;

  if (!secret) {
    return createNotFoundRewrite(req);
  }

  const pathname = req.nextUrl.pathname;
  const nowEpochSeconds = Math.floor(Date.now() / 1000);

  if (pathname === USER_ENTRY_PATH || pathname === ADMIN_ENTRY_PATH) {
    return handleEntryRequest(req, pathname, secret, nowEpochSeconds);
  }

  if (isPublicRoute(pathname)) {
    return applySecurityHeaders(NextResponse.next());
  }

  const allowed =
    hasAdminAccess(req, secret, nowEpochSeconds) ||
    hasUserAccess(req, secret, nowEpochSeconds);

  if (!allowed) {
    return createNotFoundRewrite(req);
  }

  const response = applySecurityHeaders(NextResponse.next());

  if (hasAdminAccess(req, secret, nowEpochSeconds)) {
    response.headers.set('x-airdeliver-access-tier', 'admin');
  } else {
    response.headers.set('x-airdeliver-access-tier', 'user');
  }

  return response;
}

export const config = {
  matcher: [
    '/((?!api|_next/static|_next/image|favicon.ico|robots.txt|sitemap.xml|avatars|images|textures).*)',
  ],
};
