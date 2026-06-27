//** apps/web/components/layout/Footer.tsx **//

'use client';

import React, { useRef, useCallback, useEffect, memo } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { motion } from 'framer-motion';
import { FaLinkedin, FaYoutube, FaXTwitter, FaFacebook, FaInstagram } from 'react-icons/fa6';

const Tiktok = (props: React.SVGProps<SVGSVGElement>) => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" {...props}>
    <path d="M12.525.02c1.31-.02 2.61-.01 3.91-.02.08 1.53.63 3.09 1.75 4.17 1.12 1.11 2.7 1.62 4.24 1.79v4.03c-1.44-.05-2.89-.35-4.2-.97-.57-.26-1.1-.59-1.62-.93-.01 2.92.01 5.84-.02 8.75-.08 1.4-.54 2.79-1.35 3.94-1.31 1.92-3.58 3.17-5.91 3.21-2.43.03-4.83-.95-6.43-2.88-1.59-1.92-2.3-4.45-2.2-6.87.02-1.11.23-2.21.62-3.25.39-1.04.9-2 1.52-2.81 1.1-1.45 2.7-2.45 4.5-2.87.03-.01.06-.02.09-.03z" />
  </svg>
);

const SOCIAL_LINKS = [
  { name: 'LinkedIn', href: '#', icon: FaLinkedin, hoverColor: '#0077b5' },
  { name: 'X (Twitter)', href: '#', icon: FaXTwitter, hoverColor: '#ffffff' },
  { name: 'YouTube', href: '#', icon: FaYoutube, hoverColor: '#ff0000' },
  { name: 'Facebook', href: '#', icon: FaFacebook, hoverColor: '#1877F2' },
  { name: 'Instagram', href: '#', icon: FaInstagram, hoverColor: '#E4405F' },
  { name: 'TikTok', href: '#', icon: Tiktok, hoverColor: '#00f2ea' },
] as const;

// Memoize stable sub-components to prevent unnecessary React diffing overhead
const FooterLink = memo(({ href, children }: { href: string; children: React.ReactNode }) => (
    <Link href={href} className="group/link flex items-center gap-2 text-sm text-gray-400 hover:text-cyan-400 transition-colors duration-300">
        <span className="h-px w-0 bg-cyan-400 group-hover/link:w-3 transition-all duration-300" aria-hidden="true" />
        {children}
    </Link>
));
FooterLink.displayName = 'FooterLink';

