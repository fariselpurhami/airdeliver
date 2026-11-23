/* apps/web/lib/api.ts */

import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import type { Session } from 'next-auth';

interface ExtendedSession extends Session {
  accessToken?: string;
}

const isServer = typeof window === 'undefined';

const baseURL = isServer
  ? process.env.API_URL || 'http://api:8000/api/v1'
  : process.env.NEXT_PUBLIC_API_URL || '/api/v1';

let serverAuthModule: typeof import('@/auth') | null = null;
let clientAuthModule: typeof import('next-auth/react') | null = null;

const api = axios.create({
  baseURL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
    'X-Requested-With': 'XMLHttpRequest',
  },
  withCredentials: true,
});

api.interceptors.request.use(
  async (config: InternalAxiosRequestConfig) => {
    try {
      let token: string | undefined;

      if (isServer) {
        if (!serverAuthModule) {
          serverAuthModule = await import('@/auth');
        }
        const session = (await serverAuthModule.auth()) as ExtendedSession | null;
        token = session?.accessToken;
      } else {
        if (!clientAuthModule) {
          clientAuthModule = await import('next-auth/react');
        }
        const session = (await clientAuthModule.getSession()) as ExtendedSession | null;
        token = session?.accessToken;
      }

      if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    } catch (error) {
      if (isServer) {
        console.warn('[API] Auth injection skipped on server context');
      }
    }

    return config;
  },
  (error: Error) => Promise.reject(error)
);

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    if (error.code === 'ECONNREFUSED' || error.code === 'ERR_NETWORK') {
      console.error(`🔥 [API FATAL] Network failure connecting to ${baseURL}. Service down.`);
    }

    if (error.response?.status === 401) {
      if (!isServer) {
        console.warn('🔒 [API] 401 Unauthorized. Session expired or invalid.');
      }
    }

    if (error.response?.status === 429) {
      console.warn('⏳ [API] 429 Too Many Requests. Throttling applied.');
    }

    return Promise.reject(error);
  }
);

export { api };
