// file: apps/web/app/api/auth/[...nextauth]/route.ts
// version: 1.0.0
// date: 2025-09-23
// author: Gemini 2.5 Pro

import NextAuth from 'next-auth';
import { authOptions } from '@/lib/authOptions';

const handler = NextAuth(authOptions);

export { handler as GET, handler as POST };
