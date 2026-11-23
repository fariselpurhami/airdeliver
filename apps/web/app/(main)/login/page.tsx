//** apps/web/app/(main)/login/page.tsx **//

'use client';

import React, { useState, Suspense, useEffect, useMemo, memo, useRef, useId } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { signIn } from "next-auth/react";
import { registerAccount, safeCallbackPath } from '@/lib/auth-flow';
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import { Canvas, useFrame } from '@react-three/fiber';
import { Preload } from '@react-three/drei';
import Image from 'next/image';
import { Mail, Lock, User, ArrowRight, LucideIcon } from 'lucide-react';
import * as THREE from 'three';
import { FloatingHeroCards, HERO_STAGE_CLASSES } from '@/components/hero/FloatingHeroCards';
import { MobileHomeFloatingCards } from '@/components/hero/MobileHomeFloatingCards';

// ============================================================================
// --- TYPES & TOKENS ---
// ============================================================================

type AuthVariant = 'SIGNIN' | 'SIGNUP';

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

interface FormInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
    icon: LucideIcon;
    label: string;
    error?: string;
}

const TRANSITION_PREMIUM: [number, number, number, number] = [0.16, 1, 0.3, 1];

// ============================================================================
// --- 1. HIGH-PERFORMANCE 3D BACKGROUND ---
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

const AuthFloatingProduct = memo(({
    title, image, category, delay, positionClasses, sizeClasses, colorCls, rotation, priority = false
}: FloatingCardProps) => {
    const prefersReducedMotion = useReducedMotion();

    return (
        <motion.div
            className={`absolute z-0 ${positionClasses} ${sizeClasses} will-change-transform`}
            initial={{ opacity: 0, scale: prefersReducedMotion ? 1 : 0.8, rotate: prefersReducedMotion ? rotation : rotation + 10 }}
            animate={{ opacity: 1, scale: 1, rotate: rotation }}
            transition={{ opacity: { duration: 1, delay }, scale: { duration: 1, delay, type: "spring", stiffness: 100, damping: 20 } }}
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
                        <span className="text-[9px] font-mono uppercase tracking-widest opacity-70 text-white truncate">{category}</span>
                        <h3 className="text-sm font-bold text-white tracking-wide leading-tight truncate">{title}</h3>
                    </div>
                    <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none rounded-[20px] lg:rounded-[32px] ring-2 ring-current ring-inset mix-blend-overlay" />
                </div>
            </motion.div>
        </motion.div>
    );
});
AuthFloatingProduct.displayName = 'AuthFloatingProduct';

// ============================================================================
// --- 3. ACCESSIBLE UI COMPONENTS ---
// ============================================================================

const FormInput = memo(({ icon: Icon, label, error, id, ...props }: FormInputProps) => {
    const generatedId = useId();
    const inputId = id || generatedId;
    const errorId = `${inputId}-error`;

    return (
        <div className="w-full space-y-1.5 transform-gpu">
            <label htmlFor={inputId} className="block text-left text-xs font-semibold text-zinc-300 ml-2">
                {label}
            </label>
            <div className="relative group">
                <div className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-500 group-focus-within:text-cyan-400 transition-colors duration-300 z-10 pointer-events-none">
                    <Icon size={18} aria-hidden="true" />
                </div>
                <input
                    id={inputId}
                    aria-invalid={!!error}
                    aria-errormessage={error ? errorId : undefined}
                    {...props}
                    className={`w-full bg-zinc-900/90 border ${error ? 'border-red-500' : 'border-white/10'} rounded-full py-3.5 pl-12 pr-5 text-white text-[16px] md:text-sm placeholder-zinc-500 focus:border-cyan-500 focus:bg-zinc-950 backdrop-blur-xl transition-all duration-300 shadow-lg focus:shadow-[0_0_20px_rgba(6,182,212,0.15)] outline-none disabled:opacity-50 disabled:cursor-not-allowed`}
                />
            </div>
            {error && (
                <p id={errorId} className="text-[11px] text-red-400 ml-2 font-medium" role="alert">
                    {error}
                </p>
            )}
        </div>
    );
});
FormInput.displayName = 'FormInput';

