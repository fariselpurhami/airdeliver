// apps/web/app/api/auth/[...nextauth]/route.ts

import { handlers } from "@/auth"; // نستدعي الـ handlers الجاهزة من ملف الإعدادات

export const { GET, POST } = handlers;
