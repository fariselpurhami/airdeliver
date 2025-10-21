// file: apps/web/next.config.mjs (مع تفعيل register و skipWaiting)

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
};

const pwaConfig = withPWA({
  dest: 'public',
  disable: process.env.NODE_ENV === 'development',
  register: true, // <-- تم تفعيله
  skipWaiting: true, // <-- تم تفعيله
});

export default pwaConfig(nextConfig);
