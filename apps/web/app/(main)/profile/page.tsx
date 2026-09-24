//** apps/web/app/(main)/profile/page.tsx **//

'use client';

import React, { useMemo, useRef, useEffect, useState, Suspense, memo } from 'react';
import { useSession, signOut } from "next-auth/react";
import { motion, AnimatePresence } from "framer-motion";
import Image from 'next/image';
import useSWR from 'swr';
import { api } from '@/lib/api'; 
import { redirect } from 'next/navigation';
import { toast } from 'sonner'; 
import { Canvas, useFrame } from '@react-three/fiber';
import { Preload } from '@react-three/drei';
import * as THREE from 'three';

// Icons
import { 
  Camera, ShieldCheck, LogOut, Settings, Package, Key, User
} from 'lucide-react';

// Modals
import {  
  ViewOrdersModal, 
  EditProfileDetailsModal, 
  ChangePasswordModal 
} from '@/components/profile/ProfileModals';

// ============================================================================
// --- TYPE DEFINITIONS ---
// ============================================================================
interface UserProfileData {
    id: number; email: string; full_name?: string | null; role?: string | null;
    phone_number?: string | null; address?: string | null; avatar_url?: string | null;
    country?: string | null; city?: string | null; created_at?: string | null;
    orders_completed?: number; items_favorited?: number;
}
interface DefaultPaymentData { brand: string | null; last4: string | null; }

// ============================================================================
// --- 1. OPTIMIZED 3D BACKGROUND (WHITE STARS) ---
// ============================================================================
const premiumEasing = [0.16, 1, 0.3, 1];

const heroCanvasConfig = {
  camera: { position: [0, 0, 15] as [number, number, number], fov: 75 },
  dpr: [1, 1.2] as [number, number],
  gl: { antialias: false, powerPreference: "high-performance" as const, alpha: true, depth: false, stencil: false },
};

const createParticlePositions = (count: number, radius: number): Float32Array => {
  const positions = new Float32Array(count * 3);
  for (let i = 0; i < count; i++) {
    const r = radius * Math.cbrt(Math.random());
    const theta = Math.random() * 2 * Math.PI;
    const phi = Math.acos(2 * Math.random() - 1);
    positions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
    positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
    positions[i * 3 + 2] = r * Math.cos(phi);
  }
  return positions;
};

const ParticleField = memo(({ count, radius, color, size, rotationSpeed }: any) => {
  const groupRef = useRef<THREE.Group>(null!);
  const pointsRef = useRef<THREE.Points>(null!);
  const positions = useMemo(() => createParticlePositions(count, radius), [count, radius]);
  const materialColor = useMemo(() => new THREE.Color(color), [color]);

  useEffect(() => {
    if (pointsRef.current) pointsRef.current.matrixAutoUpdate = false;
  }, []);

  useFrame((_, delta) => {
    if (!groupRef.current) return;
    const safeDelta = delta > 0.1 ? 0.1 : delta;
    groupRef.current.rotation.x += safeDelta * rotationSpeed.x;
    groupRef.current.rotation.y += safeDelta * rotationSpeed.y;
    groupRef.current.rotation.z += safeDelta * rotationSpeed.z;
  });

  return (
    <group ref={groupRef} position={[0, 0, -60]}>
      <points ref={pointsRef} frustumCulled={false}>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" count={count} array={positions} itemSize={3} />
        </bufferGeometry>
        <pointsMaterial 
          transparent color={materialColor} size={size} sizeAttenuation depthWrite={false} 
          toneMapped={false} opacity={0.8} 
          onBeforeCompile={(shader) => {
            shader.fragmentShader = shader.fragmentShader.replace(
              'void main() {',
              `void main() {
                vec2 pt = gl_PointCoord - vec2(0.5);
                if (dot(pt, pt) > 0.20) discard;`
            );
          }}
        />
      </points>
    </group>
  );
});
ParticleField.displayName = 'ParticleField';

