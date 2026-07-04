// apps/web/components/ui/CinematicBackground.tsx
'use client';

import React, {
  useRef,
  useState,
  useEffect,
  useMemo,
  useCallback,
  Suspense,
  memo,
} from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import {
  Stars,
  Preload,
  AdaptiveDpr,
  AdaptiveEvents,
  PerformanceMonitor,
} from '@react-three/drei';
import * as THREE from 'three';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface DeviceProfile {
  targetFps: number;
  starCount: number;
  dprRange: [number, number];
}

// ---------------------------------------------------------------------------
// Device capability heuristic (runs once, no re-render cost)
// ---------------------------------------------------------------------------

function getDeviceProfile(): DeviceProfile {
  if (typeof navigator === 'undefined') {
    return { targetFps: 60, starCount: 3000, dprRange: [1, 2] };
  }

  const cores = navigator.hardwareConcurrency ?? 4;
  const mem = (navigator as unknown as { deviceMemory?: number }).deviceMemory ?? 4;
  const isLowEnd = cores <= 4 || mem <= 4;

  return isLowEnd
    ? { targetFps: 30, starCount: 1500, dprRange: [1, 1.5] }
    : { targetFps: 60, starCount: 3500, dprRange: [1, 2] };
}

function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    setReduced(mq.matches);
    const handler = (e: MediaQueryListEvent) => setReduced(e.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);

  return reduced;
}

function useInViewport<T extends HTMLElement>(): [React.RefObject<T>, boolean] {
  const ref = useRef<T>(null);
  const [inView, setInView] = useState(true);

  useEffect(() => {
    const node = ref.current;
    if (!node || typeof IntersectionObserver === 'undefined') return;

    const observer = new IntersectionObserver(
      ([entry]) => setInView(entry.isIntersecting),
      { threshold: 0 }
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  return [ref, inView];
}

function useDocumentVisible(): boolean {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const handler = () => setVisible(document.visibilityState === 'visible');
    document.addEventListener('visibilitychange', handler);
    return () => document.removeEventListener('visibilitychange', handler);
  }, []);

  return visible;
}

// ---------------------------------------------------------------------------
// Animated scene contents
// ---------------------------------------------------------------------------

interface BackgroundLogicProps {
  active: boolean;
  targetFps: number;
  starCount: number;
}

const BackgroundLogic = memo(function BackgroundLogic({
  active,
  targetFps,
  starCount,
}: BackgroundLogicProps) {
  const light1Ref = useRef<THREE.PointLight>(null!);
  const light2Ref = useRef<THREE.PointLight>(null!);
  const elapsedRef = useRef(0);
  const frameInterval = 1 / targetFps;

  const fogArgs = useMemo<[THREE.ColorRepresentation, number, number]>(
    () => ['#000000', 20, 55],
    []
  );

  useFrame((state, delta) => {
    if (!active) return;

    elapsedRef.current += delta;
    if (elapsedRef.current < frameInterval) return;
    elapsedRef.current = 0;

    const time = state.clock.elapsedTime;

    if (light1Ref.current) {
      light1Ref.current.position.set(
        Math.sin(time * 0.5) * 20,
        Math.cos(time * 0.5) * 20,
        Math.cos(time * 0.5) * 15
      );
    }

    if (light2Ref.current) {
      light2Ref.current.position.set(
        Math.sin(time * 0.3) * -20,
        Math.cos(time * 0.3) * -20,
        Math.sin(time * 0.3) * 10
      );
    }
  });

  return (
    <>
      <fog attach="fog" args={fogArgs} />

      <ambientLight intensity={0.15} />

      <pointLight
        ref={light1Ref}
        color="#22d3ee"
        intensity={2.2}
        distance={60}
        decay={2}
        castShadow={false}
      />

      <pointLight
        ref={light2Ref}
        color="#a855f7"
        intensity={2.2}
        distance={60}
        decay={2}
        castShadow={false}
      />

      <Stars
        radius={100}
        depth={50}
        count={starCount}
        factor={4}
        saturation={0}
        fade
        speed={active ? 1 : 0}
      />

      <Preload all />
    </>
  );
});

// ---------------------------------------------------------------------------
// GL configuration + context-loss resilience
// ---------------------------------------------------------------------------

function GLSafeguard() {
  const { gl } = useThree();

  useEffect(() => {
    const canvas = gl.domElement;

    const handleLost = (e: Event) => {
      e.preventDefault();
    };
    const handleRestored = () => {
      gl.forceContextRestore?.();
    };

    canvas.addEventListener('webglcontextlost', handleLost, false);
    canvas.addEventListener('webglcontextrestored', handleRestored, false);

    return () => {
      canvas.removeEventListener('webglcontextlost', handleLost);
      canvas.removeEventListener('webglcontextrestored', handleRestored);
    };
  }, [gl]);

  return null;
}

// ---------------------------------------------------------------------------
// Static fallback (reduced motion / WebGL unavailable)
// ---------------------------------------------------------------------------

const StaticFallback = memo(function StaticFallback() {
  return (
    <div
      aria-hidden="true"
      className="absolute inset-0 bg-black"
      style={{
        backgroundImage:
          'radial-gradient(circle at 20% 20%, rgba(34,211,238,0.15), transparent 60%), radial-gradient(circle at 80% 80%, rgba(168,85,247,0.15), transparent 60%)',
      }}
    />
  );
});

// ---------------------------------------------------------------------------
// Root component
// ---------------------------------------------------------------------------

function supportsWebGL(): boolean {
  if (typeof window === 'undefined') return false;
  try {
    const canvas = document.createElement('canvas');
    return !!(
      window.WebGLRenderingContext &&
      (canvas.getContext('webgl') || canvas.getContext('experimental-webgl'))
    );
  } catch {
    return false;
  }
}

const CinematicBackground = memo(function CinematicBackground() {
  const [containerRef, inView] = useInViewport<HTMLDivElement>();
  const isDocVisible = useDocumentVisible();
  const prefersReducedMotion = usePrefersReducedMotion();
  const [webglOk, setWebglOk] = useState(true);

  const profile = useMemo(getDeviceProfile, []);

  useEffect(() => {
    setWebglOk(supportsWebGL());
  }, []);

  const active = inView && isDocVisible && !prefersReducedMotion;

  const glOptions = useMemo(
    () => ({
      antialias: false,
      alpha: true,
      stencil: false,
      depth: true,
      powerPreference: 'high-performance' as const,
      preserveDrawingBuffer: false,
    }),
    []
  );

  const handleCreated = useCallback(
    ({ gl }: { gl: THREE.WebGLRenderer }) => {
      gl.setClearColor(0x000000, 0);
    },
    []
  );

  return (
    <div
      ref={containerRef}
      className="fixed inset-0 -z-10 h-full w-full overflow-hidden"
    >
      {webglOk && !prefersReducedMotion ? (
        <Canvas
          gl={glOptions}
          dpr={profile.dprRange}
          camera={{ position: [0, 0, 20], fov: 75, near: 0.1, far: 100 }}
          frameloop={active ? 'always' : 'never'}
          onCreated={handleCreated}
        >
          <PerformanceMonitor>
            <AdaptiveDpr pixelated={false} />
            <AdaptiveEvents />
            <GLSafeguard />
            <Suspense fallback={null}>
              <BackgroundLogic
                active={active}
                targetFps={profile.targetFps}
                starCount={profile.starCount}
              />
            </Suspense>
          </PerformanceMonitor>
        </Canvas>
      ) : (
        <StaticFallback />
      )}

      <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-black" />
    </div>
  );
});

export default CinematicBackground;
