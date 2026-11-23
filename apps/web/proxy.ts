// apps/web/proxy.ts

import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { auth } from '@/auth'; // استيراد الدالة القياسية لـ NextAuth بدلاً من getToken

const PUBLIC_EXACT_ROUTES = new Set([
  '/',
  '/login',
  '/forgot-password',
  '/reset-password',
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
    const prefix = PUBLIC_PREFIX_ROUTES[i];
    if (prefix && pathname.startsWith(prefix)) {
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
    const recovery = pathname === '/forgot-password' || pathname === '/reset-password';
    const requestHeaders = new Headers(req.headers);
    requestHeaders.set('x-airdeliver-recovery-page', recovery ? '1' : '0');
    const response = applySecurityHeaders(NextResponse.next({request:{headers:requestHeaders}}));
    if (recovery) {
      response.headers.set('Referrer-Policy', 'no-referrer');
      response.headers.set('Cache-Control', 'no-store');
      response.headers.set('X-Robots-Tag', 'noindex, nofollow');
    }
    return response;
  }

  try {
    // 🚀 التغيير الجوهري هنا: نترك NextAuth يقوم بالتحقق من الكوكيز وفك التشفير تلقائياً 
    const session = await auth();

    // إذا لم تكن هناك جلسة صالحة، قم بالتوجيه لصفحة الدخول
    if (!session || !session.user || session.error || !session.accessToken) {
      console.log("🚨 MIDDLEWARE BLOCKED: Unauthorized or no session found!");
      return createLoginRedirect(req, pathname);
    }

    const requiresAdmin = ADMIN_PREFIXES.some((prefix) => pathname.startsWith(prefix));
    const role = session.user.role;

    if (requiresAdmin && (!role || !ADMIN_ROLES.has(role))) {
      return NextResponse.redirect(new URL("/", req.url));
    }

    return applySecurityHeaders(NextResponse.next());
  } catch (error) {
    console.error("🚨 MIDDLEWARE ERROR:", error);
    return createLoginRedirect(req, pathname);
  }
}

export const config = {
  matcher: [
    '/((?!api|_next/static|_next/image|favicon.ico|site\\.webmanifest|robots\\.txt|sitemap\\.xml|avatars|images|textures|.*\\.(?:png|jpg|jpeg|svg|gif|webp|ico)$).*)',
  ],
};
