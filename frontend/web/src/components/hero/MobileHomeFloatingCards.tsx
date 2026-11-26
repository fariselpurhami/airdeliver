'use client';
import Image from 'next/image';
import { memo } from 'react';
import { motion, useReducedMotion } from 'framer-motion';

// Original mobile home cards, positions, sizing and motion preserved verbatim.
interface HeroFloatingCardProps {
  readonly title: string; 
  readonly image: string; 
  readonly category: string; 
  readonly delay: number;
  readonly positionClasses: string; 
  readonly sizeClasses: string;
  readonly colorCls: string;
  readonly rotation: number;
}

// Colors Restored for visual hierarchy!
const HERO_CARDS: ReadonlyArray<HeroFloatingCardProps> = [
  { title: "Apple Vision Pro", category: "Spatial", delay: 0.1, rotation: -8, image: "https://images.unsplash.com/photo-1696429175928-793a1cdef1d3?q=80&w=1000&auto=format&fit=crop", positionClasses: "top-[1%] left-[16%] lg:top-[10%] lg:left-[5%]", sizeClasses: "w-21 h-29 lg:w-48 lg:h-64", colorCls: "hover:shadow-cyan-500/30 text-grey" },
  { title: "PS5", category: "Gaming", delay: 0.2, rotation: 6, image: "https://images.unsplash.com/photo-1606144042614-b2417e99c4e3?q=80&w=600&auto=format&fit=crop", positionClasses: "top-[1%] right-[16%] lg:top-[10%] lg:right-[5%]", sizeClasses: "w-21 h-29 lg:w-40 lg:h-56", colorCls: "hover:shadow-purple-500/30 text-grey" },
  { title: "Dyson", category: "Beauty", delay: 0.3, rotation: -4, image: "https://images.unsplash.com/photo-1755247339923-4fdfde950660?q=80&w=600&auto=format&fit=crop", positionClasses: "top-[50%] -left-[4%] lg:top-[45%] lg:left-[2%]", sizeClasses: "w-20 h-28 lg:w-40 lg:h-52", colorCls: "hover:shadow-pink-500/30 text-grey" },
  { title: "Headphones", category: "Audio", delay: 0.4, rotation: 8, image: "https://images.unsplash.com/photo-1618366712010-f4ae9c647dcb?q=80&w=600&auto=format&fit=crop", positionClasses: "top-[50%] -right-[3%] lg:top-[45%] lg:right-[2%]", sizeClasses: "w-20 h-28 lg:w-44 lg:h-48", colorCls: "hover:shadow-amber-500/30 text-grey" },
  { title: "Leather Handbag", category: "Bags", delay: 0.5, rotation: -6, image: "https://images.unsplash.com/photo-1691480150204-66dd1eb77391?q=80&w=600&auto=format&fit=crop", positionClasses: "top-[70%] left-[2%] lg:bottom-[25%] lg:left-[8%]", sizeClasses: "w-20 h-28 lg:w-36 lg:h-48", colorCls: "hover:shadow-emerald-500/30 text-grey" },
  { title: "Iphone 17 pro max", category: "Electronics", delay: 0.6, rotation: 5, image: "https://images.unsplash.com/photo-1764746250417-2cc103a45a56?q=80&w=600&auto=format&fit=crop", positionClasses: "top-[70%] right-[1%] lg:bottom-[25%] lg:right-[8%]", sizeClasses: "w-22 h-28 lg:w-40 lg:h-56", colorCls: "hover:shadow-blue-500/30 text-grey" },
  { title: "Nike Air Max", category: "Fashion", delay: 0.7, rotation: -5, image: "https://images.unsplash.com/photo-1542291026-7eec264c27ff?q=80&w=600&auto=format&fit=crop", positionClasses: "bottom-[0%] left-[20%] lg:bottom-[5%] lg:left-[25%]", sizeClasses: "w-20 h-28 lg:w-48 lg:h-48", colorCls: "hover:shadow-red-500/30 text-grey" },
  { title: "Galaxy Buds", category: "Audio", delay: 0.8, rotation: 7, image: "https://images.unsplash.com/photo-1600374917838-1df876d745c7?q=80&w=600&auto=format&fit=crop", positionClasses: "bottom-[0%] right-[20%] lg:bottom-[5%] lg:right-[25%]", sizeClasses: "w-20 h-28 lg:w-36 lg:h-48", colorCls: "hover:shadow-cyan-500/30 text-grey" }
];

const HeroFloatingCard = memo(({ title, image, category, delay, positionClasses, sizeClasses, colorCls, rotation }: HeroFloatingCardProps) => {
  const prefersReducedMotion = useReducedMotion();
  
  return (
    <motion.div
      className={`absolute z-0 ${positionClasses} ${sizeClasses} transform-gpu`}
      initial={{ opacity: 0, scale: prefersReducedMotion ? 1 : 0.8, rotate: prefersReducedMotion ? rotation : rotation + 10 }}
      animate={{ opacity: 1, scale: 1, rotate: rotation }}
      transition={{
        opacity: { duration: 1, delay },
        scale: { duration: 1, delay, type: "spring", stiffness: 100, damping: 20 }
      }}
      aria-hidden="true" data-mobile-hero-card={title}
    >
      <motion.div
        animate={prefersReducedMotion ? {} : { y: [0, -15, 0] }}
        transition={{ duration: 6 + delay, repeat: Infinity, ease: "easeInOut" }}
        className="w-full h-full transform-gpu"
        style={{ transform: "translateZ(0)" }}
      >
        <div className={`relative w-full h-full rounded-[20px] lg:rounded-[32px] bg-[#0D0D0C]/80 backdrop-blur-2xl border border-white/10 shadow-[0_15px_30px_rgba(0,0,0,0.5),inset_0_1px_0_rgba(255,255,255,0.1)] lg:shadow-[0_30px_60px_rgba(0,0,0,0.8)] overflow-hidden group hover:scale-105 transition-transform duration-500 hover:z-50 pointer-events-auto ${colorCls}`}>
          <div className="absolute inset-0 bg-gradient-to-t from-black/95 via-black/40 lg:via-black/20 to-transparent z-10" />
          <Image src={image} alt="" fill sizes="(max-width: 768px) 30vw, 20vw" decoding="async" className="object-cover opacity-60 lg:opacity-80 group-hover:opacity-100 transition-opacity duration-700" />
          <div className="absolute bottom-3 left-3 right-3 lg:bottom-5 lg:left-5 lg:right-5 z-20 flex flex-col gap-0.5 lg:gap-1">
            <span className="text-[7px] lg:text-[9px] font-mono uppercase tracking-[0.08em] lg:tracking-[0.3em] opacity-70 text-current mix-blend-overlay break-words">{category}</span>
            <h3 className="text-[10px] lg:text-sm font-bold text-white tracking-wide leading-tight line-clamp-2 break-words" style={{ fontFamily: "'Orbitron', sans-serif" }}>{title}</h3>
          </div>
          <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none rounded-[20px] lg:rounded-[32px] ring-1 lg:ring-2 ring-current ring-inset mix-blend-overlay" />
        </div>
      </motion.div>
    </motion.div>
  );
});
HeroFloatingCard.displayName = 'HeroFloatingCard';


export function MobileHomeFloatingCards() {
 return <div data-mobile-home-cards className="absolute inset-0 pointer-events-none z-20">{HERO_CARDS.map(card=><HeroFloatingCard key={card.title} {...card}/>)}</div>;
}
