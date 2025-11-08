// file: apps/web/lib/api.ts
import axios from 'axios';
import { getSession } from 'next-auth/react';

const api = axios.create({
  // This is the correct, standardized base URL
  baseURL: process.env.NEXT_PUBLIC_API_URL || '/api/v1',
});

api.interceptors.request.use(async (config) => {
  const session = await getSession();
  if (session?.accessToken) {
    config.headers.Authorization = `Bearer ${session.accessToken}`;
  }
  return config;
});

export { api };
