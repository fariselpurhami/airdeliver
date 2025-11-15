//** apps/web/lib/fetcher.ts **//

import { api } from './api';

export const fetcher = async <T = any>(url: string): Promise<T> => {
  try {
    const res = await api.get<T>(url);
    return res.data;
  } catch (error: any) {
    throw new Error(error.info?.detail || error.message || 'An error occurred while fetching the data.');
  }
};
