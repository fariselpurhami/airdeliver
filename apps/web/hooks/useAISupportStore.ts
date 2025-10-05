import { create } from 'zustand';

interface AISupportState {
  isSupportOpen: boolean;
  openSupport: () => void;
  closeSupport: () => void;
}

export const useAISupportStore = create<AISupportState>((set) => ({
  isSupportOpen: false,
  openSupport: () => set({ isSupportOpen: true }),
  closeSupport: () => set({ isSupportOpen: false }),
}));
