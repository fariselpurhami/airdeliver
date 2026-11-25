// frontend/web/auth.ts

import NextAuth, { type DefaultSession, type NextAuthConfig, type User } from "next-auth";
import Credentials from "next-auth/providers/credentials";
import { jwtDecode } from "jwt-decode";
import type { JWT } from "next-auth/jwt";

type UserRole = string;

interface BackendTokenResponse {
  access_token: string;
  token_type?: string;
}

interface DecodedAccessToken {
  sub?: string;
  role?: string;
  exp?: number;
  email?: string;
  name?: string;
}

interface AuthenticatedUser extends User {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  accessToken: string;
  accessTokenExpiresAt?: number;
}

declare module "next-auth" {
  interface Session {
    accessToken?: string;
    error?: "AccessTokenExpired";
    user: {
      id: string;
      role: UserRole;
      accessToken?: string;
      error?: string;
    } & DefaultSession["user"];
  }

  interface User {
    role?: UserRole;
    accessToken?: string;
    accessTokenExpiresAt?: number;
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    sub?: string;
    role?: UserRole;
    accessToken?: string;
    accessTokenExpiresAt?: number;
    error?: "AccessTokenExpired";
  }
}

const API_URL = process.env.API_URL?.trim() || "http://api:8000/api/v1";
const AUTH_SECRET = process.env.AUTH_SECRET?.trim();

if (!AUTH_SECRET) {
  throw new Error("Missing AUTH_SECRET environment variable.");
}

function buildTokenEndpoint(baseUrl: string): string {
  return `${baseUrl.replace(/\/+$/, "")}/auth/token`;
}

function normalizeRole(role?: string): UserRole {
  return role?.trim().toLowerCase() || "user";
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function isTokenExpired(expiresAt?: number): boolean {
  if (!expiresAt) return false;
  return Date.now() >= expiresAt;
}

function parseTokenExpiry(exp?: number): number | undefined {
  if (!exp || !Number.isFinite(exp)) return undefined;
  return exp * 1000;
}

function mapDecodedTokenToUser(accessToken: string, decoded: DecodedAccessToken): AuthenticatedUser | null {
  if (!isNonEmptyString(decoded.sub)) {
    return null;
  }

  const email = isNonEmptyString(decoded.email) ? decoded.email : decoded.sub;
  const name = isNonEmptyString(decoded.name) ? decoded.name : email;

  return {
    id: decoded.sub,
    email,
    name,
    role: normalizeRole(decoded.role),
    accessToken,
    accessTokenExpiresAt: parseTokenExpiry(decoded.exp),
  };
}

async function authenticateWithCredentials(email: string, password: string): Promise<AuthenticatedUser | null> {
  const response = await fetch(buildTokenEndpoint(API_URL), {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      Accept: "application/json",
    },
    body: new URLSearchParams({
      username: email,
      password,
    }),
    cache: "no-store",
  });

  if (!response.ok) {
    return null;
  }

  const data = (await response.json()) as BackendTokenResponse;

  if (!isNonEmptyString(data.access_token)) {
    return null;
  }

  let decoded: DecodedAccessToken;
  try {
    decoded = jwtDecode<DecodedAccessToken>(data.access_token);
  } catch {
    return null;
  }

  return mapDecodedTokenToUser(data.access_token, decoded);
}

export const authConfig: NextAuthConfig = {
  trustHost: true,
  secret: AUTH_SECRET,
  session: {
    strategy: "jwt",
  },
  pages: {
    signIn: "/login",
    error: "/login",
  },
  providers: [
    Credentials({
      name: "Credentials",
      credentials: {
        email: {
          label: "Email",
          type: "email",
          autocomplete: "email",
        },
        password: {
          label: "Password",
          type: "password",
          autocomplete: "current-password",
        },
      },
      async authorize(credentials) {
        const email = typeof credentials?.email === "string" ? credentials.email.trim() : "";
        const password = typeof credentials?.password === "string" ? credentials.password : "";

        if (!email || !password) {
          return null;
        }

        try {
          return await authenticateWithCredentials(email, password);
        } catch {
          return null;
        }
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user }): Promise<JWT> {
      if (user) {
        const authenticatedUser = user as AuthenticatedUser;

        token.sub = authenticatedUser.id;
        token.role = normalizeRole(authenticatedUser.role);
        token.accessToken = authenticatedUser.accessToken;
        token.accessTokenExpiresAt = authenticatedUser.accessTokenExpiresAt;
        token.error = undefined;

        return token;
      }

      if (isTokenExpired(token.accessTokenExpiresAt)) {
        token.error = "AccessTokenExpired";
        token.accessToken = undefined;
      }

      return token;
    },

    async session({ session, token }) {
      if (session.user) {
        session.user.id = token.sub ?? "";
        session.user.role = normalizeRole(token.role);
        // @ts-ignore
        session.user.accessToken = token.accessToken;
        // @ts-ignore
        session.user.error = token.error;
      }

      session.accessToken = token.accessToken;
      session.error = token.error;

      return session;
    },

    authorized({ auth, request }) {
      const isAuthenticated = Boolean(auth?.user);
      const pathname = request.nextUrl.pathname;

      const isAuthRoute = pathname === "/login";
      const isProtectedRoute = !isAuthRoute;

      if (isAuthRoute) {
        return !isAuthenticated;
      }

      if (isProtectedRoute) {
        return isAuthenticated;
      }

      return true;
    },
  },
};

export const { handlers, signIn, signOut, auth } = NextAuth(authConfig);
