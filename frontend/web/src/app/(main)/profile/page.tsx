//** frontend/web/app/(main)/profile/page.tsx **//

'use client';

import React, { useMemo, useRef, useEffect, useState, Suspense, memo } from 'react';
import { useSession, signOut } from "next-auth/react";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import { CatalogImage as Image } from '@/components/products/CatalogImage';
import useSWR from 'swr';
import { api } from '@/lib/api';
import CustomerMemoryControls from '@/components/profile/CustomerMemoryControls';
import { redirect } from 'next/navigation';
import { toast } from 'sonner'; 
import { Canvas, useFrame } from '@react-three/fiber';
import { Preload } from '@react-three/drei';
import * as THREE from 'three';

// Icons
import { 
  Camera, LogOut, Package, Key, User as UserIcon, LucideIcon
} from 'lucide-react';

// Modals
import {  
  ViewOrdersModal, 
  EditProfileDetailsModal, 
  ChangePasswordModal 
} from '@/components/profile/ProfileModals';

// ============================================================================
// --- TYPES & TOKENS ---
// ============================================================================
interface UserProfileData {
    id: number; 
    email: string; 
    full_name?: string | null; 
    role?: string | null;
    phone_number?: string | null; 
    address?: string | null; 
    avatar_url?: string | null;
    country?: string | null; 
    city?: string | null; 
    created_at?: string | null;
    orders_completed?: number; 
    items_favorited?: number;
}

interface ParticleFieldProps {
    count: number;
    radius: number;
    color: string;
    size: number;
    rotationSpeed: { x: number; y: number; z: number };
}

interface FloatingCardProps {
    title: string;
    image: string;
    category: string;
    delay: number;
    positionClasses: string;
    sizeClasses: string;
    colorCls: string;
    rotation: number;
    priority?: boolean;
}

interface IconButtonProps {
    icon: LucideIcon;
    label: string;
    onClick: () => void;
    colorClass: string;
    delay: number;
}

const TRANSITION_PREMIUM: [number, number, number, number] = [0.16, 1, 0.3, 1];

// ============================================================================
// --- 1. OPTIMIZED 3D BACKGROUND ---
// ============================================================================

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

const ParticleField = memo(({ count, radius, color, size, rotationSpeed }: ParticleFieldProps) => {
    const groupRef = useRef<THREE.Group>(null);
    const pointsRef = useRef<THREE.Points>(null);
    const positions = useMemo(() => createParticlePositions(count, radius), [count, radius]);
    const materialColor = useMemo(() => new THREE.Color(color), [color]);
    const prefersReducedMotion = useReducedMotion();

    useEffect(() => {
        if (pointsRef.current) pointsRef.current.matrixAutoUpdate = false;
    }, []);

    useFrame((_, delta) => {
        if (!groupRef.current || prefersReducedMotion) return;
        const safeDelta = Math.min(delta, 0.1);
        groupRef.current.rotation.x += safeDelta * rotationSpeed.x;
        groupRef.current.rotation.y += safeDelta * rotationSpeed.y;
        groupRef.current.rotation.z += safeDelta * rotationSpeed.z;
    });

    return (
        <group ref={groupRef} position={[0, 0, -60]}>
            <points ref={pointsRef} frustumCulled={true}>
                <bufferGeometry>
                    <bufferAttribute attach="attributes-position" args={[positions, 3]} />
                </bufferGeometry>
                <pointsMaterial 
                    transparent 
                    color={materialColor} 
                    size={size} 
                    sizeAttenuation 
                    depthWrite={false} 
                    toneMapped={false} 
                    opacity={0.8} 
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
    title, image, category, delay, positionClasses, sizeClasses, colorCls, rotation, priority = false
}: FloatingCardProps) => {
    const prefersReducedMotion = useReducedMotion();

    return (
        <motion.div
            className={`absolute z-0 ${positionClasses} ${sizeClasses} will-change-transform`}
            initial={{ opacity: 0, scale: prefersReducedMotion ? 1 : 0.8, rotate: prefersReducedMotion ? rotation : rotation + 10 }}
            animate={{ opacity: 1, scale: 1, rotate: rotation }}
            transition={{
                opacity: { duration: 1, delay },
                scale: { duration: 1, delay, type: "spring", stiffness: 100, damping: 20 }
            }}
            aria-hidden="true"
        >
            <motion.div
                animate={prefersReducedMotion ? {} : { y: [0, -15, 0] }}
                transition={{ duration: 6 + delay, repeat: Infinity, ease: "easeInOut" }}
                className="w-full h-full will-change-transform"
            >
                <div className={`relative w-full h-full rounded-[20px] lg:rounded-[32px] bg-zinc-900/80 backdrop-blur-md border border-white/10 shadow-2xl overflow-hidden group hover:scale-105 transition-transform duration-500 pointer-events-none ${colorCls}`}>
                    <div className="absolute inset-0 bg-gradient-to-t from-black/95 via-black/40 to-transparent z-10" />
                    <Image 
                        src={image} 
                        alt="" 
                        fill 
                        sizes="(max-width: 768px) 30vw, 20vw" 
                        className="object-cover opacity-60 lg:opacity-80 group-hover:opacity-100 transition-opacity duration-700" 
                        priority={priority}
                        loading={priority ? "eager" : "lazy"}
                    />

                    <div className="absolute bottom-3 left-3 right-3 lg:bottom-5 lg:left-5 lg:right-5 z-20 flex flex-col gap-0.5 lg:gap-1">
                        <span className="text-[9px] font-mono uppercase tracking-[0.1em] opacity-70 text-white break-words">{category}</span>
                        <h3 className="text-sm font-bold text-white tracking-wide leading-tight truncate">{title}</h3>
                    </div>

                    <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none rounded-[20px] lg:rounded-[32px] ring-2 ring-current ring-inset mix-blend-overlay" />
                </div>
            </motion.div>
        </motion.div>
    );
});
ProfileFloatingProduct.displayName = 'ProfileFloatingProduct';

