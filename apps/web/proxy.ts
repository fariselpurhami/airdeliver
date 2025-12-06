// apps/web/proxy.ts

import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { getToken } from 'next-auth/jwt';

/**
 * 💎 AIRDELIVER GLOBAL PROXY (The Iron Dome)
 * -------------------------------------------
 * Scope: GLOBAL (Runs on entire platform)
 * Strategy: Smart Traffic Control (Public vs Protected Zones)
 */

// 1. PUBLIC ZONES DEFINITION
// These paths are accessible to everyone, but still monitored by Proxy.
const publicPaths = [
  '/',              // Home
  '/login',         // Auth
  '/about',         // Info
  '/help',          // Support
  '/tracking',      // Order Tracking (Public access allowed usually)
  '/legal',         // Terms & Privacy
];

export async function proxy(req: NextRequest) {
  const { pathname } = req.nextUrl;

  // =========================================================
  // 1. ⚡ PERFORMANCE BYPASS (Static & Assets)
  // =========================================================
  // Skip logic for Prefetching to save resources
  if (req.headers.get('x-middleware-prefetch')) {
    return NextResponse.next();
  }

  // =========================================================
  // 2. 🛡️ GLOBAL SECURITY HEADERS (Injected Everywhere)
  // =========================================================
  // Even on public pages, we inject security headers or tracking IDs.
  // This satisfies your requirement: "Works on the whole platform".
  const response = NextResponse.next();
  response.headers.set('x-airdeliver-guard', 'active');
  response.headers.set('x-frame-options', 'SAMEORIGIN'); // Prevent Clickjacking globally

  // =========================================================
  // 3. 🚦 ROUTE INTELLIGENCE (Public vs Protected)
  // =========================================================
  
  // Check if the current path is Public or a Product page
  const isPublicPath = publicPaths.some(path => pathname === path || pathname.startsWith(path)) || 
                       pathname.startsWith('/products') || // /products & /products/xyz
                       pathname.startsWith('/product');    // /product/xyz

  // ✅ CHECK: Is user authenticated?
  const hasAuthCookie = req.cookies.has('next-auth.session-token') || 
                        req.cookies.has('__Secure-next-auth.session-token');

  // SCENARIO A: Public Page (e.g., Home, Products)
  if (isPublicPath) {
    // Even if public, if they have a token, we might want to pass it through specifically
    // but generally, we just let them pass.
    return response;
  }

  // SCENARIO B: Protected Page (Dashboard, Profile, Checkout, Orders)
  // If NOT public, it MUST be protected.
  if (!hasAuthCookie) {
    // User is trying to access a protected zone without a badge.
    return redirectToLogin(req, pathname);
  }

  // =========================================================
  // 4. 🔐 DEEP AUTH VERIFICATION (For Protected Routes Only)
  // =========================================================
  try {
    const secret = process.env.NEXTAUTH_SECRET;
    if (!secret) {
      console.error("🚨 CRITICAL: NEXTAUTH_SECRET is missing.");
      return redirectToLogin(req, pathname);
    }

    const session = await getToken({ req, secret });

    if (!session) {
      // Invalid/Expired Token
      return redirectToLogin(req, pathname);
    }

    // 👑 ADMIN PROTECTION LAYER (Based on your file tree structure)
    // If user tries to access /dashboard or /admin, verify role
    if (pathname.startsWith('/dashboard') || pathname.startsWith('/admin')) {
      if (session.role !== 'ADMIN' && session.role !== 'SUPER_ADMIN') {
        // Redirect unauthorized access to home or 403 page
        return NextResponse.redirect(new URL('/', req.url));
      }
    }

    // Inject User ID for backend tracing
    response.headers.set('x-user-id', session.sub || 'unknown');
    return response;

  } catch (error) {
    console.error('🔥 [Proxy Exception]:', error);
    return redirectToLogin(req, pathname);
  }
}

/**
 * 🔄 Smart Redirect
 */
function redirectToLogin(req: NextRequest, pathname: string) {
  const signInUrl = new URL('/login', req.url);
  signInUrl.searchParams.set('callbackUrl', pathname);
  return NextResponse.redirect(signInUrl);
}

/**
 * 🎯 GLOBAL MATCHER CONFIGURATION
 * ---------------------------------
 * Regex Explanation:
 * Match ALL paths (.*) EXCEPT:
 * - api (Next.js API routes - handled separately or let pass)
 * - _next/static (JS chunks, CSS)
 * - _next/image (Image optimization)
 * - favicon.ico
 * - avatars (Found in your apps/web/public/avatars)
 * - images (Found in your apps/web/public/images)
 * - textures (Found in your apps/web/public/textures)
 */
export const config = {
  matcher: [
    '/((?!api|_next/static|_next/image|favicon.ico|avatars|images|textures).*)',
  ],
};
