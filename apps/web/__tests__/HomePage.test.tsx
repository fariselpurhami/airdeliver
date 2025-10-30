// apps/web/__tests__/HomePage.test.tsx

import { render, screen, fireEvent } from '@testing-library/react';
import HomePage from '../app/(main)/page';
import { useAIOrderingStore } from '@/hooks/useAIOrderingStore';
import { useUIStore } from '@/hooks/useUIStore';

jest.mock('@/hooks/useAIOrderingStore');
jest.mock('@/hooks/useUIStore');

const mockSetOverlayVisible = jest.fn();
const mockShowProductOverlay = jest.fn();

describe('HomePage', () => {
  beforeEach(() => {
    mockSetOverlayVisible.mockClear();
    mockShowProductOverlay.mockClear();

    (useAIOrderingStore as jest.Mock).mockReturnValue({
      setOverlayVisible: mockSetOverlayVisible,
    });

    (useUIStore as jest.Mock).mockReturnValue({
      showProductOverlay: mockShowProductOverlay,
    });
  });

  it('renders the main headline', () => {
    render(<HomePage />);
    const headline = screen.getByRole('heading', {
      name: /THE FUTURE/i,
    });
    expect(headline).toBeInTheDocument();
  });

  it('renders the main action buttons', () => {
    render(<HomePage />);
    expect(screen.getByRole('button', { name: /Order with AI/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Explore Products/i })).toBeInTheDocument();
  });

  it('renders all main page sections', () => {
    render(<HomePage />);
    expect(screen.getByRole('heading', { name: /How It Works/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Global Scale/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Trusted by Innovators/i })).toBeInTheDocument();
  });

  it('calls the AI ordering store when "Order with AI" is clicked', () => {
    render(<HomePage />);
    const orderButton = screen.getByRole('button', { name: /Order with AI/i });
    fireEvent.click(orderButton);
    expect(mockSetOverlayVisible).toHaveBeenCalledTimes(1);
    expect(mockSetOverlayVisible).toHaveBeenCalledWith(true);
  });

  it('calls the UI store when "Explore Products" is clicked', () => {
    render(<HomePage />);
    const exploreButton = screen.getByRole('button', { name: /Explore Products/i });
    fireEvent.click(exploreButton);
    expect(mockShowProductOverlay).toHaveBeenCalledTimes(1);
  });

  it('renders timeline steps in HowItWorksSection', () => {
    render(<HomePage />);
    expect(screen.getByText('AI Takes Your Order')).toBeInTheDocument();
    expect(screen.getByText('Smart System Finds Best Option')).toBeInTheDocument();
    expect(screen.getByText('Instant Order Tracking')).toBeInTheDocument();
    expect(screen.getByText('Fast, Optimized Delivery')).toBeInTheDocument();
  });

  it('renders counters in GlobalScaleSection', () => {
    render(<HomePage />);
    expect(screen.getByText('Drones in Flight')).toBeInTheDocument();
    expect(screen.getByText('Cities Connected')).toBeInTheDocument();
    expect(screen.getByText('Orders Delivered')).toBeInTheDocument();
  });

  it('renders testimonials in TestimonialsSection', () => {
    render(<HomePage />);
    expect(screen.getByText('Elena M.')).toBeInTheDocument();
    expect(screen.getByText('Kenji T.')).toBeInTheDocument();
    expect(screen.getByText('Fatima Z.')).toBeInTheDocument();
  });
});
