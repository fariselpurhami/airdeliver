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
