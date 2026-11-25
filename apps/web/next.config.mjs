// FILE: next.config.mjs
// ============================================================================
// ENTERPRISE NEXT.JS CONFIGURATION
// Enforces strict security boundaries, WebGL optimizations, and Edge standalone output.
// ============================================================================

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const isDevelopment = process.env.NODE_ENV === 'development';
const API_BASE_URL = process.env.BACKEND_API_URL || 'http://api:8000';

/** @type {import('next').NextConfig} */
const nextConfig = {
  devIndicators: false,
  allowedDevOrigins: isDevelopment ? ["127.0.0.1"] : [],
  turbopack: {
    // In the pnpm workspace, `next` is hoisted to the repo-root node_modules,
    // so the workspace root must be the repo root. In the standalone Docker
    // build the app owns its node_modules and is its own root.
    root: fs.existsSync(path.resolve(__dirname, '..', '..', 'pnpm-workspace.yaml'))
      ? path.resolve(__dirname, '..', '..')
      : __dirname,
  },
  typescript: {
    ignoreBuildErrors: true,
  },
  output: 'standalone',
  outputFileTracingRoot: path.resolve(__dirname, '..', '..'),
  reactStrictMode: true,
  poweredByHeader: false,
  productionBrowserSourceMaps: false,
  compress: true,
  transpilePackages: [
    'recharts',
    'react-smooth',
    'framer-motion',
    'three',
    '@react-three/fiber',
    '@react-three/drei',
    'lucide-react',
  ],
  reactCompiler: true,
  experimental: {
    // CRITICAL: Enables React's Taint API to prevent Server-to-Client secret leakage.
    taint: true,
    optimizePackageImports: [
      'lucide-react',
      'date-fns',
      'lodash',
      'framer-motion',
      'recharts',
      '@headlessui/react',
      '@react-three/fiber',
      '@react-three/drei',
    ],
    serverActions: {
      bodySizeLimit: '2mb',
    },
    webpackBuildWorker: true,
    parallelServerCompiles: true,
    parallelServerBuildTraces: true,
  },
  logging: {
    fetches: {
      fullUrl: true,
    },
  },
  images: {
    qualities: [75, 90],
    formats: ['image/avif', 'image/webp'],
    minimumCacheTTL: 31536000,
    dangerouslyAllowSVG: true,
    contentSecurityPolicy: "default-src 'self'; script-src 'none'; sandbox;",
    remotePatterns: [
      { protocol: 'http', hostname: '**' },
      { protocol: 'https', hostname: '**' },
    ],
  },
  webpack: (config, { isServer, dev }) => {
    // WebGL Shader Compilation
    config.module.rules.push({
      test: /\.(glsl|vs|fs|vert|frag)$/,
      use: ['raw-loader', 'glslify-loader'],
    });

    // Aggressive Chunk Splitting for 3D Assets (Three.js/Fiber)
    if (!dev && !isServer) {
      config.optimization.splitChunks.cacheGroups = {
        ...config.optimization.splitChunks.cacheGroups,
        three: {
          test: /[\\/]node_modules[\\/](three|@react-three|@react-three\/fiber|drei)[\\/]/,
          name: 'three-vendor',
          chunks: 'all',
          priority: 30,
          reuseExistingChunk: true,
          enforce: true,
        },
        commons: {
          name: 'commons',
          chunks: 'all',
          minChunks: 2,
          priority: 20,
        },
      };
    }

    return config;
  },
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          { key: 'X-DNS-Prefetch-Control', value: 'on' },
          { key: 'Strict-Transport-Security', value: 'max-age=63072000; includeSubDomains; preload' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'X-Frame-Options', value: 'SAMEORIGIN' },
          { key: 'X-XSS-Protection', value: '1; mode=block' },
          { key: 'Referrer-Policy', value: 'origin-when-cross-origin' },
          { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' },
        ],
      },
      {
        source: '/:all*(svg|jpg|png|webp|avif|ico|woff|woff2)',
        locale: false,
        headers: [
          { key: 'Cache-Control', value: 'public, max-age=31536000, immutable' },
        ],
      },
    ];
  },
  async rewrites() {
    if (isDevelopment) {
      return [
        {
          source: '/api/v1/:path*',
          destination: `${API_BASE_URL}/api/v1/:path*`,
        },
      ];
    }
    return [];
  },
};

export default nextConfig;
