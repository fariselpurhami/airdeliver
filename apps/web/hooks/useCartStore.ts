import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { type Product } from '@/components/products/product-card';

// Define the shape of an item in the cart, adding a 'quantity' property
export interface CartItem extends Product {
  quantity: number;
}

// Define the shape of the store's state and its actions
interface CartState {
  items: CartItem[];
  addToCart: (product: Product) => void;
  removeFromCart: (productId: number) => void;
  clearCart: () => void;
}

export const useCartStore = create<CartState>()(
  // Use 'persist' to save the cart to localStorage
  persist(
    (set, get) => ({
      items: [],
      addToCart: (product) => {
        const currentItems = get().items;
        const existingItem = currentItems.find((item) => item.id === product.id);

        if (existingItem) {
          // If the product is already in the cart, increase its quantity
          set({
            items: currentItems.map((item) =>
              item.id === product.id
                ? { ...item, quantity: item.quantity + 1 }
                : item
            ),
          });
        } else {
          // If it's a new product, add it to the cart with a quantity of 1
          set({ items: [...currentItems, { ...product, quantity: 1 }] });
        }
      },
      removeFromCart: (productId) => {
        set({
          items: get().items.filter((item) => item.id !== productId),
        });
      },
      clearCart: () => set({ items: [] }),
    }),
    {
      name: 'airdeliver-cart-storage', // A unique name for the storage item
      storage: createJSONStorage(() => localStorage),
    }
  )
);
