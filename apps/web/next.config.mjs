//** apps/web/next.config.mjs **//

import path from 'path';
import { fileURLToPath } from 'url';
import withPWAInit from 'next-pwa';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const nextConfig = {
  output: 'standalone',

  experimental: {
    outputFileTracingRoot: path.join(__dirname, '../../'),
  },

  reactStrictMode: true,
  images: {
    remotePatterns: [
      {
        protocol: 'http',
        hostname: 'localhost',
        port: '8000',
        pathname: '/static/avatars/**',
      },
      {
        protocol: 'https',
        hostname: 'api.airdeliver.com',
        pathname: '/static/avatars/**',
      },
      {
        protocol: 'https',
        hostname: 'ui-avatars.com',
        pathname: '/api/**',
      },
      {
        protocol: 'https'
        ,
        hostname: 'placehold.co',
        pathname: '/**',
      },
    ],
  },
};

const withPWA = withPWAInit({
  dest: 'public',
  disable: process.env.NODE_ENV === 'development',
  register: true,
  skipWaiting: true,
});

export default withPWA(nextConfig);
