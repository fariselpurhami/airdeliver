// file: apps/web/app/api/auth/[...nextauth].ts

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
            return null; // Login failed
          }

          const tokenData = await res.json();
          const decodedToken: { sub: string, role: string, exp: number } = jwtDecode(tokenData.access_token);
          
          // Return a user object that NextAuth can use
          return {
            id: decodedToken.sub, // Using email as id for now
            email: decodedToken.sub,
            name: decodedToken.sub, // You can enhance this later
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
      // When user logs in, add custom properties to the JWT
      if (user) {
        token.role = (user as any).role;
        token.accessToken = (user as any).accessToken;
      }
      return token;
    },
    async session({ session, token }) {
      // Add custom properties to the session object
      if (session.user) {
        (session.user as any).role = token.role;
        (session.user as any).accessToken = token.accessToken;
      }
      return session;
    },
  },
  pages: {
    signIn: '/login', // Redirect users to your custom login page
    error: '/login', // Redirect users to login page on error
  },
  secret: process.env.NEXTAUTH_SECRET,
};

const handler = NextAuth(authOptions);

export { handler as GET, handler as POST };
