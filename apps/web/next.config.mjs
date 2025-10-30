// apps/web/next.config.mjs

import withPWA from 'next-pwa';

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

const pwaConfig = withPWA({
  dest: 'public',
  disable: process.env.NODE_ENV === 'development',
  register: true, 
  skipWaiting: true,
});

export default pwaConfig(nextConfig);
