// file: apps/web/lib/fetcher.ts

import { getSession } from 'next-auth/react';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '/api/v1';

export const fetcher = async (url: string) => {
    const session = await getSession();
    // @ts-ignore
    const token = session?.accessToken;

    if (!token && !url.includes('/public/')) {
   
    }

    const headers: HeadersInit = {
        'Content-Type': 'application/json',
    };
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const fullUrl = `${API_BASE_URL}${url.startsWith('/') ? '' : '/'}${url}`;

    const res = await fetch(fullUrl, { headers }); 

    if (!res.ok) {
        let errorData;
        try {
            errorData = await res.json();
        } catch (e) {
            errorData = { detail: res.statusText };
        }
        const error = new Error(errorData.detail || 'An error occurred while fetching the data.');
        
        // @ts-ignore
        error.info = errorData;
        // @ts-ignore
        error.status = res.status;
        throw error;
    }

    if (res.status === 204) {
        return null;
    }

    return res.json();
};

