//** apps/web/lib/authOptions.ts **//

import type { NextAuthConfig, User } from 'next-auth';
import Credentials from 'next-auth/providers/credentials';
import { jwtDecode } from 'jwt-decode';

interface DecodedToken {
  sub: string;
  role: string;
  exp: number;
}

interface ExtendedUser extends User {
  role?: string;
  accessToken?: string;
}

const INTERNAL_API_URL = process.env.INTERNAL_API_URL || 'http://api:8000/api/v1';

export const authOptions: NextAuthConfig = {
  providers: [
    Credentials({
      name: 'Credentials',
      credentials: {
        email: { label: 'Email', type: 'email' },
        password: { label: 'Password', type: 'password' },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) return null;
        
        try {
          const loginUrl = `${INTERNAL_API_URL}/auth/token`;
          
          const res = await fetch(loginUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({ 
              username: credentials.email as string, 
              password: credentials.password as string 
            }),
          });

          if (!res.ok) {
            return null;
          }

          const data = await res.json();
          
          if (data && data.access_token) {
            const decoded: DecodedToken = jwtDecode(data.access_token);
            
            return {
              id: decoded.sub,
              email: decoded.sub,
              name: decoded.sub,
              role: decoded.role,
              accessToken: data.access_token,
            } as ExtendedUser;
          }
          return null;
        } catch (error) {
          return null;
        }
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.accessToken = (user as ExtendedUser).accessToken;
        token.role = (user as ExtendedUser).role;
        token.sub = user.id;
      }
      return token;
    },

    async session({ session, token }) {
      if (token) {
        session.accessToken = token.accessToken as string;
        
        if (session.user) {
          session.user.id = token.sub as string;
          session.user.role = (token.role as string)?.toLowerCase();
        }
      }
      return session;
    },
  },
  pages: {
    signIn: '/login',
    error: '/login',
  },
  session: {
    strategy: 'jwt',
  },
  secret: process.env.NEXTAUTH_SECRET,
};
