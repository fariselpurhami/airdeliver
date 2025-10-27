// file: apps/web/next.config.mjs (النسخة المصححة)

import withPWA from 'next-pwa';

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: 'http://api:8000/api/v1/:path*',
      },
    ];
  },

  // --- 👇 قسم images لازم يكون هنا (جوه nextConfig) 👇 ---
  images: {
    remotePatterns: [
      {
        protocol: 'http',
        hostname: 'localhost',
        port: '8000', // Port for the API serving images
        pathname: '/static/avatars/**', // Path for user avatars
      },
      // Allow images from ui-avatars.com (used for fallback)
      {
        protocol: 'https',
        hostname: 'ui-avatars.com',
        pathname: '/api/**',
      },
      // Allow images from placehold.co (used for fallback)
      {
        protocol: 'https',
        hostname: 'placehold.co',
        pathname: '/**', // Allow any path from this domain
      },
    ],
  },
  // --- 👆 نهاية قسم images 👆 ---

}; // <-- القوس ده هو اللي بيقفل nextConfig

const pwaConfig = withPWA({
  dest: 'public',
  disable: process.env.NODE_ENV === 'development',
  register: true, // <-- Kept as per original file
  skipWaiting: true, // <-- Kept as per original file
});

export default pwaConfig(nextConfig);
