//** apps/web/next.config.mjs **//

import path from 'path';
import { fileURLToPath } from 'url';
import withPWAInit from 'next-pwa';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const isDevelopment = process.env.NODE_ENV === 'development';

const API_BASE_URL = process.env.BACKEND_API_URL || 'http://api:8000';

const nextConfig = {
  output: 'standalone',

  experimental: {
    outputFileTracingRoot: path.join(__dirname, '../../'),
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

  reactStrictMode: true,
  images: {
    remotePatterns: [
      {
        protocol: 'http',
        hostname: 'localhost',
        port: '8000',
        pathname: '/**',
      },
      {
        protocol: 'http',
        hostname: 'api',
        port: '8000',
        pathname: '/**',
      },
      {
        protocol: 'https',
        hostname: 'api.airdeliver.com',
        pathname: '/**',
      },
      {
        protocol: 'https',
        hostname: 'ui-avatars.com',
        pathname: '/api/**',
      },
      {
        protocol: 'https',
        hostname: 'placehold.co',
        pathname: '/**',
      },
    ],
  },
};

const withPWA = withPWAInit({
  dest: 'public',
  disable: isDevelopment,
  register: true,
  skipWaiting: true,
});

export default withPWA(nextConfig);
