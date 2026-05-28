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
  '/legal'
]);

const PUBLIC_PREFIX_ROUTES = [
  '/api/auth',
  '/products',
  '/product',
  '/_next'
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
    return createLoginRedirect(req, pathname);
  }

  const secret = process.env.AUTH_SECRET;

  if (!secret) {
    return createLoginRedirect(req, pathname);
  }

  try {
    const token = await getToken({ req, secret });

    if (!token) {
      return createLoginRedirect(req, pathname);
    }

    let requiresAdmin = false;
    for (let i = 0; i < ADMIN_PREFIXES.length; i++) {
      if (pathname.startsWith(ADMIN_PREFIXES[i])) {
        requiresAdmin = true;
        break;
      }
    }

    if (requiresAdmin && (!token.role || !ADMIN_ROLES.has(token.role as string))) {
      return NextResponse.redirect(new URL('/', req.url));
    }

    const response = applySecurityHeaders(NextResponse.next());
    response.headers.set('x-user-id', (token.sub as string) || 'unknown');

    return response;

  } catch (error) {
    return createLoginRedirect(req, pathname);
  }
}

export const config = {
  matcher: [
    '/((?!api|_next/static|_next/image|favicon.ico|avatars|images|textures).*)',
  ],
};
