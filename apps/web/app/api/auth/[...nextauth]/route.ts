// apps/web/app/api/auth/[...nextauth]/route.ts

// 💎 SOTA ARCHITECTURE: Import handlers directly from the central configuration file
import { handlers } from "@/auth"

// Export standard HTTP methods for App Router (The correct v5 syntax)
export const { GET, POST } = handlers
