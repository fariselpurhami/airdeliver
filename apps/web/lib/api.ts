// apps/web/lib/api.ts

import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { getSession } from 'next-auth/react';

const isServer = typeof window === 'undefined';
const baseURL = isServer 

  ? (process.env.API_URL || 'http://api:8000/api/v1') 
  : (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1');

const api = axios.create({
  baseURL,
  timeout: 20000,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'Accept-Encoding': 'gzip, deflate, br',
  },
  withCredentials: true,
});

api.interceptors.request.use(
  async (config: InternalAxiosRequestConfig) => {
    try {
      const session = await getSession();
      if (session?.accessToken && config.headers) {
        config.headers.Authorization = `Bearer ${session.accessToken}`;
      }
    } catch (error) {
   
      if (isServer) console.warn('[API] Failed to get session on server side:', error);
    }
    return config;
  },
  (error) => Promise.reject(error)
);

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    if (error.code === 'ECONNREFUSED') {
        console.error(`�� [API FATAL] Connection Refused to ${baseURL}.`);
    }
    return Promise.reject(error);
  }
);

export { api };
