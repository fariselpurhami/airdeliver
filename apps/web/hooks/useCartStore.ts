
import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { type Product } from '@/types';

export interface CartItem extends Product {
  quantity: number;
}

interface CartState {
  items: CartItem[];
  addToCart: (product: Product) => void;
  removeFromCart: (productId: number) => void;
  clearCart: () => void;
  replaceItems: (items: CartItem[]) => void;
}

export const useCartStore = create<CartState>()(

  persist(
    (set, get) => ({
      items: [],
      addToCart: (product) => {
        const currentItems = get().items;
        const existingItem = currentItems.find((item) => item.id === product.id);

        if (existingItem) {

          set({
            items: currentItems.map((item) =>
              item.id === product.id
                ? { ...item, quantity: item.quantity + 1 }
                : item
            ),
          });
        } else {
         
          set({ items: [...currentItems, { ...product, quantity: 1 }] });
        }
      },
      removeFromCart: (productId) => {
        set({
          items: get().items.filter((item) => item.id !== productId),
        });
      },
      clearCart: () => set({ items: [] }),
      replaceItems: (items) => set({ items }),
    }),
    {
      name: 'airdeliver-cart-storage', 
      storage: createJSONStorage(() => localStorage),
    }
  )
);
