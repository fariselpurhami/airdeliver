'use client';
import React from 'react';
import Image from 'next/image';
import { motion, useReducedMotion, useScroll, useSpring, useTransform, type MotionValue } from 'framer-motion';

// Both routes use the same stage dimensions and cards, not nested relative frames.
export const HERO_STAGE_CLASSES = 'relative w-full min-h-[1000px] sm:min-h-[1000px] lg:min-h-[85vh] lg:h-[820px] flex flex-col items-center justify-center pt-44 pb-44 lg:pt-32 lg:pb-16 overflow-hidden perspective-1000 isolate';

export const FloatingCategoryCard = React.memo(({ 
    title, image, category, delay, yOffset, colorCls, rotation, sizeClasses 
}: { 
    title: string, image: string, category: string, delay: number, yOffset?: MotionValue<number>, colorCls: string, rotation: number, sizeClasses: string 
}) => { const reduced = useReducedMotion(); return (
    <motion.div 
        style={{ y: reduced ? 0 : undefined }}
        aria-hidden="true" data-hero-card={title} className={`absolute z-0 ${sizeClasses} will-change-transform`}
        initial={{ opacity: 0, scale: 0.8, rotate: rotation + 10 }}
        animate={{ opacity: 1, scale: 1, rotate: rotation }}
        transition={{ 
            opacity: { duration: 1, delay },
            scale: { duration: 1, delay, type: "spring", stiffness: 100, damping: 20 }
        }}
    >
        <motion.div
            animate={reduced ? {} : { y: [0, -15, 0] }}
            transition={{ duration: 6 + delay, repeat: Infinity, ease: "easeInOut" }}
            className="w-full h-full will-change-transform"
            style={{ transform: "translateZ(0)" }}
        >
            <div className={`relative w-full h-full rounded-[20px] lg:rounded-[32px] bg-[#0D0D0C]/80 backdrop-blur-2xl border border-white/10 shadow-[0_15px_30px_rgba(0,0,0,0.5),inset_0_1px_0_rgba(255,255,255,0.1)] lg:shadow-[0_30px_60px_rgba(0,0,0,0.8)] overflow-hidden group hover:scale-105 transition-transform duration-500 hover:z-50 ${colorCls}`}>
                <div className="absolute inset-0 bg-gradient-to-t from-black/95 via-black/40 lg:via-black/20 to-transparent z-10" />
                <Image src={image} alt="" fill sizes="(max-width: 768px) 30vw, 20vw" loading="eager" className="object-cover opacity-60 lg:opacity-80 group-hover:opacity-100 transition-opacity duration-700" />
                
                <div className="absolute bottom-3 left-3 right-3 lg:bottom-5 lg:left-5 lg:right-5 z-20 flex flex-col gap-0.5 lg:gap-1">
                    <span className="text-[7px] lg:text-[9px] font-mono uppercase tracking-[0.08em] lg:tracking-[0.3em] opacity-70 text-white mix-blend-overlay break-words">{category}</span>
                    <h3 className="text-[10px] lg:text-sm font-bold text-white tracking-wide leading-tight line-clamp-2 break-words" style={{ fontFamily: "'Orbitron', sans-serif" }}>{title}</h3>
                </div>
                
                <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none rounded-[20px] lg:rounded-[32px] ring-1 lg:ring-2 ring-current ring-inset mix-blend-overlay" />
            </div>
        </motion.div>
    </motion.div>
); });
FloatingCategoryCard.displayName = 'FloatingCategoryCard';


export function FloatingHeroCards() {
 const { scrollY } = useScroll();
 const smoothScrollY = useSpring(scrollY, { damping: 30, stiffness: 150, mass: 0.5 });
 const yFast = useTransform(smoothScrollY, [0,800], [0,-180]);
 const yMedium = useTransform(smoothScrollY, [0,800], [0,-100]);
 const ySlow = useTransform(smoothScrollY, [0,800], [0,-40]);
 return <div className="absolute inset-0 pointer-events-none z-0" data-floating-hero-cards>
            <FloatingCategoryCard sizeClasses="w-[24%] max-w-[112px] h-28 sm:h-36 left-[5%] top-[11%] lg:bottom-auto lg:right-auto lg:max-w-none lg:w-56 lg:h-72 lg:top-[10%] lg:left-[8%]" yOffset={yFast} delay={0.1} rotation={-8} category="Audio" title="Galaxy Buds" image="https://images.unsplash.com/photo-1600374917838-1df876d745c7?q=80&w=600&auto=format&fit=crop" colorCls="hover:shadow-cyan-500/20 text-cyan-400" />
            <FloatingCategoryCard sizeClasses="w-[24%] max-w-[112px] h-28 sm:h-36 left-[38%] top-[11%] lg:bottom-auto lg:right-auto lg:max-w-none lg:w-48 lg:h-60 lg:top-[45%] lg:left-[2%]" yOffset={ySlow} delay={0.3} rotation={-4} category="Beauty" title="Dyson" image="https://images.unsplash.com/photo-1755247339923-4fdfde950660?q=80&w=600&auto=format&fit=crop" colorCls="hover:shadow-pink-500/20 text-pink-400" />
            <FloatingCategoryCard sizeClasses="w-[24%] max-w-[112px] h-28 sm:h-36 right-[5%] top-[11%] lg:bottom-auto lg:right-auto lg:max-w-none lg:w-52 lg:h-64 lg:top-[65%] lg:left-[12%]" yOffset={yMedium} delay={0.5} rotation={6} category="Wearables" title="Apple Watch Ultra" image="https://images.unsplash.com/photo-1590688560938-57c514814ddb?q=80&w=600&auto=format&fit=crop" colorCls="hover:shadow-amber-500/20 text-amber-400" />
            
            <FloatingCategoryCard sizeClasses="w-[24%] max-w-[112px] h-28 sm:h-36 left-[5%] bottom-[3%] lg:bottom-auto lg:left-auto lg:max-w-none lg:w-56 lg:h-72 lg:top-[15%] lg:right-[8%]" yOffset={yMedium} delay={0.2} rotation={8} category="Bags" title="Leather Handbag" image="https://images.unsplash.com/photo-1691480150204-66dd1eb77391?q=80&w=600&auto=format&fit=crop" colorCls="hover:shadow-purple-500/20 text-purple-400" />
            <FloatingCategoryCard sizeClasses="w-[24%] max-w-[112px] h-28 sm:h-36 left-[38%] bottom-[3%] lg:bottom-auto lg:left-auto lg:max-w-none lg:w-48 lg:h-64 lg:top-[50%] lg:right-[3%]" yOffset={yFast} delay={0.4} rotation={4} category="Electronics" title="Iphone 17 pro max" image="https://images.unsplash.com/photo-1764746250417-2cc103a45a56?q=80&w=600&auto=format&fit=crop" colorCls="hover:shadow-emerald-500/20 text-emerald-400" />
            <FloatingCategoryCard sizeClasses="w-[24%] max-w-[112px] h-28 sm:h-36 right-[5%] bottom-[3%] lg:bottom-auto lg:left-auto lg:max-w-none lg:w-52 lg:h-56 lg:top-[70%] lg:right-[15%]" yOffset={ySlow} delay={0.6} rotation={-6} category="Fashion" title="Zara" image="https://images.unsplash.com/photo-1551028719-00167b16eac5?q=80&w=600&auto=format&fit=crop" colorCls="hover:shadow-blue-500/20 text-blue-400" />

</div>;
}
