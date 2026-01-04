// apps/web/lib/api.ts

import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';

// 💎 SOTA ARCHITECTURE: Define Environment and Base URL
const isServer = typeof window === 'undefined';

const baseURL = isServer 
  ? (process.env.API_URL || 'http://api:8000/api/v1') // Server: Use Docker Service Name
  : (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'); // Client: Use Hostname

const api = axios.create({
  baseURL,
  timeout: 40000,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  },
  withCredentials: true,
});

// 💎 SOTA INTERCEPTOR: Context-Aware Authentication Injection
api.interceptors.request.use(
  async (config: InternalAxiosRequestConfig) => {
    try {
      let token = null;

      if (isServer) {
        // 🖥️ SERVER-SIDE: Use the Auth.js auth() helper (No HTTP roundtrip)
        const { auth } = await import("@/auth");
        const session = await auth();
        // @ts-ignore
        token = session?.accessToken; 
      } else {
        // 🌐 CLIENT-SIDE: Use standard next-auth/react getSession
        const { getSession } = await import("next-auth/react");
        const session = await getSession();
        // @ts-ignore
        token = session?.accessToken;
      }

      if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    } catch (error) {
       // Log warning but allow request to continue for public endpoints
       if (isServer) console.warn('[API] Auth injection skipped on server');
    }
    return config;
  },
  (error) => Promise.reject(error)
);

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    if (error.code === 'ECONNREFUSED') {
        console.error(`🔥 [API FATAL] Connection Refused to ${baseURL}. Service might be down.`);
    }
    return Promise.reject(error);
  }
);

export { api };