// ============================================================================
// --- 3. ACCESSIBLE UI COMPONENTS ---
// ============================================================================

const IconButton = memo(({ icon: Icon, label, onClick, colorClass, delay }: IconButtonProps) => (
    <motion.button
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5, delay: delay, ease: TRANSITION_PREMIUM }}
        onClick={onClick}
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.95 }}
        aria-label={label}
        className="group relative flex items-center justify-center w-12 h-12 rounded-full bg-zinc-800/50 border border-white/10 backdrop-blur-md transition-all duration-300 hover:bg-zinc-700/80 hover:border-white/20 shadow-lg focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan-400 focus-visible:outline-offset-2"
    >
        <div className={`absolute inset-0 rounded-full blur-md transition-opacity duration-500 -z-10 opacity-0 group-hover:opacity-40 ${colorClass}`} aria-hidden="true" />
        <Icon size={20} className="text-zinc-300 group-hover:text-white transition-colors duration-300" aria-hidden="true" />
        
        {/* Visible Tooltip on Hover/Focus via CSS */}
        <span className="absolute -bottom-10 opacity-0 group-hover:opacity-100 group-focus-visible:opacity-100 transition-opacity duration-300 text-[11px] font-medium text-white whitespace-nowrap bg-zinc-900/90 px-2.5 py-1.5 rounded-lg border border-white/10 shadow-xl pointer-events-none z-50">
            {label}
        </span>
    </motion.button>
));
IconButton.displayName = 'IconButton';

// ============================================================================
// --- 4. MAIN PAGE COMPONENT ---
// ============================================================================

const HERO_CARDS: FloatingCardProps[] = [
    { title: "Apple Vision Pro", category: "Neural Tech", delay: 0.1, rotation: -8, image: "https://images.unsplash.com/photo-1696429175928-793a1cdef1d3?q=80&w=1000&auto=format&fit=crop", positionClasses: "top-[2%] left-[4%] lg:top-[8%] lg:left-[5%]", sizeClasses: "w-24 h-32 lg:w-48 lg:h-64", colorCls: "hover:shadow-cyan-500/20 text-cyan-400", priority: true },
    { title: "PS5 Console", category: "Hardware", delay: 0.2, rotation: 6, image: "https://images.unsplash.com/photo-1606144042614-b2417e99c4e3?q=80&w=600&auto=format&fit=crop", positionClasses: "top-[2%] right-[4%] lg:top-[8%] lg:right-[5%]", sizeClasses: "w-24 h-32 lg:w-40 lg:h-56", colorCls: "hover:shadow-purple-500/20 text-purple-400", priority: true },
    { title: "Dyson Airwrap", category: "Aesthetic", delay: 0.3, rotation: -4, image: "https://images.unsplash.com/photo-1755247339923-4fdfde950660?q=80&w=600&auto=format&fit=crop", positionClasses: "top-[40%] -left-[5%] lg:top-[45%] lg:left-[2%]", sizeClasses: "w-20 h-28 lg:w-40 lg:h-52", colorCls: "hover:shadow-pink-500/20 text-pink-400" },
    { title: "Sony WH-1000XM5", category: "Audio", delay: 0.4, rotation: 8, image: "https://images.unsplash.com/photo-1618366712010-f4ae9c647dcb?q=80&w=600&auto=format&fit=crop", positionClasses: "top-[40%] -right-[5%] lg:top-[45%] lg:right-[2%]", sizeClasses: "w-20 h-28 lg:w-44 lg:h-48", colorCls: "hover:shadow-amber-500/20 text-amber-400" },
    { title: "Leather Tote", category: "Bags", delay: 0.5, rotation: -6, image: "https://images.unsplash.com/photo-1691480150204-66dd1eb77391?q=80&w=600&auto=format&fit=crop", positionClasses: "bottom-[5%] left-[5%] lg:bottom-[15%] lg:left-[8%]", sizeClasses: "w-24 h-32 lg:w-36 lg:h-48", colorCls: "hover:shadow-emerald-500/20 text-emerald-400" },
    { title: "iPhone 17 Pro", category: "Electronics", delay: 0.6, rotation: 5, image: "https://images.unsplash.com/photo-1764746250417-2cc103a45a56?q=80&w=600&auto=format&fit=crop", positionClasses: "bottom-[5%] right-[5%] lg:bottom-[15%] lg:right-[8%]", sizeClasses: "w-24 h-32 lg:w-40 lg:h-56", colorCls: "hover:shadow-blue-500/20 text-blue-400" }
];

