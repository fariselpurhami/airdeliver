//** apps/web/next.config.mjs **//

import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const isDevelopment = process.env.NODE_ENV === 'development';
const API_BASE_URL = process.env.BACKEND_API_URL || 'http://api:8000';

/** @type {import('next').NextConfig} */

const nextConfig = {
  output: 'standalone',
  reactStrictMode: true,

  poweredByHeader: false,
  productionBrowserSourceMaps: false,

  compress: true,

  outputFileTracingRoot: path.join(__dirname, '../../'),
  transpilePackages: [
    'recharts',
    'react-smooth',
    'framer-motion',
    'three',
    '@react-three/fiber',
    '@react-three/drei',
    'lucide-react'
  ],

  experimental: {

    reactCompiler: true,

    turbo: {
      rules: {
        '*.glsl': {
          loaders: ['raw-loader'],
          as: '*.js',
        },
        '*.vs': {
          loaders: ['raw-loader'],
          as: '*.js',
        },
        '*.fs': {
          loaders: ['raw-loader'],
          as: '*.js',
        },
      },
      resolveAlias: {
      },
    },
    
    optimizePackageImports: [
      'lucide-react',
      'date-fns',
      'lodash',
      'framer-motion',
      'recharts',
      '@headlessui/react',
      '@react-three/fiber', 
      '@react-three/drei'
    ],
    
    serverActions: {
      bodySizeLimit: '2mb',
    },
    
    webpackBuildWorker: true,
    parallelServerCompiles: true,

    parallelServerBuildTraces: true,
    optimizeCss: true, 
  },

  logging: {
    fetches: {
      fullUrl: true,
    },
  },

  images: {
    formats: ['image/avif', 'image/webp'],
    minimumCacheTTL: 31536000, 
    dangerouslyAllowSVG: true,
    contentSecurityPolicy: "default-src 'self'; script-src 'none'; sandbox;",
    remotePatterns: [
      { protocol: 'http', hostname: 'localhost', port: '8000', pathname: '/**' },
      { protocol: 'http', hostname: 'api', port: '8000', pathname: '/**' },
      { protocol: 'https', hostname: 'api.airdeliver.com', pathname: '/**' },
      { protocol: 'https', hostname: 'ui-avatars.com', pathname: '/api/**' },
      { protocol: 'https', hostname: 'placehold.co', pathname: '/**' },
    ],
  },

  webpack: (config, { isServer, dev }) => {

    config.module.rules.push({
      test: /\.(glsl|vs|fs|vert|frag)$/,
      use: ['raw-loader', 'glslify-loader'],
    });

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

    config.module.rules.push({
      test: /\.(glsl|vs|fs|vert|frag)$/,
      use: ['raw-loader', 'glslify-loader'],
    });

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
          { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' } 
        ]
      },

      {
        source: '/:all*(svg|jpg|png|webp|avif|ico|woff|woff2)',
        locale: false,
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=31536000, immutable',
          },
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