const SubmitButton = memo(({ children, isLoading }: { children: React.ReactNode, isLoading: boolean }) => (
    <motion.button
        whileHover={{ scale: 1.01 }}
        whileTap={{ scale: 0.98 }}
        type="submit"
        disabled={isLoading}
        aria-disabled={isLoading}
        className="relative flex items-center justify-center w-full overflow-hidden rounded-full py-3.5 px-6 text-sm font-bold text-black bg-white hover:bg-cyan-50 hover:text-cyan-900 transition-colors duration-300 shadow-xl disabled:opacity-70 disabled:cursor-not-allowed group"
    >
        {isLoading ? (
            <span className="flex items-center gap-2" aria-live="polite">
                <span className="sr-only">Authenticating...</span>
                <span className="w-1.5 h-1.5 bg-black rounded-full animate-bounce" />
                <span className="w-1.5 h-1.5 bg-black rounded-full animate-bounce delay-100" />
                <span className="w-1.5 h-1.5 bg-black rounded-full animate-bounce delay-200" />
            </span>
        ) : (
            children
        )}
    </motion.button>
));
SubmitButton.displayName = 'SubmitButton';

// ============================================================================
// --- 4. FORMS ---
// ============================================================================

const SignUpForm = memo(({ onSwitch }: { onSwitch: () => void }) => {
    const router = useRouter();
    const searchParams = useSearchParams();
    const [isLoading, setIsLoading] = useState(false);
    const [formData, setFormData] = useState({ fullName: '', email: '', password: '' });
    const [error, setError] = useState('');
    const busy = useRef(false);

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setFormData(prev => ({ ...prev, [e.target.name]: e.target.value }));
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (busy.current) return;
        busy.current = true;
        setIsLoading(true); 
        setError('');

        try {
            await registerAccount(formData);
            const result = await signIn('credentials', {
                redirect: false,
                email: formData.email,
                password: formData.password,
            });
            
            if (result?.error) {
                setError('Your account was created, but sign-in could not finish. Try signing in.');
            } else if (result?.ok) {
                router.refresh();
                router.push(safeCallbackPath(searchParams.get('callbackUrl')));
            }
        } catch (err) {
            setError('Registration could not be confirmed. If you already created this account, try signing in. Otherwise check your email and use a password of 8 to 128 characters.');
        } finally {
            busy.current = false;
            setIsLoading(false);
        }
    };

    return (
        <motion.div initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -15 }} transition={{ duration: 0.6, ease: TRANSITION_PREMIUM }} className="w-full space-y-8">
            <div className="text-center space-y-3">
                <h1 className="text-4xl sm:text-6xl lg:text-[clamp(36px,4.4vw,76px)] font-black uppercase tracking-tighter text-white drop-shadow-2xl leading-[1.05] sm:leading-[0.95]" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                    Create an <br />
                    <span className="text-transparent bg-clip-text bg-gradient-to-r from-white via-cyan-200 to-zinc-400">
                        account
                    </span>
                </h1>
                <p className="text-sm text-zinc-400 font-light max-w-[260px] mx-auto">
                    Join airdeliver to experience the future of commerce.
                </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4 max-w-[320px] mx-auto w-full relative z-30" noValidate>
                <FormInput icon={User} label="Full Name" name="fullName" type="text" placeholder="Jane Doe" required disabled={isLoading} value={formData.fullName} onChange={handleChange} />
                <FormInput icon={Mail} label="Email Address" name="email" type="email" placeholder="jane@example.com" required disabled={isLoading} value={formData.email} onChange={handleChange} />
                <FormInput icon={Lock} label="Password" name="password" type="password" minLength={8} maxLength={128} placeholder="••••••••" required disabled={isLoading} value={formData.password} onChange={handleChange} />
                
                {error && (
                    <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-xl backdrop-blur-md" role="alert" aria-live="assertive">
                        <p className="text-xs text-red-400 text-center font-medium">{error}</p>
                    </div>
                )}

                <div className="pt-2">
                    <SubmitButton isLoading={isLoading}>
                        Sign Up <ArrowRight size={16} className="ml-2 group-hover:translate-x-1 transition-transform" />
                    </SubmitButton>
                </div>
            </form>

            <div className="text-center relative z-30">
                <p className="text-zinc-400 text-sm font-light">
                    Already have an account?{' '}
                    <button type="button" onClick={onSwitch} className="text-white hover:text-cyan-300 font-medium transition-colors duration-300 focus-visible:outline-cyan-400 focus-visible:underline rounded-sm">
                        Sign in
                    </button>
                </p>
            </div>
        </motion.div>
    );
});
SignUpForm.displayName = 'SignUpForm';