export default function ProfilePage() {
    const { data: session, status: sessionStatus, update: updateSession } = useSession();
    
    // Abstracted fetcher for cleaner SWR usage
    const fetchProfile = async (url: string) => {
        const res = await api.get(url);
        return res.data;
    };

    const { data: userData, mutate: mutateProfile } = useSWR<UserProfileData>(
        sessionStatus === 'authenticated' ? '/users/me' : null, 
        fetchProfile, 
        { revalidateOnFocus: false }
    );

    const [isMounted, setIsMounted] = useState(false);
    const [isEditDetailsModalOpen, setIsEditDetailsModalOpen] = useState(false);
    const [isPasswordModalOpen, setIsPasswordModalOpen] = useState(false);
    const [isOrdersModalOpen, setIsOrdersModalOpen] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    useEffect(() => { 
        setIsMounted(true); 
    }, []);

    // Redirect unauthenticated users immediately
    if (sessionStatus === 'unauthenticated') {
        redirect('/login');
    }

    const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file || !session?.accessToken) return;
        
        const formData = new FormData();
        formData.append('file', file);
        
        toast.promise((async () => {
            const response = await api.post<UserProfileData>('/users/me/avatar', formData, { 
                headers: { 'Content-Type': 'multipart/form-data' } 
            });
            await mutateProfile(response.data, false);
            if (response.data.avatar_url && session?.user) {
                await updateSession({ user: { ...session.user, image: response.data.avatar_url } });
            }
        })(), { 
            loading: 'Uploading photo...', 
            success: 'Profile photo updated successfully.', 
            error: 'Failed to upload photo. Please try again.' 
        });
    };

    // Fallback UI during SSR or initial hydration
    if (!isMounted) return <div className="min-h-screen bg-[#050505]" aria-hidden="true" />;

    const profileData = userData || {} as UserProfileData;
    const fallbackName = profileData?.full_name || 'User';
    const userImage = profileData?.avatar_url || session?.user?.image || `https://ui-avatars.com/api/?name=${encodeURIComponent(fallbackName)}&background=000000&color=ffffff&size=128`;

    return (
        <main className="relative min-h-[100svh] w-full bg-[#050505] overflow-hidden flex items-center justify-center font-sans">
            
            <input 
                type="file" 
                ref={fileInputRef} 
                onChange={handleFileChange} 
                accept="image/*" 
                className="hidden" 
                aria-hidden="true"
                tabIndex={-1}
            />

            {/* 3D Background */}
            <div className="absolute inset-0 z-0 pointer-events-none transform-gpu" style={{ contain: 'strict' }}>
                <Suspense fallback={null}>
                    <Canvas 
                        camera={{ position: [0, 0, 15], fov: 75 }} 
                        dpr={typeof window !== 'undefined' ? Math.min(window.devicePixelRatio, 2) : 1}
                        gl={{ antialias: false, powerPreference: "high-performance", alpha: true, depth: false, stencil: false }}
                    >
                        {/* Particle count reduced from original concept for better standard performance while maintaining aesthetic */}
                        <ParticleField count={10000} radius={60} color="#ffffff" size={0.07} rotationSpeed={{ x: -0.0001, y: -0.0001, z: -0.0008 }} />
                        <Preload all />
                    </Canvas>
                </Suspense>
            </div>

            {/* Ambient Brand Lighting */}
            <div className="absolute top-[10%] left-[10%] w-[50%] h-[50%] rounded-full bg-cyan-900/10 blur-[120px] pointer-events-none mix-blend-screen" aria-hidden="true" />
            <div className="absolute bottom-[10%] right-[10%] w-[50%] h-[50%] rounded-full bg-indigo-900/10 blur-[120px] pointer-events-none mix-blend-screen" aria-hidden="true" />
            
            <div className="container mx-auto px-5 sm:px-6 lg:px-12 relative z-10 h-full flex flex-col items-center justify-center min-h-[100svh]">
                
                {/* --- CENTRAL PROFILE CONTENT --- */}
                <div className="flex flex-col items-center text-center w-full max-w-[600px] relative z-30 pointer-events-auto pb-16 pt-28 sm:pt-24">
                    <motion.div 
                        initial={{ opacity: 0, y: 20 }} 
                        animate={{ opacity: 1, y: 0 }} 
                        transition={{ duration: 0.8, ease: TRANSITION_PREMIUM }}
                        className="flex flex-col items-center w-full"
                    >
                        {/* Interactive Avatar */}
                        <button 
                            className="relative w-24 h-24 lg:w-28 lg:h-28 mx-auto mb-6 rounded-full border border-white/20 bg-zinc-900 overflow-hidden shadow-2xl group hover:scale-105 transition-transform duration-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan-400 focus-visible:outline-offset-4"
                            onClick={() => fileInputRef.current?.click()}
                            aria-label="Change profile picture"
                        >
                            <div className="absolute inset-0 bg-gradient-to-tr from-white/5 to-transparent z-10 mix-blend-overlay pointer-events-none" />
                            <Image 
                                src={userImage} 
                                alt="" 
                                fill 
                                className="object-cover opacity-90 group-hover:opacity-30 transition-opacity duration-300" 
                                unoptimized={userImage.includes('ui-avatars')} // Only unoptimize external fallback avatars
                            />
                            <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity z-20 pointer-events-none">
                                <Camera className="text-white w-6 h-6 drop-shadow-lg" aria-hidden="true" />
                            </div>
                        </button>

                        {/* User Details */}
                        <div className="mb-8 w-full space-y-2">
                            <h1 className="text-3xl lg:text-4xl font-black text-white tracking-tight drop-shadow-lg px-2 truncate">
                                {profileData?.full_name || 'Welcome Back'}
                            </h1>
                            <p className="text-sm text-zinc-400 font-medium drop-shadow-md truncate max-w-[280px] mx-auto">
                                {profileData?.email || (sessionStatus === 'loading' ? 'Verifying identity...' : '')}
                            </p>
                        </div>

                        {/* Action Bar */}
                        <div className="flex items-center justify-center gap-3 sm:gap-5">
                            <IconButton 
                                icon={Package} 
                                label="View Orders" 
                                delay={0.1}
                                onClick={() => setIsOrdersModalOpen(true)}
                                colorClass="bg-cyan-500"
                            />
                            <IconButton 
                                icon={UserIcon} 
                                label="Edit Profile" 
                                delay={0.2}
                                onClick={() => setIsEditDetailsModalOpen(true)}
                                colorClass="bg-purple-500"
                            />
                            <IconButton 
                                icon={Key} 
                                label="Security" 
                                delay={0.3}
                                onClick={() => setIsPasswordModalOpen(true)}
                                colorClass="bg-emerald-500"
                            />
                            <div className="w-px h-8 bg-white/10 mx-1" aria-hidden="true" />
                            <IconButton 
                                icon={LogOut} 
                                label="Sign Out" 
                                delay={0.4}
                                onClick={() => signOut({ callbackUrl: '/login' })}
                                colorClass="bg-red-500"
                            />
                        </div>
                        <CustomerMemoryControls />
                    </motion.div>
                </div>

                {/* Floating Product Decor */}
                <div className="absolute inset-0 pointer-events-none z-0 flex items-center justify-center perspective-1000 opacity-25 sm:opacity-100">
                    <motion.div
                        initial={{ opacity: 0 }} 
                        animate={{ opacity: 1 }} 
                        transition={{ duration: 1.2, ease: TRANSITION_PREMIUM, delay: 0.2 }}
                        className="relative w-full max-w-7xl h-full flex items-center justify-center"
                    >
                        {HERO_CARDS.map((card, idx) => (
                            <ProfileFloatingProduct key={idx} {...card} />
                        ))}
                    </motion.div>
                </div>

            </div>

            {/* Modals */}
            <EditProfileDetailsModal 
                isOpen={isEditDetailsModalOpen} 
                onClose={() => setIsEditDetailsModalOpen(false)} 
                userData={profileData} 
                onSave={async (d: Partial<UserProfileData>) => { 
                    await api.put('/users/me', d); 
                    mutateProfile(); 
                    setIsEditDetailsModalOpen(false); 
                }} 
            />
            <ChangePasswordModal 
                isOpen={isPasswordModalOpen} 
                onClose={() => setIsPasswordModalOpen(false)} 
                onSave={async (c: string, n: string) => { 
                    await api.post('/users/me/change-password', { current_password: c, new_password: n }); 
                    setIsPasswordModalOpen(false); 
                }} 
            />
            <ViewOrdersModal 
                isOpen={isOrdersModalOpen} 
                onClose={() => setIsOrdersModalOpen(false)} 
            />
        </main>
    );
}
