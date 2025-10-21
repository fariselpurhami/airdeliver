// file: apps/web/lib/authOptions.ts (النسخة النهائية بالعنوان الصحيح 100%)

import { NextAuthOptions } from 'next-auth';
import CredentialsProvider from 'next-auth/providers/credentials';
import { jwtDecode } from 'jwt-decode';

interface DecodedToken {
  sub: string;
  role: string; // Assuming role is directly on the token
  exp: number;
}

export const authOptions: NextAuthOptions = {
  providers: [
    CredentialsProvider({
      name: 'Credentials',
      credentials: {
        email: { label: 'Email', type: 'email' },
        password: { label: 'Password', type: 'password' },
      },
      async authorize(credentials) {
        if (!credentials) return null;
        try {
          // --- العنوان الصحيح للـ API بناءً على auth.py الأصلي ---
          const apiUrl = 'http://api:8000/api/v1'; // العنوان الأساسي للـ API
          const loginUrl = `${apiUrl}/auth/token`; // المسار الصحيح لتسجيل الدخول

          console.log(`Authorize attempting to fetch from: ${loginUrl}`);

          const res = await fetch(loginUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            // FastAPI's OAuth2 expects the email field to be named 'username'
            body: new URLSearchParams({ username: credentials.email, password: credentials.password }),
          });

          console.log(`Authorize response status: ${res.status}`);

          if (!res.ok) {
            console.error('Failed to authorize with API', res.status, await res.text());
            return null; // فشل تسجيل الدخول
          }

          const data = await res.json();
          if (data && data.access_token) {
            const decoded: DecodedToken = jwtDecode(data.access_token);
            // إرجاع كائن المستخدم لـ NextAuth
            return {
              id: decoded.sub, // استخدام الإيميل كـ id مؤقتًا
              email: decoded.sub,
              name: decoded.sub, // يمكنك تحسين الاسم لاحقًا
              role: decoded.role, // جلب الصلاحية من التوكن
              accessToken: data.access_token,
            };
          }
          return null;
        } catch (error) {
          console.error('Authorize Error during fetch:', error);
          return null;
        }
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user }) {
      // عند تسجيل الدخول، أضف الخصائص المخصصة للـ JWT
      if (user) {
        token.accessToken = (user as any).accessToken;
        token.role = (user as any).role;
      }
      return token;
    },
    async session({ session, token }) {
      // أضف الخصائص المخصصة لكائن الجلسة
      if (session.user) {
        (session.user as any).accessToken = token.accessToken;
        (session.user as any).role = token.role;
      }
      return session;
    },
  },
  pages: {
    signIn: '/login', // صفحة تسجيل الدخول المخصصة
    error: '/login', // إعادة التوجيه لصفحة الدخول عند الخطأ
  },
  session: {
    strategy: 'jwt', // استخدام JWT للجلسات
  },
  secret: process.env.NEXTAUTH_SECRET, // المفتاح السري لـ NextAuth
};
