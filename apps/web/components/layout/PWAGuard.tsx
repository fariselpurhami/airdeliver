'use client';

import { type ReactNode, useEffect } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { useDeviceDetection } from '@/hooks/usePWAInstall';

export interface PWAGuardProps {
  /** The application content to guard. */
  readonly children: ReactNode;
  /** Optional fallback UI to prevent FOUC (Flash of Unstyled Content) during device detection hydration. */
  readonly fallback?: ReactNode;
}

/**
 * PWAGuard
 * 
 * Enforces Progressive Web App (PWA) usage constraints.
 * Redirects mobile web users (non-standalone) on deep links back to the root ('/') 
 * to guide them through the PWA installation or primary funnel.
 */
export default function PWAGuard({ children, fallback = null }: PWAGuardProps) {
  const { isMobile, isStandalone, mounted } = useDeviceDetection();
  const pathname = usePathname();
  const router = useRouter();

  // Encapsulate the business rule: we only redirect if we have hydrated (mounted),
  // the device is mobile, it is running in a standard browser (!isStandalone),
  // and the user is attempting to access a route other than the root.
  const requiresRedirect = mounted && isMobile && !isStandalone && pathname !== '/';

  useEffect(() => {
    if (requiresRedirect) {
      // Use replace() to avoid polluting the browser history stack with protected routes
      router.replace('/');
    }
  }, [requiresRedirect, router]);

  // Phase 1: Await hydration and device capability detection.
  // Returning a fallback prevents hydration mismatches and suppresses layout shifts (FOUC).
  if (!mounted) {
    return <>{fallback}</>;
  }

  // Phase 2: Intercept render if a redirect is actively in progress.
  // We return null to ensure restricted content never leaks to the DOM.
  if (requiresRedirect) {
    return null;
  }

  // Phase 3: Authorization successful.
  // Desktop users, installed PWA users, or users on the root index pass through.
  return <>{children}</>;
}
