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

jest.mock('framer-motion', () => ({
  ...jest.requireActual('framer-motion'),
  useInView: () => true,
  useScroll: () => ({ scrollYProgress: { get: () => 0, on: () => {} } }),
  useTransform: () => 0,
  useSpring: (val) => val,
  motion: {
    div: ({ children, ...props }) => <div {...props}>{children}</div>,
    h1: ({ children, ...props }) => <h1 {...props}>{children}</h1>,
    h2: ({ children, ...props }) => <h2 {...props}>{children}</h2>,
    p: ({ children, ...props }) => <p {...props}>{children}</p>,
    span: ({ children, ...props }) => <span {...props}>{children}</span>,
  },
  AnimatePresence: ({ children }) => <>{children}</>,
}));

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
