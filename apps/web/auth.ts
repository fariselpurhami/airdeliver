// apps/web/auth.ts
import NextAuth, { type NextAuthConfig, type User } from "next-auth"
import Credentials from "next-auth/providers/credentials"
import { jwtDecode } from 'jwt-decode';

// --- ⚙️ Type Definitions ---
interface DecodedToken {
  sub: string;
  role: string;
  exp: number;
}

interface ExtendedUser extends User {
  role?: string;
  accessToken?: string;
}

// الرابط الداخلي للـ Docker (Backend Service)
const INTERNAL_API_URL = process.env.API_URL || 'http://api:8000/api/v1'; 

export const authConfig: NextAuthConfig = {
  // 🛡️ SOTA FIX: ضروري جداً لبيئة Docker
  trustHost: true, 
  secret: process.env.AUTH_SECRET,
  session: { strategy: 'jwt' },
  pages: {
    signIn: '/login',
    error: '/login',
  },
  
  providers: [
    Credentials({
      name: 'Credentials',
      credentials: {
        email: { label: 'Email', type: 'email' },
        password: { label: 'Password', type: 'password' },
      },
      async authorize(credentials) {
        console.log("\n🛑 ---------------- AUTH DEBUG START ----------------");
        console.log("🔥 1. Authorize Function Triggered");
        
        if (!credentials?.email || !credentials?.password) {
            console.log("❌ 1.1 Missing credentials inputs");
            return null;
        }
        
        try {
          const loginUrl = `${INTERNAL_API_URL}/auth/token`;
          console.log(`🌐 2. Target API URL: ${loginUrl}`);
          console.log(`📨 2.1 Payload sent: username=${credentials.email}`);
          
          const res = await fetch(loginUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({ 
              username: credentials.email as string, 
              password: credentials.password as string 
            }),
          });

          console.log(`📡 3. API Response Status: ${res.status} ${res.statusText}`);

          if (!res.ok) {
            const errorText = await res.text();
            console.log(`❌ 3.1 API Error Body: ${errorText}`);
            console.log("🛑 ---------------- AUTH DEBUG END (FAIL) ----------------\n");
            return null; 
          }

          const data = await res.json();
          // طباعة أول 50 حرف من التوكن عشان اللوج ميبقاش ضخم
          const tokenPreview = data.access_token ? `${data.access_token.substring(0, 50)}...` : 'NONE';
          console.log(`📦 4. API Data Received. Token Preview: ${tokenPreview}`);
          
          if (data && data.access_token) {
            console.log("🔑 5. Token found, attempting decode...");
            
            try {
                const decoded = jwtDecode<DecodedToken>(data.access_token);
                console.log("🧩 6. Token Decoded Successfully:", JSON.stringify(decoded, null, 2));

                // التحقق من وجود الـ ID (sub)
                if (!decoded.sub) {
                    console.log("❌ 6.1 CRITICAL: 'sub' field missing in token!");
                    return null;
                }

                const userObj: ExtendedUser = {
                  id: decoded.sub,
                  email: decoded.sub, // يمكن تغييره لو التوكن فيه حقل email منفصل
                  name: decoded.sub,
                  role: decoded.role,
                  accessToken: data.access_token,
                };
                
                console.log("✅ 7. Authorization Successful. Returning User Object.");
                console.log("🛑 ---------------- AUTH DEBUG END (SUCCESS) ----------------\n");
                return userObj;

            } catch (decodeError) {
                console.log("❌ 5.1 JWT Decode Failed:", decodeError);
                return null;
            }
          }
          
          console.log("❌ 4.1 No access_token in response data");
          return null;

        } catch (error) {
          console.error("☠️ CRITICAL SYSTEM ERROR inside authorize:", error);
          return null;
        }
      },
    }),
  ],
  
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        // هذه الخطوة تحدث فقط عند تسجيل الدخول لأول مرة
        const u = user as ExtendedUser;
        token.accessToken = u.accessToken;
        token.role = u.role;
        token.sub = u.id;
      }
      return token;
    },

    async session({ session, token }) {
      if (token && session.user) {
        // نقل البيانات من التوكن للسيشن عشان الفرونت يشوفها
        // @ts-ignore
        session.accessToken = token.accessToken as string; 
        // @ts-ignore
        session.user.id = token.sub as string;
        // @ts-ignore
        session.user.role = (token.role as string)?.toLowerCase();
      }
      return session;
    },
  },
}

export const { handlers, signIn, signOut, auth } = NextAuth(authConfig)