const Footer = () => {
    const footerRef = useRef<HTMLElement>(null);
    const rafRef = useRef<number | null>(null);

    // Bypassing React render cycles & JS heavy lifting entirely for the hover effect.
    // Offloading to native CSS variables synchronized with the display frame rate.
    const handlePointerMove = useCallback((e: React.PointerEvent<HTMLElement>) => {
        // Optimization: Do not compute hover tracking for touch/stylus inputs
        if (e.pointerType !== 'mouse') return;

        if (rafRef.current) cancelAnimationFrame(rafRef.current);

        rafRef.current = requestAnimationFrame(() => {
            if (!footerRef.current) return;
            const rect = footerRef.current.getBoundingClientRect();
            // Assign directly to CSS engine, avoiding React reconciliation entirely
            footerRef.current.style.setProperty('--x', `${e.clientX - rect.left}px`);
            footerRef.current.style.setProperty('--y', `${e.clientY - rect.top}px`);
        });
    }, []);

    // Ensure we avoid memory leaks on unmount
    useEffect(() => {
        return () => {
            if (rafRef.current) cancelAnimationFrame(rafRef.current);
        };
    }, []);

  return (
    <footer 
        ref={footerRef} 
        // Added 'group' class to orchestrate child opacity transitions natively in CSS
        className="relative bg-black pt-24 pb-10 overflow-hidden group" 
        onPointerMove={handlePointerMove}
    >
        {/* Decorative Grid Background */}
        <div className="absolute inset-0 bg-[url('/grid.svg')] opacity-[0.03] pointer-events-none" aria-hidden="true" />
        
        {/* Hardware-Accelerated Tracking Mask */}
        <div
            aria-hidden="true"
            className="absolute inset-0 z-0 bg-gradient-to-r from-cyan-500/10 via-purple-500/10 to-blue-500/10 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none will-change-[mask-image]"
            style={{ 
                // Native CSS handling falls back safely if variables aren't set yet
                maskImage: `radial-gradient(400px circle at var(--x, 50%) var(--y, 100%), rgba(255,255,255,0.1), transparent 80%)`,
                WebkitMaskImage: `radial-gradient(400px circle at var(--x, 50%) var(--y, 100%), rgba(255,255,255,0.1), transparent 80%)`
            }}
        />
        
        {/* Top Border Glow */}
        <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-cyan-500/50 to-transparent" aria-hidden="true" />

        <div className="container mx-auto px-6 relative z-10">
            <div className="grid grid-cols-1 md:grid-cols-12 gap-12 lg:gap-8 mb-20">
                
                {/* Branding & Logo */}
                <div className="md:col-span-5 lg:col-span-4 flex flex-col gap-6">
                    <div className="relative inline-block w-fit">
                        <Link href="/" aria-label="airdeliver homepage">
                            <Image 
                                src="/logo.png" 
                                alt="airdeliver" 
                                width={120} 
                                height={24} 
                                className="object-contain hover:opacity-80 transition-opacity duration-300"
                                quality={90}
                                loading="lazy"
                            />
                        </Link>
                    </div>

                    <p className="text-gray-400/80 text-[11px] font-extralight tracking-[0.4em] max-w-sm mt-2">
                        Commerce. Takes Flight.
                    </p>
                </div>

                {/* Navigation Links */}
                <div className="md:col-span-7 lg:col-span-8 grid grid-cols-2 sm:grid-cols-3 gap-8">
                    <nav aria-labelledby="footer-shop-heading" className="flex flex-col gap-4">
                        <h3 id="footer-shop-heading" className="text-white font-bold uppercase tracking-widest text-xs flex items-center gap-2" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                            <span className="w-1.5 h-1.5 bg-purple-500 rounded-full" aria-hidden="true" /> Shop
                        </h3>
                        <div className="flex flex-col gap-3">
                            <FooterLink href="/products">All Products</FooterLink>
                            <FooterLink href="/products?category=accessories">Accessories</FooterLink>
                        </div>
                    </nav>

                    <nav aria-labelledby="footer-company-heading" className="flex flex-col gap-4">
                        <h3 id="footer-company-heading" className="text-white font-bold uppercase tracking-widest text-xs flex items-center gap-2" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                            <span className="w-1.5 h-1.5 bg-cyan-500 rounded-full" aria-hidden="true" /> Company
                        </h3>
                        <div className="flex flex-col gap-3">
                            <FooterLink href="/about">About Us</FooterLink>
                            <FooterLink href="/legal/terms-of-service">Terms of Service</FooterLink>
                            <FooterLink href="/legal/privacy-policy">Privacy Policy</FooterLink>
                        </div>
                    </nav>

                    <nav aria-labelledby="footer-support-heading" className="flex flex-col gap-4">
                        <h3 id="footer-support-heading" className="text-white font-bold uppercase tracking-widest text-xs flex items-center gap-2" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                            <span className="w-1.5 h-1.5 bg-white rounded-full" aria-hidden="true" /> Support
                        </h3>
                        <div className="flex flex-col gap-3">
                            <FooterLink href="/help">Contact Us</FooterLink>
                        </div>
                    </nav>
                </div>
            </div>

            {/* Bottom Bar: Copyright & Socials */}
            <div className="border-t border-white/10 pt-8 flex flex-col md:flex-row justify-between items-center gap-4 text-sm text-gray-500">
                <p className="font-sans text-[11px] tracking-normal opacity-70">
                    © {new Date().getFullYear()} airdeliver inc. all rights reserved.
                </p>

                <div className="flex gap-6">
                    {SOCIAL_LINKS.map((social) => (
                        <motion.a
                            key={social.name}
                            href={social.href}
                            whileHover={{ scale: 1.2, color: social.hoverColor, y: -2 }}
                            whileTap={{ scale: 0.95 }}
                            className="text-gray-400 transition-colors duration-300"
                            target="_blank"
                            rel="noopener noreferrer"
                            aria-label={`Visit our ${social.name} page`}
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

export default memo(Footer);
