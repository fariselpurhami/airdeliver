// file: apps/web/lib/authOptions.ts
// version: 1.0.0
// date: 2025-09-23
// author: Gemini 2.5 Pro

import { NextAuthOptions } from 'next-auth';
import CredentialsProvider from 'next-auth/providers/credentials';
import { api } from './api';
import { jwtDecode } from 'jwt-decode';

interface DecodedToken {
  sub: string;
  role: string;
  exp: number;
}

export const authOptions: NextAuthOptions = {
  providers: [
    CredentialsProvider({
      name: 'Credentials',
      credentials: {
        username: { label: 'Email', type: 'email' },
        password: { label: 'Password', type: 'password' },
      },
      async authorize(credentials) {
        if (!credentials) return null;
        try {
          const { data } = await api.post('/auth/token', new URLSearchParams(credentials));
          if (data && data.access_token) {
            const decoded: DecodedToken = jwtDecode(data.access_token);
            return {
              id: decoded.sub,
              email: decoded.sub,
              role: decoded.role,
              accessToken: data.access_token,
            };
          }
          return null;
        } catch (error) {
          console.error('Auth Error', error);
          return null;
        }
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.accessToken = user.accessToken;
        token.role = user.role;
      }
      return token;
    },
    async session({ session, token }) {
      session.accessToken = token.accessToken;
      session.user.role = token.role;
      return session;
    },
  },
  pages: {
    signIn: '/profile', // Redirect to profile page for login
  },
  session: {
    strategy: 'jwt',
  },
  secret: process.env.NEXTAUTH_SECRET,
};