// ============================================================================
// --- 2. FLOATING PRODUCT CARDS ---
// ============================================================================
const ProfileFloatingProduct = memo(({
    title, image, category, delay, positionClasses, sizeClasses, colorCls, rotation
}: any) => (
    <motion.div
        className={`absolute z-0 ${positionClasses} ${sizeClasses} will-change-transform`}
        initial={{ opacity: 0, scale: 0.8, rotate: rotation + 10 }}
        animate={{ opacity: 1, scale: 1, rotate: rotation }}
        transition={{
            opacity: { duration: 1, delay },
            scale: { duration: 1, delay, type: "spring", stiffness: 100, damping: 20 }
        }}
    >
        <motion.div
            animate={{ y: [0, -15, 0] }}
            transition={{ duration: 6 + delay, repeat: Infinity, ease: "easeInOut" }}
            className="w-full h-full will-change-transform"
        >
            <div className={`relative w-full h-full rounded-[20px] lg:rounded-[32px] bg-[#0D0D0C]/80 backdrop-blur-2xl border border-white/10 shadow-[0_15px_30px_rgba(0,0,0,0.5)] overflow-hidden group hover:scale-105 transition-transform duration-500 hover:z-50 pointer-events-none ${colorCls}`}>
                <div className="absolute inset-0 bg-gradient-to-t from-black/95 via-black/40 lg:via-black/20 to-transparent z-10" />
                <Image src={image} alt={category} fill sizes="(max-width: 768px) 30vw, 20vw" className="object-cover opacity-60 lg:opacity-80 group-hover:opacity-100 transition-opacity duration-700" />

                <div className="absolute bottom-3 left-3 right-3 lg:bottom-5 lg:left-5 lg:right-5 z-20 flex flex-col gap-0.5 lg:gap-1">
                    <span className="text-[7px] lg:text-[9px] font-mono uppercase tracking-[0.2em] opacity-70 text-white mix-blend-overlay line-clamp-1">{category}</span>
                    <h3 className="text-[10px] lg:text-sm font-bold text-white tracking-wide leading-tight line-clamp-1" style={{ fontFamily: "'Orbitron', sans-serif" }}>{title}</h3>
                </div>

                <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none rounded-[20px] lg:rounded-[32px] ring-1 lg:ring-2 ring-current ring-inset mix-blend-overlay" />
            </div>
        </motion.div>
    </motion.div>
));
ProfileFloatingProduct.displayName = 'ProfileFloatingProduct';

// ============================================================================
// --- 3. ICON BUTTON COMPONENT ---
// ============================================================================
const IconButton = memo(({ icon: Icon, label, onClick, colorClass, delay }: any) => (
    <motion.button
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5, delay: delay, ease: premiumEasing }}
        onClick={onClick}
        whileHover={{ scale: 1.15, y: -2 }}
        whileTap={{ scale: 0.95 }}
        className="group relative flex items-center justify-center w-12 h-12 rounded-full bg-white/5 border border-white/10 backdrop-blur-md transition-all duration-300 hover:bg-white/10 hover:border-white/20 shadow-lg cursor-pointer transform-gpu"
    >
        <div className={`absolute -inset-[2px] rounded-full blur-md transition-all duration-500 -z-10 opacity-0 group-hover:opacity-60 ${colorClass}`} />
        <Icon size={18} className="text-gray-300 group-hover:text-white transition-colors duration-300" />
        
        {/* Tooltip */}
        <span className="absolute -bottom-8 opacity-0 group-hover:opacity-100 transition-opacity duration-300 text-[10px] font-mono tracking-wider text-gray-300 whitespace-nowrap bg-black/80 px-2 py-1 rounded-md border border-white/10">
            {label}
        </span>
    </motion.button>
));
IconButton.displayName = 'IconButton';


