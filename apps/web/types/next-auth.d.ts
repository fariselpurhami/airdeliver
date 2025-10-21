// file: apps/web/types/next-auth.d.ts

import { DefaultSession, DefaultUser } from 'next-auth';
import { JWT, DefaultJWT } from 'next-auth/jwt';

// قم بتوسيع تعريفات JWT
declare module 'next-auth/jwt' {
  interface JWT extends DefaultJWT {
    role?: string;
    accessToken?: string;
  }
}

// قم بتوسيع تعريفات Session و User
declare module 'next-auth' {
  interface Session {
    user: {
      id?: string;
      role?: string;
    } & DefaultSession['user'];
    accessToken?: string;
  }

  interface User extends DefaultUser {
    role?: string;
    accessToken?: string;
  }
}
