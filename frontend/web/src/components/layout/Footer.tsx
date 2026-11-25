//** frontend/web/components/layout/Footer.tsx **//

'use client';

import React, { useRef, useEffect, memo } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { FaLinkedin, FaYoutube, FaXTwitter, FaFacebook, FaInstagram, FaSnapchat, FaTiktok } from 'react-icons/fa6';


const SOCIAL_LINKS = [
  { name: 'LinkedIn', href: '#', icon: FaLinkedin, hoverColor: '#0077b5' },
  { name: 'X (Twitter)', href: '#', icon: FaXTwitter, hoverColor: '#ffffff' },
  { name: 'YouTube', href: '#', icon: FaYoutube, hoverColor: '#ff0000' },
  { name: 'Facebook', href: '#', icon: FaFacebook, hoverColor: '#1877F2' },
  { name: 'Instagram', href: '#', icon: FaInstagram, hoverColor: '#E4405F' },
  { name: 'Snapchat', href: '#', icon: FaSnapchat, hoverColor: '#FFFC00' },
  { name: 'TikTok', href: '#', icon: FaTiktok, hoverColor: '#00f2ea' },
] as const;

// Memoize stable sub-components to prevent unnecessary React diffing overhead
const FooterLink = memo(({ href, children }: { href: string; children: React.ReactNode }) => (
    <Link href={href} className="group/link flex items-center gap-2 text-sm text-gray-400 hover:text-cyan-400 transition-colors duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 rounded-sm">
        <span className="h-px w-0 bg-cyan-400 group-hover/link:w-3 transition-all duration-300 transform-gpu" aria-hidden="true" />
        {children}
    </Link>
));
FooterLink.displayName = 'FooterLink';

const Footer = () => {
    const footerRef = useRef<HTMLElement>(null);

    // CRITICAL PERF: We bypass React Synthetic Events for high-frequency pointer tracking.
    // Using native passive listeners guarantees the compositor thread isn't blocked.
    useEffect(() => {
        const el = footerRef.current;
        if (!el) return;

        let rafId: number;

        const handlePointerMove = (e: PointerEvent) => {
            if (e.pointerType !== 'mouse') return;

            cancelAnimationFrame(rafId);
            rafId = requestAnimationFrame(() => {
                const rect = el.getBoundingClientRect();
                // Direct CSS OM manipulation avoids React reconciler overhead completely
                el.style.setProperty('--x', `${e.clientX - rect.left}px`);
                el.style.setProperty('--y', `${e.clientY - rect.top}px`);
            });
        };

        el.addEventListener('pointermove', handlePointerMove, { passive: true });

        return () => {
            el.removeEventListener('pointermove', handlePointerMove);
            cancelAnimationFrame(rafId);
        };
    }, []);

  return (
    <footer 
        ref={footerRef} 
        // CRITICAL PERF: 'contain-content' strictly isolates layout/paint of this node.
        // It prevents the high-frequency hover repaints from propagating up the DOM tree.
        className="relative bg-black pt-24 pb-29 md:pb-10 overflow-hidden group contain-content"
    >
        {/* Decorative Grid Background */}
        <div className="absolute inset-0 bg-[url('/grid.svg')] opacity-[0.03] pointer-events-none transform-gpu translate-z-0" aria-hidden="true" />
        
        {/* Hardware-Accelerated Tracking Mask */}
        <div
            aria-hidden="true"
            className="absolute inset-0 z-0 bg-gradient-to-r from-cyan-500/10 via-purple-500/10 to-blue-500/10 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none will-change-[mask-image] transform-gpu translate-z-0"
            style={{ 
                maskImage: `radial-gradient(400px circle at var(--x, 50%) var(--y, 100%), rgba(255,255,255,0.1), transparent 80%)`,
                WebkitMaskImage: `radial-gradient(400px circle at var(--x, 50%) var(--y, 100%), rgba(255,255,255,0.1), transparent 80%)`
            }}
        />
        
        {/* Top Border Glow */}
        <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-cyan-500/50 to-transparent transform-gpu" aria-hidden="true" />

        <div className="container mx-auto px-6 relative z-10">
            <div className="grid grid-cols-1 md:grid-cols-12 gap-12 lg:gap-8 mb-20">
                
                {/* Branding & Logo */}
                <div className="md:col-span-5 lg:col-span-4 flex flex-col gap-6">
                    <div className="relative inline-block w-fit">
                        <Link href="/" aria-label="airdeliver homepage" className="focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 rounded-sm block">
                            <Image 
                                src="/logo.png" 
                                alt="airdeliver logo" 
                                width={120} 
                                height={24} 
                                className="object-contain hover:opacity-80 transition-opacity duration-300 transform-gpu"
                                quality={90}
                                loading="lazy"
                                decoding="async"
                            />
                        </Link>
                    </div>

                    <p className="text-gray-400/80 text-[13px] font-extralight max-w-sm mt-2">
                        Future of Commerce: Powered by AI.
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

                <div className="flex gap-4">
                    {SOCIAL_LINKS.map((social) => {
                        const Icon = social.icon;
                        return (
                            <a
                                key={social.name}
                                href={social.href}
                                // CRITICAL PERF: Stripped heavy framer-motion library overhead here.
                                // Achieved exact same physics feel via pure GPU-accelerated CSS and custom properties.
                                className="text-gray-400 transition-all duration-300 will-change-transform focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--hover-color)] rounded-sm hover:text-[var(--hover-color)] hover:scale-[1.2] hover:-translate-y-[2px] active:scale-[0.95]"
                                style={{ '--hover-color': social.hoverColor } as React.CSSProperties}
                                target="_blank"
                                rel="noopener noreferrer"
                                aria-label={`Visit our ${social.name} page`}
                            >
                                <Icon size={20} aria-hidden="true" />
                            </a>
                        );
                    })}
                </div>
            </div>
        </div>
    </footer>
  );
};

export default memo(Footer);
