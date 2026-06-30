// apps/web/app/api/auth/[...nextauth]/route.ts

import NextAuth from "next-auth";
import { authConfig } from "@/auth"; // استيراد الإعدادات فقط

// في الإصدار الرابع، NextAuth بترجع الـ handler مباشرة
const handler = NextAuth(authConfig);

// تصدير المسارات لـ Next.js
export { handler as GET, handler as POST };
