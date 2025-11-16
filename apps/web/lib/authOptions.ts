//** apps/web/lib/authOptions.ts **//

import { NextAuthOptions } from 'next-auth';
import CredentialsProvider from 'next-auth/providers/credentials';
import { jwtDecode } from 'jwt-decode';

interface DecodedToken {
  sub: string;
  role: string; 
  exp: number;
}

const INTERNAL_API_URL = process.env.INTERNAL_API_URL || 'http://api:8000/api/v1';

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
          
          const loginUrl = `${INTERNAL_API_URL}/auth/token`; 

          console.log(`Authorize attempting to fetch from: ${loginUrl}`);

          const res = await fetch(loginUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({ username: credentials.email, password: credentials.password }),
          });

          console.log(`Authorize response status: ${res.status}`);

          if (!res.ok) {
            console.error('Failed to authorize with API', res.status, await res.text());
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
      
      if (user) {
        token.accessToken = (user as any).accessToken;
        token.role = (user as any).role;
      }
      return token;
    },

    async session({ session, token }) {
      
      session.accessToken = token.accessToken as string;

     
      if (session.user) {
        
        if (token.role) {
            session.user.role = (token.role as string).toLowerCase();
        }
        
        session.user.id = token.sub as string;
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
