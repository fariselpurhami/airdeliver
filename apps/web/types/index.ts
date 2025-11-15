//** apps/web/types/index.ts **//

export interface Product {
  id: number;
  name: string;
  description: string;
  price: number;
  image_url: string | null;
  inventory: number;
  predicted_delivery?: string;
  trending_status?: string;
  stock_level?: string;
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

export interface WebSocketNotification {
  id?: number;
  title: string;
  body: string;
  type: 'security' | 'order_update' | 'payment' | 'ai_agent' | 'default';
  created_at: string;
}

export interface TelemetryPayload {
  lat: number;
  lon: number;
  alt_m: number;
  ground_speed_m_s: number;
  battery_pct: number;
  mission_id?: string | null;
  flight_mode?: string | null;
  flags?: string[] | null;
}