const SignInForm = memo(({ onSwitch }: { onSwitch: () => void }) => {
    const router = useRouter();
    const searchParams = useSearchParams();
    const [isLoading, setIsLoading] = useState(false);
    const [formData, setFormData] = useState({ email: '', password: '' });
    const [error, setError] = useState('');
    const busy = useRef(false);

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setFormData(prev => ({ ...prev, [e.target.name]: e.target.value }));
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (busy.current) return;
        busy.current = true;
        setIsLoading(true); 
        setError('');

        try {
            const result = await signIn('credentials', { 
                redirect: false, 
                email: formData.email, 
                password: formData.password 
            });
            
            if (result?.error) {
                setError('Invalid email or password.');
            } else if (result?.ok) {
                router.refresh();
                router.push(safeCallbackPath(searchParams.get('callbackUrl')));
            }
        } catch (err) {
            setError('An unexpected error occurred. Please try again.');
        } finally {
            busy.current = false;
            setIsLoading(false);
        }
    };

    return (
        <motion.div initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -15 }} transition={{ duration: 0.6, ease: TRANSITION_PREMIUM }} className="w-full space-y-8">
            <div className="text-center space-y-3">
                <h1 className="text-4xl sm:text-6xl lg:text-[clamp(36px,4.4vw,76px)] font-black uppercase tracking-tighter text-white drop-shadow-2xl leading-[1.05] sm:leading-[0.95]" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                    Welcome <br />
                    <span className="text-transparent bg-clip-text bg-gradient-to-r from-white via-cyan-200 to-zinc-400">
                        back
                    </span>
                </h1>
                <p className="text-sm text-zinc-400 font-light max-w-[260px] mx-auto">
                    Sign in to manage your deliveries and track your orders.
                </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4 max-w-[320px] mx-auto w-full relative z-30" noValidate>
                <FormInput icon={Mail} label="Email Address" name="email" type="email" placeholder="jane@example.com" required disabled={isLoading} value={formData.email} onChange={handleChange} />
                <div className="space-y-2">
                    <FormInput icon={Lock} label="Password" name="password" type="password" placeholder="••••••••" required disabled={isLoading} value={formData.password} onChange={handleChange} />
                    <div className="flex justify-end px-1">
                        <button type="button" className="text-xs text-zinc-400 hover:text-white transition-colors focus-visible:outline-cyan-400 rounded-sm">
                            Forgot password?
                        </button>
                    </div>
                </div>
                
                {error && (
                    <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-xl backdrop-blur-md" role="alert" aria-live="assertive">
                        <p className="text-xs text-red-400 text-center font-medium">{error}</p>
                    </div>
                )}

                <div className="pt-2">
                    <SubmitButton isLoading={isLoading}>Sign In</SubmitButton>
                </div>
            </form>

            <div className="text-center relative z-30">
                <p className="text-zinc-400 text-sm font-light">
                    Don't have an account?{' '}
                    <button type="button" onClick={onSwitch} className="text-white hover:text-cyan-300 font-medium transition-colors duration-300 focus-visible:outline-cyan-400 focus-visible:underline rounded-sm">
                        Create an account
                    </button>
                </p>
            </div>
        </motion.div>
    );
});
SignInForm.displayName = 'SignInForm';

// ============================================================================
// --- 5. PAGE ORCHESTRATOR ---
// ============================================================================

const HERO_CARDS: FloatingCardProps[] = [
    { title: "Apple Vision Pro", category: "Neural Tech", delay: 0.1, rotation: -8, image: "https://images.unsplash.com/photo-1696429175928-793a1cdef1d3?q=80&w=1000&auto=format&fit=crop", positionClasses: "top-[12%] left-[4%] lg:top-[8%] lg:left-[5%]", sizeClasses: "w-24 h-32 lg:w-48 lg:h-64", colorCls: "hover:shadow-cyan-500/20 text-cyan-400", priority: true },
    { title: "PS5 Console", category: "Hardware", delay: 0.2, rotation: 6, image: "https://images.unsplash.com/photo-1606144042614-b2417e99c4e3?q=80&w=600&auto=format&fit=crop", positionClasses: "top-[12%] right-[4%] lg:top-[8%] lg:right-[5%]", sizeClasses: "w-24 h-32 lg:w-40 lg:h-56", colorCls: "hover:shadow-purple-500/20 text-purple-400", priority: true },
    { title: "Dyson Airwrap", category: "Aesthetic", delay: 0.3, rotation: -4, image: "https://images.unsplash.com/photo-1755247339923-4fdfde950660?q=80&w=600&auto=format&fit=crop", positionClasses: "top-[60%] -left-[5%] lg:top-[45%] lg:left-[2%]", sizeClasses: "w-20 h-28 lg:w-40 lg:h-52", colorCls: "hover:shadow-pink-500/20 text-pink-400" },
    { title: "Sony WH-1000XM5", category: "Audio", delay: 0.4, rotation: 8, image: "https://images.unsplash.com/photo-1618366712010-f4ae9c647dcb?q=80&w=600&auto=format&fit=crop", positionClasses: "top-[60%] -right-[5%] lg:top-[45%] lg:right-[2%]", sizeClasses: "w-20 h-28 lg:w-44 lg:h-48", colorCls: "hover:shadow-amber-500/20 text-amber-400" },
    { title: "Leather Tote", category: "Bags", delay: 0.5, rotation: -6, image: "https://images.unsplash.com/photo-1691480150204-66dd1eb77391?q=80&w=600&auto=format&fit=crop", positionClasses: "bottom-[5%] left-[5%] lg:bottom-[15%] lg:left-[8%]", sizeClasses: "w-24 h-32 lg:w-36 lg:h-48", colorCls: "hover:shadow-emerald-500/20 text-emerald-400" },
    { title: "iPhone 17 Pro", category: "Electronics", delay: 0.6, rotation: 5, image: "https://images.unsplash.com/photo-1764746250417-2cc103a45a56?q=80&w=600&auto=format&fit=crop", positionClasses: "bottom-[5%] right-[5%] lg:bottom-[15%] lg:right-[8%]", sizeClasses: "w-24 h-32 lg:w-40 lg:h-56", colorCls: "hover:shadow-blue-500/20 text-blue-400" }
];

