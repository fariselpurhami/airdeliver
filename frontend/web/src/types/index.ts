//** frontend/web/types/index.ts **//

export interface Product {
  sku?: string;
  currency?: string;
  rating?: number | null;
  is_active?: boolean;
  attributes?: Record<string, unknown>;
    price_status?: 'listed' | 'unknown';
  id: number;
  name: string;
  description: string;
  price: number;
  image_url: string | null;
  inventory: number;
  predicted_delivery?: string;
  trending_status?: string;
  stock_level?: string;
  stock_status?: string;
  isAIRec?: boolean;
}

export interface Notification {
  id: number;
  title: string;
  body: string;
  type: 'security' | 'order_update' | 'payment' | 'ai_agent' | 'default';
  read: boolean;
  created_at: string;
  timestamp: string;
  cta: string | null;
}

