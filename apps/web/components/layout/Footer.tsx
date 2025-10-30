'use client';

import React, { useRef } from 'react';
import Link from 'next/link';
import { motion, useMotionValue, useTransform } from 'framer-motion';
import { Linkedin, Youtube, X, Facebook, Instagram } from 'lucide-react';
import dynamic from 'next/dynamic';

const Chatbot = dynamic(() => import('@/components/ai/Chatbot'), { 
  ssr: false,
  loading: () => <p>Loading...</p> 
});

const Tiktok = (props: React.SVGProps<SVGSVGElement>) => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" {...props}>
    <path d="M12.525.02c1.31-.02 2.61-.01 3.91-.02.08 1.53.63 3.09 1.75 4.17 1.12 1.11 2.7 1.62 4.24 1.79v4.03c-1.44-.05-2.89-.35-4.2-.97-.57-.26-1.1-.59-1.62-.93-.01 2.92.01 5.84-.02 8.75-.08 1.4-.54 2.79-1.35 3.94-1.31 1.92-3.58 3.17-5.91 3.21-2.43.03-4.83-.95-6.43-2.88-1.59-1.92-2.3-4.45-2.2-6.87.02-1.11.23-2.21.62-3.25.39-1.04.9-2 1.52-2.81 1.1-1.45 2.7-2.45 4.5-2.87.03-.01.06-.02.09-.03z" />
  </svg>
);

const socialLinks = [
  { name: 'LinkedIn', href: '#', icon: Linkedin, hoverColor: '#00c6ff' },
  { name: 'X (Twitter)', href: '#', icon: X, hoverColor: '#ffffff' },
  { name: 'YouTube', href: '#', icon: Youtube, hoverColor: '#ff0000' },
  { name: 'Facebook', href: '#', icon: Facebook, hoverColor: '#1877F2' },
  { name: 'Instagram', href: '#', icon: Instagram, hoverColor: '#E4405F' },
  { name: 'TikTok', href: '#', icon: Tiktok, hoverColor: '#00f2ea' },
];

const Footer = () => {
    const footerRef = useRef<HTMLElement>(null);
    const mouseX = useMotionValue(Infinity);
    const mouseY = useMotionValue(Infinity);

    const maskImage = useTransform(
        [mouseX, mouseY],
        ([newX, newY]) => {
            const rect = footerRef.current?.getBoundingClientRect();
            
            if (!rect || newX === Infinity) {
                return "radial-gradient(circle at 50% -200%, white 0%, black 100%)";
            }
            
            
            const x = (newX as number) - rect.left;
            const y = (newY as number) - rect.top;
            
            return `radial-gradient(300px circle at ${x}px ${y}px, white 20%, transparent 100%)`;
        }
    );

  return (
    <>
      <motion.footer
        ref={footerRef}
        onMouseMove={(e) => {
            mouseX.set(e.clientX);
            mouseY.set(e.clientY);
        }}
        onMouseLeave={() => {
            mouseX.set(Infinity);
            mouseY.set(Infinity);
        }}
        className="relative py-20 px-4 text-white overflow-hidden bg-ultra-black"
      >
        <div className="absolute inset-0 -z-20 bg-grid-white/[0.05]" />
        <motion.div
            className="absolute inset-0 -z-10 bg-gradient-to-t from-cyan-900/50 via-violet-900/30 to-ultra-black"
            style={{
                maskImage: maskImage,
                WebkitMaskImage: maskImage,
            }}
        />
        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-cyan-500 to-transparent" />
        <div className="container mx-auto grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-8">
          <div className="lg:col-span-2 col-span-2 md:col-span-4">
            <h2 className="text-2xl font-bold" style={{ fontFamily: "'Orbitron', sans-serif" }}>
              airdeliver
            </h2>
            <p className="mt-2 text-sm text-gray-400 max-w-xs italic">
              We Soar In The Sky By Delivering Your Orders.
            </p>
          </div>
          <div>
            <h3 className="font-bold mb-4 text-white" style={{ fontFamily: "'Orbitron', sans-serif" }}>Shop</h3>
            <ul className="space-y-2 text-sm">
              <li><Link href="/products" className="text-gray-400 hover:text-white transition-colors">All Products</Link></li>
              <li><Link href="/products?category=accessories" className="text-gray-400 hover:text-white transition-colors">Accessories</Link></li>
            </ul>
          </div>
          <div>
            <h3 className="font-bold mb-4 text-white" style={{ fontFamily: "'Orbitron', sans-serif" }}>Company</h3>
            <ul className="space-y-2 text-sm">
              <li><Link href="/about" className="text-gray-400 hover:text-white transition-colors">About Us</Link></li>
              <li><Link href="/legal/terms-of-service" className="text-gray-400 hover:text-white transition-colors">Terms of Service</Link></li>
              <li><Link href="/legal/privacy-policy" className="text-gray-400 hover:text-white transition-colors">Privacy Policy</Link></li>
            </ul>
          </div>
          <div>
            <h3 className="font-bold mb-4 text-white" style={{ fontFamily: "'Orbitron', sans-serif" }}>Support</h3>
            <ul className="space-y-2 text-sm">
                {/* --- هذا هو السطر الذي تم تعديله --- */}
                <li><Link href="/help" className="text-gray-400 hover:text-white transition-colors">Contact Us</Link></li>
            </ul>
          </div>
        </div>
        <div className="container mx-auto mt-16 pt-8 border-t border-white/10 flex flex-col md:flex-row justify-between items-center text-sm">
          <p className="text-gray-500 mb-4 md:mb-0">
            © {new Date().getFullYear()} airdeliver Inc. All rights reserved.
          </p>
          <div className="flex gap-4">
            {socialLinks.map((social) => (
              <motion.a
                key={social.name}
                href={social.href}
                aria-label={social.name}
                target="_blank"
                rel="noopener noreferrer"
                whileHover={{ scale: 1.2, color: social.hoverColor }}
                className="text-gray-400"
              >
                <social.icon size={18} />
              </motion.a>
            ))}
          </div>
        </div>
      </motion.footer>
      
      <Chatbot />
    </>
  );
};

export default Footer;