function AuthFormOrchestrator() {
    const searchParams = useSearchParams();
    const mode = searchParams.get('mode');
    const [variant, setVariant] = useState<AuthVariant>(mode === 'SIGNUP' ? 'SIGNUP' : 'SIGNIN');

    const toggleVariant = () => setVariant(prev => prev === 'SIGNIN' ? 'SIGNUP' : 'SIGNIN');

    return (
        <AnimatePresence mode="wait">
            {variant === 'SIGNIN' ? (
                <SignInForm key="signin" onSwitch={toggleVariant} />
            ) : (
                <SignUpForm key="signup" onSwitch={toggleVariant} />
            )}
        </AnimatePresence>
    );
}

export default function AuthPage() {
    const [isMounted, setIsMounted] = useState(false);

    useEffect(() => {
        setIsMounted(true);
    }, []);

    // SSR graceful fallback
    if (!isMounted) return <div className="min-h-screen bg-[#050505]" aria-hidden="true" />;

    return (
        <main className={`${HERO_STAGE_CLASSES} max-lg:min-h-[100svh] max-lg:pt-28 max-lg:pb-16 bg-[#050505] font-sans`} data-hero-stage="auth">
            
            {/* 3D Background */}
            <div className="absolute inset-0 z-0 pointer-events-none transform-gpu opacity-25" style={{ contain: 'strict' }}>
                <Suspense fallback={null}>
                    <Canvas 
                        camera={{ position: [0, 0, 15], fov: 75 }} 
                        dpr={typeof window !== 'undefined' ? Math.min(window.devicePixelRatio, 2) : 1}
                        gl={{ antialias: false, powerPreference: "high-performance", alpha: true, depth: false, stencil: false }}
                    >
                        <ParticleField count={10000} radius={60} color="#ffffff" size={0.07} rotationSpeed={{ x: -0.0001, y: -0.0001, z: -0.0008 }} />
                        <Preload all />
                    </Canvas>
                </Suspense>
            </div>
            
            <div className="contents">
                
                {/* Auth Form Container */}
                <div className="relative z-30 w-full max-w-3xl lg:max-w-[48%] mx-auto px-4 sm:px-6 text-center pointer-events-auto before:absolute before:inset-0 before:bg-[radial-gradient(ellipse_at_center,rgba(5,5,5,0.98)_0%,rgba(5,5,5,0.92)_55%,transparent_100%)] before:rounded-[40px] before:-z-10">
                    <Suspense fallback={<div className="h-[400px] flex items-center justify-center"><div className="w-8 h-8 border-2 border-white border-t-transparent rounded-full animate-spin" aria-label="Loading authentication forms..." /></div>}>
                        <AuthFormOrchestrator />
                    </Suspense>
                </div>

                {/* Same stage, card components and mobile frame as products. */}
                <div className="hidden lg:contents"><FloatingHeroCards /></div>
                <div className="absolute inset-x-5 top-28 bottom-16 lg:hidden pointer-events-none" data-mobile-auth-distribution style={{ opacity: 0.32 }}><MobileHomeFloatingCards /></div>

            </div>
        </main>
    );
}
