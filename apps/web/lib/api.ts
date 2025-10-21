// file: apps/web/lib/api.ts
// CORRECTED VERSION

import axios from 'axios';
import { getSession } from 'next-auth/react';

const api = axios.create({
  // Use a relative path to make requests go through the Next.js proxy.
  baseURL: '/api/v1',
});

api.interceptors.request.use(async (config) => {
  const session = await getSession();
  if (session?.accessToken) {
    config.headers.Authorization = `Bearer ${session.accessToken}`;
  }
  return config;
});

export { api };
