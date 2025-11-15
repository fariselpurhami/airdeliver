//** apps/web/lib/api.ts **//

import axios from 'axios';
import { getSession } from 'next-auth/react';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '/api/v1';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use(
  async (config) => {
    const session = await getSession();
    const token = session?.accessToken;

    if (token && !config.headers['Authorization']) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const errorData = error.response?.data || { detail: error.message };
    const customError = new Error(errorData.detail || 'An API error occurred.');
    (customError as any).status = error.response?.status;
    (customError as any).info = errorData;
    return Promise.reject(customError);
  }
);
