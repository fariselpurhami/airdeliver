/** apps/web/jest.setup.js **/

import '@testing-library/jest-dom';

global.ResizeObserver = class ResizeObserver {
  constructor(callback) { this.callback = callback; }
  observe(target) { }
  unobserve(target) { }
  disconnect() { }
};

global.IntersectionObserver = class IntersectionObserver {
  constructor(callback) { this.callback = callback; }
  observe(target) { }
  unobserve(target) { }
  disconnect() { }
};

Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(),
    removeListener: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

jest.mock('framer-motion', () => {
  const React = jest.requireActual('react');
  // framer-motion-only props that must not reach DOM elements
  const MOTION_PROPS = new Set([
    'initial', 'animate', 'exit', 'variants', 'transition', 'whileInView',
    'whileHover', 'whileTap', 'whileFocus', 'whileDrag', 'viewport', 'drag',
    'dragConstraints', 'dragElastic', 'dragMomentum', 'layout', 'layoutId',
    'onAnimationStart', 'onAnimationComplete', 'style',
  ]);
  const strip = (props) => {
    const clean = {};
    for (const [k, v] of Object.entries(props)) {
      if (!MOTION_PROPS.has(k)) clean[k] = v;
    }
    return clean;
  };
  return {
    ...jest.requireActual('framer-motion'),
    useInView: () => true,
    useReducedMotion: () => true,
    useScroll: () => ({ scrollYProgress: { get: () => 0, on: () => {} } }),
    useTransform: () => 0,
    useSpring: (val) => val,
    useAnimation: () => ({ start: jest.fn(), set: jest.fn(), stop: jest.fn() }),
    // Any motion.<tag> renders as the plain tag with motion props stripped.
    motion: new Proxy({}, {
      get: (target, tag) => {
        if (typeof tag !== 'string') return undefined;
        const Component = ({ children, ...props }) =>
          React.createElement(tag, strip(props), children);
        Component.displayName = `motion.${tag}`;
        return Component;
      },
    }),
    AnimatePresence: ({ children }) => React.createElement(React.Fragment, null, children),
  };
});

jest.mock('@react-three/fiber', () => ({
  ...jest.requireActual('@react-three/fiber'),
  Canvas: ({ children }) => <div>{children}</div>,
  useFrame: () => {},
  useThree: () => ({
  gl: { dispose: jest.fn() },
  viewport: { width: 100, height: 100 },
  camera: { position: [0, 0, 0] },
}),
}));

jest.mock('@react-three/drei', () => ({
  ...jest.requireActual('@react-three/drei'),
  Preload: () => null,
  Float: ({ children }) => <div>{children}</div>,
  Line: () => null,
  Text: () => null,
  useTexture: () => null,
  OrbitControls: () => null,
  Html: ({ children }) => <div>{children}</div>,
}));

jest.mock('embla-carousel-react', () => () => [jest.fn(), null]);

// next-auth v5 is ESM-only and next/jest's default transformIgnorePatterns
// cannot be overridden, so the auth client is mocked in tests.
jest.mock('next-auth/react', () => ({
  useSession: () => ({ data: null, status: 'unauthenticated' }),
  signIn: jest.fn(),
  signOut: jest.fn(),
  getSession: jest.fn(() => Promise.resolve(null)),
  SessionProvider: ({ children }) => children,
}));

// react-markdown and remark-gfm are ESM-only; mock them in tests.
jest.mock('react-markdown', () => ({
  __esModule: true,
  default: ({ children }) => children,
}));
jest.mock('remark-gfm', () => ({ __esModule: true, default: () => null }));

// App Router hooks need a mounted router; mock navigation in tests.
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    prefetch: jest.fn(),
    back: jest.fn(),
    forward: jest.fn(),
    refresh: jest.fn(),
  }),
  usePathname: () => '/',
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({}),
  redirect: jest.fn(),
  notFound: jest.fn(),
}));
