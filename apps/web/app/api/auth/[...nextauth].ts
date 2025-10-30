// apps/web/app/api/auth/[...nextauth].ts

import NextAuth, { NextAuthOptions } from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";
import { jwtDecode } from "jwt-decode";

export const authOptions: NextAuthOptions = {
  providers: [
    CredentialsProvider({
      name: "Credentials",
      credentials: {
        email: { label: "Email", type: "text" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        if (!credentials) return null;

        try {
          const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/auth/login/access-token`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({ username: credentials.email, password: credentials.password }),
          });

          if (!res.ok) {
            return null; 
          }

          const tokenData = await res.json();
          const decodedToken: { sub: string, role: string, exp: number } = jwtDecode(tokenData.access_token);
          
          return {
            id: decodedToken.sub, 
            email: decodedToken.sub,
            name: decodedToken.sub, 
            role: decodedToken.role,
            accessToken: tokenData.access_token,
          };

        } catch (e) {
          console.error("Authorize error:", e);
          return null;
        }
      },
    }),
  ],
  session: {
    strategy: "jwt",
  },
  callbacks: {
    async jwt({ token, user }) {
      
      if (user) {
        token.role = (user as any).role;
        token.accessToken = (user as any).accessToken;
      }
      return token;
    },
    async session({ session, token }) {
      
      if (session.user) {
        (session.user as any).role = token.role;
        (session.user as any).accessToken = token.accessToken;
      }
      return session;
    },
  },
  pages: {
    signIn: '/login', 
    error: '/login', 
  },
  secret: process.env.NEXTAUTH_SECRET,
};

const handler = NextAuth(authOptions);

export { handler as GET, handler as POST };
