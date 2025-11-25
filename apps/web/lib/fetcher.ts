// apps/web/lib/fetcher.ts

import { api } from '@/lib/api';

export const fetcher = async (url: string) => {
    try {
       
        const response = await api.get(url);
        return response.data;
    } catch (error: any) {
    
        if (error.response) {
            const customError = new Error(error.response.data?.detail || 'An error occurred while fetching data.');
            // @ts-ignore
            customError.info = error.response.data;
            // @ts-ignore
            customError.status = error.response.status;
            throw customError;
        }
        throw error;
    }
};
