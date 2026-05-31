// apps/web/app/api/auth/[...nextauth]/route.ts
import NextAuth from "next-auth";
import { authConfig } from "@/auth"; // تأكد من مسار ملف auth.ts الرئيسي

const handler = NextAuth(authConfig);

export { handler as GET, handler as POST };
