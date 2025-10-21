// file: hooks/useUIStore.ts

import { create } from 'zustand';

interface UIState {
  isProductOverlayVisible: boolean;
  showProductOverlay: () => void;
  hideProductOverlay: () => void;
}

export const useUIStore = create<UIState>((set) => ({
  isProductOverlayVisible: false,
  showProductOverlay: () => set({ isProductOverlayVisible: true }),
  hideProductOverlay: () => set({ isProductOverlayVisible: false }),
}));
