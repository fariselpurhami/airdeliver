// apps/web/lib/api.ts

import axios from 'axios';
import { getSession } from 'next-auth/react';

const api = axios.create({
  baseURL: '/',
});

api.interceptors.request.use(async (config) => {
  const session = await getSession();
  if (session?.accessToken) {
    config.headers.Authorization = `Bearer ${session.accessToken}`;
  }
  return config;
});

export { api };
