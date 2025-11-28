//** apps/web/components/layout/Footer.tsx **//

'use client';

import React, { useRef } from 'react';
import Link from 'next/link';
import { motion, useMotionValue, useTransform } from 'framer-motion';
import { Linkedin, Youtube, X, Facebook, Instagram } from 'lucide-react';

const Tiktok = (props: React.SVGProps<SVGSVGElement>) => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" {...props}>
    <path d="M12.525.02c1.31-.02 2.61-.01 3.91-.02.08 1.53.63 3.09 1.75 4.17 1.12 1.11 2.7 1.62 4.24 1.79v4.03c-1.44-.05-2.89-.35-4.2-.97-.57-.26-1.1-.59-1.62-.93-.01 2.92.01 5.84-.02 8.75-.08 1.4-.54 2.79-1.35 3.94-1.31 1.92-3.58 3.17-5.91 3.21-2.43.03-4.83-.95-6.43-2.88-1.59-1.92-2.3-4.45-2.2-6.87.02-1.11.23-2.21.62-3.25.39-1.04.9-2 1.52-2.81 1.1-1.45 2.7-2.45 4.5-2.87.03-.01.06-.02.09-.03z" />
  </svg>
);

const socialLinks = [
  { name: 'LinkedIn', href: '#', icon: Linkedin, hoverColor: '#0077b5' },
  { name: 'X (Twitter)', href: '#', icon: X, hoverColor: '#ffffff' },
  { name: 'YouTube', href: '#', icon: Youtube, hoverColor: '#ff0000' },
  { name: 'Facebook', href: '#', icon: Facebook, hoverColor: '#1877F2' },
  { name: 'Instagram', href: '#', icon: Instagram, hoverColor: '#E4405F' },
  { name: 'TikTok', href: '#', icon: Tiktok, hoverColor: '#00f2ea' },
];

const FooterLink = ({ href, children }: { href: string, children: React.ReactNode }) => (
    <Link href={href} className="group flex items-center gap-2 text-sm text-gray-400 hover:text-cyan-400 transition-colors duration-300">
        <span className="h-px w-0 bg-cyan-400 group-hover:w-3 transition-all duration-300" />
        {children}
    </Link>
);

const Footer = () => {
    const footerRef = useRef<HTMLElement>(null);
    const mouseX = useMotionValue(Infinity);
    const mouseY = useMotionValue(Infinity);

    const maskImage = useTransform(
        [mouseX, mouseY],
        ([newX, newY]) => {
            const rect = footerRef.current?.getBoundingClientRect();
            if (!rect || newX === Infinity) return "radial-gradient(circle at 50% 100%, transparent 0%, transparent 100%)";
            const x = (newX as number) - rect.left;
            const y = (newY as number) - rect.top;
            return `radial-gradient(400px circle at ${x}px ${y}px, rgba(255,255,255,0.1), transparent 80%)`;
        }
    );

  return (
    <footer ref={footerRef} className="relative bg-black pt-24 pb-10 overflow-hidden" 
        onMouseMove={(e) => { mouseX.set(e.clientX); mouseY.set(e.clientY); }}
        onMouseLeave={() => { mouseX.set(Infinity); mouseY.set(Infinity); }}
    >
        <div className="absolute inset-0 bg-[url('/grid.svg')] opacity-[0.03] pointer-events-none" />
        <motion.div
            className="absolute inset-0 z-0 bg-gradient-to-r from-cyan-500/10 via-purple-500/10 to-blue-500/10 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none"
            style={{ maskImage, WebkitMaskImage: maskImage }}
        />
        <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-cyan-500/50 to-transparent" />

        <div className="container mx-auto px-6 relative z-10">
            
            <div className="grid grid-cols-1 md:grid-cols-12 gap-12 lg:gap-8 mb-20">
                
                <div className="md:col-span-5 lg:col-span-4 flex flex-col gap-6">
                    <div className="relative inline-block">
                        <h2 className="text-2xl font-bold text-white tracking-tight" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                            airdeliver
                        </h2>
                    </div>
                    
                    <p className="text-gray-400 text-sm leading-relaxed max-w-sm">
                        We Soar In The Sky By Delivering Your Orders.
                    </p>
                </div>

                <div className="md:col-span-7 lg:col-span-8 grid grid-cols-2 sm:grid-cols-3 gap-8">
                    <div className="flex flex-col gap-4">
                        <h3 className="text-white font-bold uppercase tracking-widest text-xs flex items-center gap-2" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                            <span className="w-1.5 h-1.5 bg-purple-500 rounded-full" /> Shop
                        </h3>
                        <nav className="flex flex-col gap-3">
                            <FooterLink href="/products">All Products</FooterLink>
                            <FooterLink href="/products?category=accessories">Accessories</FooterLink>
                        </nav>
                    </div>

                    <div className="flex flex-col gap-4">
                        <h3 className="text-white font-bold uppercase tracking-widest text-xs flex items-center gap-2" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                            <span className="w-1.5 h-1.5 bg-cyan-500 rounded-full" /> Company
                        </h3>
                        <nav className="flex flex-col gap-3">
                            <FooterLink href="/about">About Us</FooterLink>
                            <FooterLink href="/legal/terms-of-service">Terms of Service</FooterLink>
                            <FooterLink href="/legal/privacy-policy">Privacy Policy</FooterLink>
                        </nav>
                    </div>

                    <div className="flex flex-col gap-4">
                        <h3 className="text-white font-bold uppercase tracking-widest text-xs flex items-center gap-2" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                            <span className="w-1.5 h-1.5 bg-white rounded-full" /> Support
                        </h3>
                        <nav className="flex flex-col gap-3">
                            <FooterLink href="/help">Contact Us</FooterLink>
                        </nav>
                    </div>
                </div>
            </div>

            <div className="border-t border-white/10 pt-8 flex flex-col md:flex-row justify-between items-center gap-4 text-sm text-gray-500">
                <p className="font-mono text-[10px] tracking-widest uppercase">
                    © {new Date().getFullYear()} airdeliver Inc. All rights reserved.
                </p>

                <div className="flex gap-6">
                    {socialLinks.map((social) => (
                        <motion.a
                            key={social.name}
                            href={social.href}
                            whileHover={{ scale: 1.2, color: social.hoverColor, y: -2 }}
                            whileTap={{ scale: 0.95 }}
                            className="text-gray-400 transition-colors duration-300"
                            target="_blank"
                            rel="noopener noreferrer"
                            aria-label={social.name}
                        >
                            <social.icon size={20} />
                        </motion.a>
                    ))}
                </div>
            </div>
        </div>
    </footer>
  );
};

export default Footer;
