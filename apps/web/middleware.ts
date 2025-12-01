// apps/web/middleware.ts

import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { getToken } from 'next-auth/jwt';

export async function middleware(req: NextRequest) {

  const { pathname } = req.nextUrl;

  const hasAuthCookie = req.cookies.has('next-auth.session-token') || 
                        req.cookies.has('__Secure-next-auth.session-token');

  if (!hasAuthCookie) {
    const signInUrl = new URL('/login', req.url);
    signInUrl.searchParams.set('callbackUrl', pathname);
    return NextResponse.redirect(signInUrl);
  }

  const session = await getToken({ req, secret: process.env.NEXTAUTH_SECRET });

  if (!session) {
    const signInUrl = new URL('/login', req.url);
    signInUrl.searchParams.set('callbackUrl', pathname);
    return NextResponse.redirect(signInUrl);
  }

  const response = NextResponse.next();
  
  response.headers.set('X-DNS-Prefetch-Control', 'on');
  response.headers.set('Strict-Transport-Security', 'max-age=63072000; includeSubDomains; preload');
  response.headers.set('X-Frame-Options', 'SAMEORIGIN');
  response.headers.set('X-Content-Type-Options', 'nosniff'); 
  response.headers.set('Referrer-Policy', 'origin-when-cross-origin'); 
  response.headers.set('Cache-Control', 'private, no-cache, no-store, max-age=0, must-revalidate');

  return response;
}

export const config = {
  matcher: [
    '/profile/:path*',
    '/orders/:path*',
    '/settings/:path*',
    '/dashboard/:path*',
    '/checkout/:path*'
  ],
};
