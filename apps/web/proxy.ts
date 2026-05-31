// apps/web/proxy.ts

import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { getToken } from 'next-auth/jwt';

const PUBLIC_EXACT_ROUTES = new Set([
  '/',
  '/login',
  '/register',
  '/about',
  '/help',
  '/tracking',
]);

const PUBLIC_PREFIX_ROUTES = [
  '/api/auth',
  '/products',
  '/product',
  '/_next',
  '/legal'
];

const AUTH_COOKIES = [
  'authjs.session-token',
  '__Secure-authjs.session-token',
  'next-auth.session-token',
  '__Secure-next-auth.session-token'
];

const ADMIN_PREFIXES = [
  '/dashboard',
  '/admin'
];

const ADMIN_ROLES = new Set([
  'admin',
  'ADMIN',
  'SUPER_ADMIN'
]);

const SECURITY_HEADERS = {
  'x-airdeliver-guard': 'active',
  'x-frame-options': 'DENY',
  'x-content-type-options': 'nosniff',
  'referrer-policy': 'strict-origin-when-cross-origin',
  'strict-transport-security': 'max-age=31536000; includeSubDomains'
} as const;

function isPublicRoute(pathname: string): boolean {
  if (PUBLIC_EXACT_ROUTES.has(pathname)) {
    return true;
  }
  for (let i = 0; i < PUBLIC_PREFIX_ROUTES.length; i++) {
    if (pathname.startsWith(PUBLIC_PREFIX_ROUTES[i])) {
      return true;
    }
  }
  return false;
}

function hasAuthCookie(req: NextRequest): boolean {
  for (let i = 0; i < AUTH_COOKIES.length; i++) {
    if (req.cookies.has(AUTH_COOKIES[i])) {
      return true;
    }
  }
  return false;
}

function createLoginRedirect(req: NextRequest, pathname: string): NextResponse {
  if (pathname === '/login') {
    return NextResponse.next();
  }
  const url = new URL('/login', req.url);
  url.searchParams.set('callbackUrl', pathname);
  return NextResponse.redirect(url);
}

function applySecurityHeaders(response: NextResponse): NextResponse {
  for (const [key, value] of Object.entries(SECURITY_HEADERS)) {
    response.headers.set(key, value);
  }
  return response;
}

export async function proxy(req: NextRequest) {
  if (req.headers.get('x-middleware-prefetch')) {
    return NextResponse.next();
  }

  const { pathname } = req.nextUrl;
  const isPublic = isPublicRoute(pathname);

  if (isPublic) {
    return applySecurityHeaders(NextResponse.next());
  }

  if (!hasAuthCookie(req)) {
    console.log("🚨 MIDDLEWARE BLOCKED: No Auth Cookie found in browser!");
    return createLoginRedirect(req, pathname);
  }

  const secret = process.env.AUTH_SECRET;

  if (!secret) {
    console.log("🚨 MIDDLEWARE BLOCKED: AUTH_SECRET is missing in .env!");
    return createLoginRedirect(req, pathname);
  }

  try {
    const isSecureRequest =
      req.nextUrl.protocol === "https:" ||
      req.headers.get("x-forwarded-proto") === "https";

    const cookieCandidates = isSecureRequest
      ? [
          "__Secure-authjs.session-token",
          "__Secure-next-auth.session-token",
          "authjs.session-token",
          "next-auth.session-token",
        ]
      : ["authjs.session-token", "next-auth.session-token"];

    let token = null;

    for (const cookieName of cookieCandidates) {
      if (!req.cookies.has(cookieName)) {
        continue;
      }

      token = await getToken({
        req,
        secret,
        secureCookie: isSecureRequest,
        cookieName,
        salt: cookieName,
      });

      if (token) {
        break;
      }
    }

    if (!token) {
      return createLoginRedirect(req, pathname);
    }

    const requiresAdmin = ADMIN_PREFIXES.some((prefix) => pathname.startsWith(prefix));
    const role = typeof token.role === "string" ? token.role : null;

    if (requiresAdmin && (!role || !ADMIN_ROLES.has(role))) {
      return NextResponse.redirect(new URL("/", req.url));
    }

    return applySecurityHeaders(NextResponse.next());
  } catch {
    return createLoginRedirect(req, pathname);
  }
} // <--- القوس ده اللي كان ناقص وبيعمل المشكلة

export const config = {
  matcher: [
    '/((?!api|_next/static|_next/image|favicon.ico|avatars|images|textures).*)',
  ],
};
