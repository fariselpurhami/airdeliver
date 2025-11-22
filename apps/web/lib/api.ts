// file: apps/web/lib/api.ts

import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { getSession, signOut } from 'next-auth/react';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000, 
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  },
});

api.interceptors.request.use(
  async (config: InternalAxiosRequestConfig) => {
   
    const session = await getSession();
    if (session?.accessToken && config.headers) {
      config.headers.Authorization = `Bearer ${session.accessToken}`;
    }
    return config;
  },
  (error) => {
    console.error('[API Request Error]:', error);
    return Promise.reject(error);
  }
);

api.interceptors.response.use(
  (response) => {
    
    return response;
  },
  async (error: AxiosError) => {
    
    if (error.response?.status === 401) {

        console.warn('[API] Unauthorized access detected.');
    }

    if (error.response?.status && error.response.status >= 500) {
        console.error('[API] Critical Server Error:', error.message);
    }

    return Promise.reject(error);
  }
);

export { api };
