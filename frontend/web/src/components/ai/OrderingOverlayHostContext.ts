'use client';
import { createContext } from 'react';
// Pages retain their entry points. Only the shell owns the live connection.
export const OrderingOverlayHostContext = createContext(false);
