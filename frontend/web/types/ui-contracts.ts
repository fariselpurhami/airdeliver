// ============================================================================
// FILE: frontend/web/types/ui-contracts.ts
// ============================================================================
import { z } from 'zod';

export const TrackingPayloadSchema = z.object({
  traceId: z.string().uuid(),
  timestamp: z.number(),
  event: z.enum(['MOUNT', 'INTERACTION', 'ERROR']),
  metadata: z.record(z.string(), z.unknown()).optional(),
});

export type UIState = 
  | { status: 'IDLE' }
  | { status: 'AI_OVERLAY_ACTIVE'; traceId: string }
  | { status: 'PRODUCT_OVERLAY_ACTIVE'; traceId: string }
  | { status: 'MOBILE_PWA_VIEW' }
  | { status: 'FATAL_ERROR'; message: string };

export type UIAction =
  | { type: 'OPEN_AI_CART'; payload: { traceId: string } }
  | { type: 'OPEN_PRODUCTS'; payload: { traceId: string } }
  | { type: 'CLOSE_OVERLAYS' }
  | { type: 'FORCE_MOBILE_VIEW' }
  | { type: 'REPORT_ERROR'; payload: { message: string } };

export const uiStateReducer = (state: UIState, action: UIAction): UIState => {
  switch (action.type) {
    case 'OPEN_AI_CART':
      if (state.status === 'FATAL_ERROR') return state;
      return { status: 'AI_OVERLAY_ACTIVE', traceId: action.payload.traceId };
    case 'OPEN_PRODUCTS':
      if (state.status === 'FATAL_ERROR') return state;
      return { status: 'PRODUCT_OVERLAY_ACTIVE', traceId: action.payload.traceId };
    case 'CLOSE_OVERLAYS':
      if (state.status === 'FATAL_ERROR' || state.status === 'MOBILE_PWA_VIEW') return state;
      return { status: 'IDLE' };
    case 'FORCE_MOBILE_VIEW':
      return { status: 'MOBILE_PWA_VIEW' };
    case 'REPORT_ERROR':
      return { status: 'FATAL_ERROR', message: action.payload.message };
    default:
      return state;
  }
};