// ============================================================================
// --- 4. MAIN PAGE COMPONENT ---
// ============================================================================
export default function ProfilePage() {
    const { data: session, status: sessionStatus, update: updateSession } = useSession();
    const swrFetcher = (url: string) => api.get(url).then(res => res.data);

    const { data: userData, mutate: mutateProfile } = useSWR<UserProfileData>(
        sessionStatus === 'authenticated' ? '/users/me' : null, swrFetcher, { revalidateOnFocus: false }
    );

    const [isClient, setIsClient] = useState(false);
    const [isEditDetailsModalOpen, setIsEditDetailsModalOpen] = useState(false);
    const [isPasswordModalOpen, setIsPasswordModalOpen] = useState(false);
    const [isOrdersModalOpen, setIsOrdersModalOpen] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    useEffect(() => { setIsClient(true); }, []);

    if (sessionStatus === 'unauthenticated') redirect('/login');

    const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file || !session?.accessToken) return;
        const formData = new FormData();
        formData.append('file', file);
        toast.promise((async () => {
                 const response = await api.post<UserProfileData>('/users/me/avatar', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
                 mutateProfile(response.data, false);
                 if (response.data.avatar_url && session?.user) await updateSession({ user: { ...session.user, image: response.data.avatar_url } });
            })(), { loading: 'Uploading photo...', success: 'Profile photo updated.', error: 'Failed to upload photo.' }
        );
    };

    const profileData = userData || {} as UserProfileData;
    const userImage = profileData?.avatar_url || session?.user?.image || `https://ui-avatars.com/api/?name=${encodeURIComponent(profileData?.full_name || 'User')}&background=000000&color=ffffff&size=128`;
    
    // 8 Floating Product Cards (Identical to Hero Section Concept)
    const HERO_CARDS = [
      {
        title: "Apple Vision Pro", category: "Neural Tech", delay: 0.1, rotation: -8,
        image: "https://images.unsplash.com/photo-1696429175928-793a1cdef1d3?q=80&w=1000&auto=format&fit=crop",
        positionClasses: "top-[1%] left-[6%] lg:top-[10%] lg:left-[5%]",
        sizeClasses: "w-20 h-28 lg:w-48 lg:h-64", colorCls: "hover:shadow-cyan-500/20 text-cyan-400"
      },
      {
        title: "PS5", category: "Wearables", delay: 0.2, rotation: 6,
        image: "https://images.unsplash.com/photo-1606144042614-b2417e99c4e3?q=80&w=600&auto=format&fit=crop",
        positionClasses: "top-[1%] right-[6%] lg:top-[10%] lg:right-[5%]",
        sizeClasses: "w-20 h-28 lg:w-40 lg:h-56", colorCls: "hover:shadow-purple-500/20 text-purple-400"
      },
      {
        title: "Dyson", category: "Aesthetic", delay: 0.3, rotation: -4,
        image: "https://images.unsplash.com/photo-1755247339923-4fdfde950660?q=80&w=600&auto=format&fit=crop",
        positionClasses: "top-[50%] -left-[4%] lg:top-[45%] lg:left-[2%]",
        sizeClasses: "w-20 h-28 lg:w-40 lg:h-52", colorCls: "hover:shadow-pink-500/20 text-pink-400"
      },
      {
        title: "Headphones", category: "Audio", delay: 0.4, rotation: 8,
        image: "https://images.unsplash.com/photo-1618366712010-f4ae9c647dcb?q=80&w=600&auto=format&fit=crop",
        positionClasses: "top-[50%] -right-[3%] lg:top-[45%] lg:right-[2%]",
        sizeClasses: "w-20 h-28 lg:w-44 lg:h-48", colorCls: "hover:shadow-amber-500/20 text-amber-400"
      },
      {
        title: "Leather Handbag", category: "Bags", delay: 0.5, rotation: -6,
        image: "https://images.unsplash.com/photo-1691480150204-66dd1eb77391?q=80&w=600&auto=format&fit=crop",
        positionClasses: "top-[70%] left-[2%] lg:bottom-[25%] lg:left-[8%]",
        sizeClasses: "w-20 h-28 lg:w-36 lg:h-48", colorCls: "hover:shadow-emerald-500/20 text-emerald-400"
      },
      {
        title: "Iphone 17 pro max", category: "Electronics", delay: 0.6, rotation: 5,
        image: "https://images.unsplash.com/photo-1764746250417-2cc103a45a56?q=80&w=600&auto=format&fit=crop",
        positionClasses: "top-[70%] right-[1%] lg:bottom-[25%] lg:right-[8%]",
        sizeClasses: "w-20 h-28 lg:w-40 lg:h-56", colorCls: "hover:shadow-blue-500/20 text-blue-400"
      },
      {
        title: "Nike Air Max", category: "Fashion", delay: 0.7, rotation: -5,
        image: "https://images.unsplash.com/photo-1542291026-7eec264c27ff?q=80&w=600&auto=format&fit=crop",
        positionClasses: "bottom-[0%] left-[20%] lg:bottom-[5%] lg:left-[25%]",
        sizeClasses: "w-20 h-28 lg:w-48 lg:h-48", colorCls: "hover:shadow-red-500/20 text-red-400"
      },
      {
        title: "Galaxy Buds", category: "Neural Tech", delay: 0.8, rotation: 7,
        image: "https://images.unsplash.com/photo-1600374917838-1df876d745c7?q=80&w=600&auto=format&fit=crop",
        positionClasses: "bottom-[0%] right-[20%] lg:bottom-[5%] lg:right-[25%]",
        sizeClasses: "w-20 h-28 lg:w-36 lg:h-48", colorCls: "hover:shadow-cyan-500/20 text-cyan-400"
      }
    ];

    if (!isClient) return <div className="min-h-screen bg-black" />;

    return (
        <section className="relative min-h-[100svh] w-full bg-[#050505] overflow-hidden flex items-center pt-28 pb-16 lg:pt-0 lg:pb-0 font-sans">
            <input type="file" ref={fileInputRef} onChange={handleFileChange} accept="image/*" className="hidden" />

            {/* 3D Background Canvas with White Stars */}
            <div className="absolute inset-0 z-0 pointer-events-none transform-gpu" style={{ contain: 'strict' }}>
                <Suspense fallback={null}>
                    <Canvas {...heroCanvasConfig}>
                        <ParticleField count={5000} radius={66} color="#ffffff" size={0.065} rotationSpeed={{ x: -0.0001, y: -0.0001, z: -0.001 }} />
                        <Preload all />
                    </Canvas>
                </Suspense>
            </div>

            {/* Very Subtle Background Lighting */}
            <div className="absolute top-[10%] left-[10%] w-[50%] h-[50%] rounded-full bg-cyan-600/5 blur-[120px] pointer-events-none mix-blend-screen" />
            <div className="absolute bottom-[10%] right-[10%] w-[50%] h-[50%] rounded-full bg-blue-600/5 blur-[120px] pointer-events-none mix-blend-screen" />
            
            <div className="container mx-auto px-5 sm:px-6 lg:px-12 relative z-10 h-full">
                <div className="w-full flex flex-col items-center justify-center min-h-[75vh] lg:min-h-[100svh] relative">
                    
                    {/* --- COMPACT FLOATING CENTRAL CONTENT --- */}
                    <div className="flex flex-col items-center text-center w-full max-w-xs relative z-30 pointer-events-auto">
                        
                        <motion.div 
                            initial={{ opacity: 0, y: 30, filter: "blur(10px)" }} 
                            animate={{ opacity: 1, y: 0, filter: "blur(0px)" }} 
                            transition={{ duration: 0.8, ease: premiumEasing }}
                            className="flex flex-col items-center w-full"
                        >
                            {/* Compact Floating Avatar */}
                            <div 
                                className="relative w-20 h-20 lg:w-24 lg:h-24 mx-auto mb-5 rounded-full border border-white/20 bg-black overflow-hidden shadow-[0_0_40px_rgba(255,255,255,0.1)] cursor-pointer group hover:scale-105 transition-transform duration-500"
                                onClick={() => fileInputRef.current?.click()}
                            >
                                <div className="absolute inset-0 bg-gradient-to-tr from-white/5 to-white/10 z-10 mix-blend-overlay" />
                                <Image src={userImage} alt="Profile" fill className="object-cover opacity-90 group-hover:opacity-40 transition-opacity duration-300" unoptimized />
                                <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity z-20">
                                    <Camera className="text-white w-5 h-5 drop-shadow-md" />
                                </div>
                            </div>

                            {/* Compact Floating Text Info */}
                            <div className="mb-6 w-full space-y-1.5">
                                
                                <h1 className="text-2xl sm:text-3xl lg:text-4xl font-black text-white tracking-tighter drop-shadow-2xl px-2 leading-tight" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                                    {profileData?.full_name || 'Agent Identity'}
                                </h1>
                                <p className="text-[11px] sm:text-xs text-gray-400 font-light drop-shadow-md">
                                    {profileData?.email || 'Verifying credentials...'}
                                </p>
                            </div>

                            {/* --- ICON BAR: INLINE ACTIONS --- */}
                            <div className="flex items-center justify-center gap-4 mt-2">
                                <IconButton 
                                    icon={Package} 
                                    label="View Orders" 
                                    delay={0.1}
                                    onClick={() => setIsOrdersModalOpen(true)}
                                    colorClass="bg-cyan-500/40"
                                />
                                <IconButton 
                                    icon={User} 
                                    label="Account Settings" 
                                    delay={0.2}
                                    onClick={() => setIsEditDetailsModalOpen(true)}
                                    colorClass="bg-purple-500/40"
                                />
                                <IconButton 
                                    icon={Key} 
                                    label="Security" 
                                    delay={0.3}
                                    onClick={() => setIsPasswordModalOpen(true)}
                                    colorClass="bg-emerald-500/40"
                                />
                                <IconButton 
                                    icon={LogOut} 
                                    label="Sign Out" 
                                    delay={0.4}
                                    onClick={() => signOut({ callbackUrl: '/login' })}
                                    colorClass="bg-red-500/40"
                                />
                            </div>

                        </motion.div>
                    </div>

                    {/* Floating Product Cards (Absolute) */}
                    <div className="absolute inset-0 pointer-events-none z-20 flex items-center justify-center perspective-1000">
                        <motion.div
                            initial={{ opacity: 0, scale: 0.9, rotateY: 10 }} animate={{ opacity: 1, scale: 1, rotateY: 0 }} transition={{ duration: 1.2, ease: premiumEasing, delay: 0.2 }}
                            className="relative w-full h-full flex items-center justify-center"
                        >
                            {HERO_CARDS.map((card, idx) => (
                                <ProfileFloatingProduct key={idx} {...card} />
                            ))}
                        </motion.div>
                    </div>

                </div>
            </div>

            {/* Existing Modals */}
            <EditProfileDetailsModal isOpen={isEditDetailsModalOpen} onClose={() => setIsEditDetailsModalOpen(false)} userData={profileData} onSave={async (d) => { await api.put('/users/me', d); mutateProfile(); setIsEditDetailsModalOpen(false); }} />
            <ChangePasswordModal isOpen={isPasswordModalOpen} onClose={() => setIsPasswordModalOpen(false)} onSave={async (c, n) => { await api.post('/users/me/change-password', { current_password: c, new_password: n }); setIsPasswordModalOpen(false); }} />
            <ViewOrdersModal isOpen={isOrdersModalOpen} onClose={() => setIsOrdersModalOpen(false)} />
        </section>
    );
}
