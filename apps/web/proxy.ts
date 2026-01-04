// apps/web/proxy.ts

import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { getToken } from 'next-auth/jwt';

/**
 * 💎 AIRDELIVER GLOBAL PROXY (The Iron Dome) - V5 UPDATE
 * -------------------------------------------
 * Scope: GLOBAL (Runs on entire platform)
 * Strategy: Smart Traffic Control (Public vs Protected Zones)
 */

// 1. PUBLIC ZONES DEFINITION
const publicPaths = [
  '/',              
  '/login',         
  '/register',      // Added Register just in case
  '/about',         
  '/help',          
  '/tracking',      
  '/legal', 
  '/api/auth',      // ⚠️ IMPORTANT: Allow Auth Routes pass through       
];

export async function proxy(req: NextRequest) {
  const { pathname } = req.nextUrl;

  // =========================================================
  // 1. ⚡ PERFORMANCE BYPASS
  // =========================================================
  if (req.headers.get('x-middleware-prefetch')) {
    return NextResponse.next();
  }

  // =========================================================
  // 2. 🛡️ GLOBAL SECURITY HEADERS
  // =========================================================
  const response = NextResponse.next();
  response.headers.set('x-airdeliver-guard', 'active');
  response.headers.set('x-frame-options', 'SAMEORIGIN');

  // =========================================================
  // 3. 🚦 ROUTE INTELLIGENCE (Public vs Protected)
  // =========================================================
  
  // Check if public path OR product page OR NextAuth internal route
  const isPublicPath = publicPaths.some(path => pathname === path || pathname.startsWith(path)) || 
                       pathname.startsWith('/products') || 
                       pathname.startsWith('/product') ||
                       pathname.startsWith('/_next'); // Allow Next.js internals

  // 🔍 V5 COOKIE DETECTION (The Missing Link)
  // Auth.js v5 uses 'authjs.session-token' by default now
  const hasAuthCookie = 
    req.cookies.has('authjs.session-token') ||                // <--- V5 Standard (HTTP)
    req.cookies.has('__Secure-authjs.session-token') ||       // <--- V5 Standard (HTTPS)
    req.cookies.has('next-auth.session-token') ||             // <--- Legacy V4
    req.cookies.has('__Secure-next-auth.session-token');      // <--- Legacy V4 Secure

  // Debug Log (To see what's happening in Docker logs)
  // console.log(`🛡️ Proxy: ${pathname} | Cookie Found: ${hasAuthCookie}`);

  // SCENARIO A: Public Page
  if (isPublicPath) {
    return response;
  }

  // SCENARIO B: Protected Page
  if (!hasAuthCookie) {
    console.log(`⛔ Proxy Block: User tried accessing ${pathname} without cookie.`);
    return redirectToLogin(req, pathname);
  }

  // =========================================================
  // 4. 🔐 DEEP AUTH VERIFICATION
  // =========================================================
  try {
    const secret = process.env.AUTH_SECRET;
    if (!secret) {
      console.error("🚨 CRITICAL: AUTH_SECRET is missing in Proxy.");
      // In dev, we might want to fail hard, but for now redirect
      return redirectToLogin(req, pathname);
    }

    // ⚠️ Note: getToken in v5 might need explicit cookieName if defaults differ
    // but usually it detects 'authjs.session-token' automatically in latest versions.
    const session = await getToken({ 
      req, 
      secret,
      // If V5 standard fails, we might need to specify cookieName here, 
      // but let's try standard first.
    });

    if (!session) {
      console.log(`⚠️ Proxy Warning: Cookie existed but token validation failed for ${pathname}`);
      return redirectToLogin(req, pathname);
    }

    // 👑 ADMIN PROTECTION LAYER
    if (pathname.startsWith('/dashboard') || pathname.startsWith('/admin')) {
      if (session.role !== 'admin' && session.role !== 'SUPER_ADMIN') {
        console.log(`⛔ Role Mismatch: User ${session.sub} tried accessing Admin.`);
        return NextResponse.redirect(new URL('/', req.url));
      }
    }

    // Inject User ID
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
  // Avoid redirect loops
  if (pathname === '/login') return NextResponse.next();
  
  const signInUrl = new URL('/login', req.url);
  signInUrl.searchParams.set('callbackUrl', pathname);
  return NextResponse.redirect(signInUrl);
}

export const config = {
  matcher: [
    // Match everything EXCEPT api routes, static files, images
    '/((?!api|_next/static|_next/image|favicon.ico|avatars|images|textures).*)',
  ],
};
