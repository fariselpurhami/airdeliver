// frontend/web/__tests__/HomePage.test.tsx
//
// Characterizes the landing page as it exists today. The page itself
// (app/(main)/page.tsx) is an async server component that reads headers(),
// so the tests render the client tree it delegates to: LandingClient.

import fs from 'fs';
import type * as JestGlobals from '@jest/globals';
import '@testing-library/jest-dom/jest-globals';
import { render, screen, fireEvent } from '@testing-library/react';
import { LandingClient } from '../app/(main)/_components/LandingClient';
import { useAIOrderingStore } from '@/hooks/useAIOrderingStore';
import { useUIStore } from '@/hooks/useUIStore';

jest.mock('@/hooks/useAIOrderingStore');
jest.mock('@/hooks/useUIStore');

const mockSetOverlayVisible = jest.fn();
const mockShowProductOverlay = jest.fn();
const mockHideProductOverlay = jest.fn();

const renderLanding = () =>
  render(<LandingClient nonce="test-nonce" initialTraceId="test-trace" />);

describe('HomePage', () => {
  beforeEach(() => {
    mockSetOverlayVisible.mockClear();
    mockShowProductOverlay.mockClear();
    mockHideProductOverlay.mockClear();

    // Zustand-style mocks: support both useStore() and useStore(selector).
    const aiState = {
      messages: [],
      isLoading: false,
      isProcessing: false,
      paymentDetails: null,
      glowingProductId: null,
      socketStatus: 'disconnected',
      flyQueue: [],
      removeFlyItem: jest.fn(),
      setOverlayVisible: mockSetOverlayVisible,
      sendMessage: jest.fn(),
      sendImage: jest.fn(),
      addProductById: jest.fn(),
      removeProductById: jest.fn(),
      resetChat: jest.fn(),
      initiateCheckoutRecovery: jest.fn(),
      confirmCurrentOrder: jest.fn(),
      clearCart: jest.fn(),
      restoreCheckout: jest.fn(),
      saveForLater: jest.fn(),
      hardCancelOrder: jest.fn(),
      addSocketAIMessage: jest.fn(),
      connectSocket: jest.fn(),
      disconnectSocket: jest.fn(),
    };
    (useAIOrderingStore as unknown as ReturnType<typeof JestGlobals.jest.fn>).mockImplementation(
      ((selector?: unknown) =>
        typeof selector === 'function'
          ? (selector as (state: typeof aiState) => unknown)(aiState)
          : aiState) as (...args: unknown[]) => unknown
    );

    const uiState = {
      showProductOverlay: mockShowProductOverlay,
      hideProductOverlay: mockHideProductOverlay,
    };
    (useUIStore as unknown as ReturnType<typeof JestGlobals.jest.fn>).mockImplementation(
      ((selector?: unknown) =>
        typeof selector === 'function'
          ? (selector as (state: typeof uiState) => unknown)(uiState)
          : uiState) as (...args: unknown[]) => unknown
    );
  });

  it('renders the main headline', () => {
    const view=renderLanding();
    const badge=screen.getByText('AI-SECURED ORDERS');
    const headline = screen.getByRole('heading', {
      name: /shopping at the\s+speed of thought/i,
    });
    expect(headline).toBeInTheDocument();
    expect(badge.compareDocumentPosition(headline)&Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    if(process.env.HOME_BADGE_PREVIEW)fs.writeFileSync('/tmp/home-badge-render.html','<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"><link rel="stylesheet" href="file:///tmp/home-layer.css"></head><body style="margin:0;background:#04060a;color:white">'+view.container.innerHTML+'</body></html>');
  });

  it('renders the main action buttons', () => {
    renderLanding();
    expect(screen.getByRole('button', { name: /start ai order/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /explore trending products/i })).toBeInTheDocument();
  });

  it('renders all main page sections', () => {
    renderLanding();
    expect(screen.getByRole('heading', { name: /how it\s+works/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /future of commerce/i })).toBeInTheDocument();
  });

  it('calls the AI ordering store when the order button is clicked', () => {
    renderLanding();
    const orderButton = screen.getByRole('button', { name: /start ai order/i });
    fireEvent.click(orderButton);
    expect(mockSetOverlayVisible).toHaveBeenCalledTimes(1);
    expect(mockSetOverlayVisible).toHaveBeenCalledWith(true);
  });

  it('calls the UI store when "Explore trending products" is clicked', () => {
    renderLanding();
    const exploreButton = screen.getByRole('button', { name: /explore trending products/i });
    fireEvent.click(exploreButton);
    expect(mockShowProductOverlay).toHaveBeenCalledTimes(1);
  });

  it('renders the HowItWorks steps', () => {
    renderLanding();
    expect(screen.getByText('AI Intent Recognition')).toBeInTheDocument();
    expect(screen.getByText('Inventory Sync')).toBeInTheDocument();
    expect(screen.getByText('Multimodal Visual Matching')).toBeInTheDocument();
    expect(screen.getByText('Autonomous One-Tap Checkout')).toBeInTheDocument();
  });

  it('renders the final CTA', () => {
    renderLanding();
    expect(screen.getByRole('link', { name: /sign up/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /download app/i })).toBeInTheDocument();
  });

  it('renders the trusted partners strip', () => {
    renderLanding();
    expect(
      screen.getByText(/Trusted by NVIDIA, STRIPE, AWS, CLOUDFLARE, and MASTERCARD/i)
    ).toBeInTheDocument();
  });
});
