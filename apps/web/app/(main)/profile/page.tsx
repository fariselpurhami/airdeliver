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
import {
    User, Mail, MapPin, Phone, Clock, Loader2, LogOut, AlertCircle,
    CreditCard, Package, ShieldCheck, Edit3, KeyRound, Settings, Camera, ChevronRight, Box, Lock, Activity
} from 'lucide-react';
import {  
  ViewOrdersModal, 
  EditProfileDetailsModal, 
  ChangePasswordModal 
} from '@/components/profile/ProfileModals';
import dynamic from 'next/dynamic';
import { Canvas, useFrame } from '@react-three/fiber';
import { Points, PointMaterial } from '@react-three/drei';
import * as THREE from 'three';

// ============================================================================
// --- TYPE DEFINITIONS ---
// ============================================================================
interface UserProfileData {
    id: number; email: string; full_name?: string | null; role?: string | null;
    phone_number?: string | null; address?: string | null; avatar_url?: string | null;
    country?: string | null; city?: string | null; created_at?: string | null;
    orders_completed?: number; items_favorited?: number;
    stripe_customer_id?: string | null; 
}

interface OrderRead {
    id: number; user_id: number; status: string; total_price: number;
    created_at: string; items: OrderItemRead[];
}

interface OrderItemRead {
    id: number; product_id: number; quantity: number;
    price_per_unit: number; product?: ProductRead | null;
}

interface ProductRead {
    id: number; name: string; description?: string | null;
    price: number; inventory: number; image_url?: string | null;
}

interface PaginatedOrdersResponse {
    total: number; page: number; limit: number; orders: OrderRead[];
}

interface DefaultPaymentData {
    brand: string | null;
    last4: string | null;
}

// ============================================================================
// --- 1. ARCHITECTURAL BACKGROUND (Premium Network Globe) ---
// ============================================================================
const NetworkGlobe = () => {
  const ref = useRef<THREE.Group>(null!);
  
  // Create a sophisticated Fibonacci sphere (Apple/Stripe style globe)
  const points = useMemo(() => {
    const pts = [];
    const numPoints = 2500;
    const radius = 12;
    for (let i = 0; i < numPoints; i++) {
        const phi = Math.acos(-1 + (2 * i) / numPoints);
        const theta = Math.sqrt(numPoints * Math.PI) * phi;
        pts.push(
            radius * Math.cos(theta) * Math.sin(phi),
            radius * Math.sin(theta) * Math.sin(phi),
            radius * Math.cos(phi)
        );
    }
    return new Float32Array(pts);
  }, []);

  useFrame((state, delta) => {
    if (ref.current) {
      ref.current.rotation.y += delta * 0.05; // Slow, elegant rotation
      ref.current.rotation.x = Math.sin(state.clock.elapsedTime * 0.1) * 0.1; // Gentle floating
    }
  });

  return (
    <group ref={ref} position={[0, -5, -15]} rotation={[0.2, 0, 0]}>
      <Points positions={points}>
        <PointMaterial transparent color="#ffffff" size={0.06} opacity={0.25} depthWrite={false} />
      </Points>
    </group>
  );
};

const ProfileBackground = memo(() => {
    return (
        <>
            <fog attach="fog" args={['#050505', 10, 40]} />
            <ambientLight intensity={0.4} />
            <directionalLight position={[10, 10, 5]} intensity={1} color="#ffffff" />
            <directionalLight position={[-10, -10, -5]} intensity={1} color="#3b82f6" />
            <NetworkGlobe />
        </>
    );
});
ProfileBackground.displayName = "ProfileBackground";

const DynamicProfileBackground = dynamic(() => Promise.resolve(ProfileBackground), { 
    ssr: false,
    loading: () => null
});

// ============================================================================
// --- 2. MAIN PROFILE COMPONENT (Corporate Premium UI) ---
// ============================================================================
export default function ProfilePage() {
    const { data: session, status: sessionStatus, update: updateSession } = useSession();
    
    const profileApiUrl = '/users/me';
    const ordersApiUrl = '/orders/me?page=1&limit=3';
    const paymentApiUrl = '/users/me/default-payment-method'; 
    const swrFetcher = (url: string) => api.get(url).then(res => res.data);

    const { data: userData, error: userError, isLoading: isLoadingUser, mutate: mutateProfile } = useSWR<UserProfileData>(
        sessionStatus === 'authenticated' ? profileApiUrl : null, swrFetcher, { revalidateOnFocus: false }
    );
    const { data: ordersData, isLoading: isLoadingOrders } = useSWR<PaginatedOrdersResponse>(
        sessionStatus === 'authenticated' ? ordersApiUrl : null, swrFetcher, { revalidateOnFocus: false }
    );
    const { data: paymentData } = useSWR<DefaultPaymentData>(
        sessionStatus === 'authenticated' ? paymentApiUrl : null, swrFetcher, { revalidateOnFocus: false }
    );

    useEffect(() => {
        if (userError) signOut({ callbackUrl: '/login' });
    }, [userError]);

    const [isClient, setIsClient] = useState(false);
    const [isEditDetailsModalOpen, setIsEditDetailsModalOpen] = useState(false);
    const [isPasswordModalOpen, setIsPasswordModalOpen] = useState(false);
    const [isOrdersModalOpen, setIsOrdersModalOpen] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    useEffect(() => { setIsClient(true); }, []);

    const joinedDate = useMemo(() => (
        userData?.created_at ? new Date(userData.created_at).toLocaleDateString('en-US', { year: 'numeric', month: 'long' }) : null
    ), [userData?.created_at]);

    const realShippingInfo = useMemo(() => (
        [userData?.address, userData?.city, userData?.country].filter(Boolean).join(', ') || null
    ), [userData?.address, userData?.city, userData?.country]);

    const handleProfileDetailsSave = async (updatedData: Partial<UserProfileData>) => {
        if (!session?.accessToken) { toast.error("Authentication error."); return; }
        toast.promise((async () => {
                const response = await api.put<UserProfileData>(profileApiUrl, updatedData);
                mutateProfile(response.data, false);
                if (updatedData.full_name && session?.user) await updateSession({ user: { ...session.user, name: updatedData.full_name } });
                setIsEditDetailsModalOpen(false);
                return response.data;
            })(), { loading: 'Updating profile...', success: 'Profile updated successfully.', error: 'Failed to update profile.' }
        );
    };

    const handlePasswordSave = async (currentPassword: string, newPassword: string) => {
        if (!session?.accessToken) return;
        toast.promise((async () => {
                await api.post('/users/me/change-password', { current_password: currentPassword, new_password: newPassword });
                setIsPasswordModalOpen(false);
             })(), { loading: 'Updating security settings...', success: 'Password changed successfully.', error: 'Failed to change password.' }
        );
    };

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

    const isSystemLoading = !isClient || sessionStatus === 'loading' || (sessionStatus === 'authenticated' && isLoadingUser);

    if (sessionStatus === 'unauthenticated') redirect('/login');
    if (isClient && userError) return <ErrorDisplay message={(userError as any)?.message} />;

    const profileData = userData || {} as UserProfileData;
    const userImage = profileData?.avatar_url || session?.user?.image || `https://ui-avatars.com/api/?name=${encodeURIComponent(profileData?.full_name || session?.user?.email || 'A')}&background=E5E7EB&color=000000&bold=true&size=128`;

    return (
        <>
            <input type="file" ref={fileInputRef} onChange={handleFileChange} accept="image/*" className="hidden" />

            <main className="relative min-h-screen w-full bg-[#050505] text-gray-200 pt-28 pb-16 px-4 md:px-8 overflow-x-hidden">
                {/* 3D Background */}
                <div className="fixed inset-0 z-0 opacity-80 pointer-events-none transform-gpu">
                    <Canvas camera={{ position: [0, 2, 15], fov: 50 }} dpr={[1, 2]} performance={{ min: 0.5 }}>
                        <Suspense fallback={null}><DynamicProfileBackground /></Suspense>
                    </Canvas>
                    <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_0%,#050505_100%)]" />
                </div>

                <AnimatePresence mode="wait">
                    {isSystemLoading ? (
                        <LoadingScreen key="loading" />
                    ) : (
                        <motion.div 
                            key="content"
                            initial={{ opacity: 0, y: 20, filter: "blur(8px)" }}
                            animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                            transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
                            className="relative z-10 w-full max-w-6xl mx-auto space-y-8"
                        >
                            {/* --- HEADER: USER IDENTITY --- */}
                            <header className="relative w-full rounded-3xl border border-white/[0.08] bg-white/[0.02] p-8 md:p-12 backdrop-blur-2xl shadow-2xl">
                                <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-white/20 to-transparent" />
                                
                                <div className="relative z-10 flex flex-col md:flex-row items-center md:items-start gap-8">
                                    {/* Avatar */}
                                    <div className="relative group shrink-0">
                                        <div className="relative h-32 w-32 md:h-40 md:w-40 rounded-full p-1 bg-gradient-to-b from-white/20 to-transparent shadow-2xl">
                                            <div className="absolute inset-0 bg-black rounded-full" />
                                            <Image
                                                src={userImage} alt="Profile" fill 
                                                className="rounded-full object-cover relative z-10" unoptimized
                                            />
                                            <div 
                                                className="absolute inset-0 z-20 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex flex-col items-center justify-center cursor-pointer rounded-full backdrop-blur-sm" 
                                                onClick={() => fileInputRef.current?.click()}
                                            >
                                                <Camera className="text-white h-6 w-6 mb-2" />
                                                <span className="text-xs font-medium text-white">Edit</span>
                                            </div>
                                        </div>
                                    </div>
                                    
                                    {/* Identity Data */}
                                    <div className="flex-1 text-center md:text-left space-y-3 pt-4">
                                        <div className="inline-flex items-center gap-1.5 text-emerald-400/90">
                                            <ShieldCheck size={14} />
                                            <span className="text-white text-[11px] font-extralight tracking-[0.4em] max-w-sm">VERIFIED</span>
                                        </div>
                                        
                                        <h1 className="text-4xl md:text-5xl font-semibold text-white tracking-tight">
                                            {profileData?.full_name || 'Account Setup'}
                                        </h1>
                                        
                                        <div className="flex flex-wrap items-center justify-center md:justify-start gap-4 text-sm text-gray-400">
                                            <span className="flex items-center gap-1.5"><Mail size={16} /> {profileData.email}</span>
                                            {joinedDate && <span className="flex items-center gap-1.5"><Clock size={16} /> Member since {joinedDate}</span>}
                                        </div>

                                        <div className="flex flex-wrap items-center justify-center md:justify-start gap-8 pt-4">
                                            <StatItem label="Total Orders" value={profileData?.orders_completed || 0} />
                                            <div className="w-px h-8 bg-white/10" />
                                            <StatItem label="Saved Items" value={profileData?.items_favorited || 0} />
                                        </div>
                                    </div>
                                </div>
                            </header>

                            {/* --- GRID: INFORMATION & SETTINGS --- */}
                            <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
                                
                                {/* Left Column: Personal Data & Orders */}
                                <div className="xl:col-span-2 space-y-8">
                                    {/* Personal Info */}
                                    <GlassPanel title="Personal Information" icon={<User className="text-gray-400" />}>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-6">
                                            <DataField label="Full Name" value={profileData?.full_name} />
                                            <DataField label="Email Address" value={profileData?.email} />
                                            <DataField label="Phone Number" value={profileData?.phone_number} />
                                            <DataField label="Shipping Address" value={realShippingInfo} />
                                        </div>
                                    </GlassPanel>

                                    {/* Connectivity / Integrations */}
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                        <IntegrationCard 
                                            icon={<CreditCard className="text-gray-300" />} title="Payment Method"
                                            status={paymentData?.brand ? 'Connected' : 'Not Configured'}
                                            value={paymentData?.brand ? `${paymentData.brand.toUpperCase()} •••• ${paymentData.last4}` : 'Add a payment method'}
                                            isActive={!!paymentData?.brand}
                                        />
                                        <IntegrationCard 
                                            icon={<MapPin className="text-gray-300" />} title="Delivery Location"
                                            status={realShippingInfo ? 'Verified' : 'Pending'}
                                            value={realShippingInfo ? `${userData?.city}, ${userData?.country}` : 'Add delivery location'}
                                            isActive={!!realShippingInfo}
                                        />
                                    </div>

                                    {/* Recent Orders */}
                                    <GlassPanel title="Order History" icon={<Box className="text-gray-400" />} action={{ label: "View All", onClick: () => setIsOrdersModalOpen(true) }}>
                                        {isLoadingOrders ? (
                                            <div className="py-8 flex justify-center"><Loader2 className="w-6 h-6 animate-spin text-gray-400" /></div>
                                        ) : ordersData?.orders && ordersData.orders.length > 0 ? (
                                            <div className="space-y-3">
                                                {ordersData.orders.map(order => <OrderCard key={order.id} order={order} />)}
                                            </div>
                                        ) : (
                                            <div className="flex flex-col items-center justify-center py-10 text-gray-500 bg-white/[0.02] rounded-2xl border border-dashed border-white/10">
                                                <Package className="w-10 h-10 mb-3 text-gray-600" />
                                                <p className="text-sm">No orders placed yet.</p>
                                            </div>
                                        )}
                                    </GlassPanel>
                                </div>

                                {/* Right Column: Account Settings */}
                                <div className="xl:col-span-1">
                                    <div className="sticky top-32 space-y-6">
                                        <div className="rounded-3xl border border-white/[0.08] bg-white/[0.02] backdrop-blur-3xl p-6 shadow-2xl">
                                            <h3 className="text-lg font-semibold text-white mb-6 flex items-center gap-2">
                                                <Settings className="w-5 h-5 text-gray-400" /> 
                                                Account Settings
                                            </h3>
                                            
                                            <div className="space-y-2">
                                                <SettingMenuButton icon={<Edit3 size={18}/>} title="Edit Profile" onClick={() => setIsEditDetailsModalOpen(true)} />
                                                <SettingMenuButton icon={<Lock size={18}/>} title="Security" onClick={() => setIsPasswordModalOpen(true)} />
                                            </div>
                                            
                                            <div className="h-px bg-white/[0.08] my-6" />
                                            
                                            <button 
                                                onClick={() => signOut({ callbackUrl: '/login' })}
                                                className="w-full flex items-center justify-between p-4 rounded-xl bg-white/[0.02] hover:bg-white/[0.05] border border-transparent hover:border-white/10 transition-all text-red-400 group"
                                            >
                                                <span className="text-sm font-medium">Sign Out</span>
                                                <LogOut size={16} className="group-hover:translate-x-1 transition-transform" />
                                            </button>
                                        </div>
                                    </div>
                                </div>

                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </main>

            {/* Modals */}
            <EditProfileDetailsModal isOpen={isEditDetailsModalOpen} onClose={() => setIsEditDetailsModalOpen(false)} userData={profileData!} onSave={handleProfileDetailsSave} />
            <ChangePasswordModal isOpen={isPasswordModalOpen} onClose={() => setIsPasswordModalOpen(false)} onSave={handlePasswordSave} />
            <ViewOrdersModal isOpen={isOrdersModalOpen} onClose={() => setIsOrdersModalOpen(false)} />
        </>
    );
}

// ============================================================================
// --- 3. SUB-COMPONENTS (Premium Design System) ---
// ============================================================================

const LoadingScreen = memo(() => (
    <motion.div 
        exit={{ opacity: 0, filter: "blur(5px)" }}
        className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-[#050505]"
    >
        <div className="w-12 h-12 rounded-full border-2 border-white/10 border-t-white/80 animate-spin mb-4" />
        <h2 className="text-sm font-medium text-gray-400 tracking-wide">Loading Profile...</h2>
    </motion.div>
));
LoadingScreen.displayName = "LoadingScreen";

const ErrorDisplay = ({ message }: { message: string }) => (
    <div className="min-h-screen bg-[#050505] flex flex-col items-center justify-center p-4">
        <AlertCircle className="h-12 w-12 text-red-400 mb-4" />
        <h2 className="text-2xl font-semibold text-white mb-2">Something went wrong</h2>
        <p className='text-gray-400 text-sm'>{message || 'Please try refreshing the page.'}</p>
    </div>
);

const StatItem = ({ label, value }: { label: string, value: number }) => (
    <div className="flex flex-col">
        <span className="text-2xl font-bold text-white tabular-nums">{value}</span>
        <span className="text-xs text-gray-500 uppercase tracking-wider mt-1">{label}</span>
    </div>
);

const GlassPanel = ({ title, icon, children, action }: { title: string, icon: React.ReactNode, children: React.ReactNode, action?: { label: string, onClick: () => void } }) => (
    <div className="bg-white/[0.02] backdrop-blur-2xl border border-white/[0.08] rounded-3xl p-6 md:p-8">
        <div className="flex items-center justify-between mb-8">
            <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-white/[0.05] border border-white/5">{icon}</div>
                <h2 className="text-xl font-semibold text-white tracking-tight">{title}</h2>
            </div>
            {action && (
                <button onClick={action.onClick} className="text-sm font-medium text-blue-400 hover:text-blue-300 flex items-center gap-1 transition-colors">
                    {action.label} <ChevronRight size={16} />
                </button>
            )}
        </div>
        <div>{children}</div>
    </div>
);

const DataField = ({ label, value }: { label: string, value?: string | null }) => (
    <div className="flex flex-col space-y-1">
        <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">{label}</span>
        <span className="text-gray-200 font-medium text-sm md:text-base truncate">
            {value || <span className="text-gray-600 italic">Not provided</span>}
        </span>
    </div>
);

const IntegrationCard = ({ icon, title, status, value, isActive }: { icon: React.ReactNode, title: string, status: string, value: string, isActive: boolean }) => (
    <div className="p-5 rounded-2xl bg-white/[0.02] border border-white/[0.08] flex items-center gap-4 hover:bg-white/[0.04] transition-colors">
        <div className="p-3 rounded-xl bg-white/[0.05] shrink-0">
            {icon}
        </div>
        <div className="overflow-hidden">
            <h4 className="text-sm font-medium text-gray-200 mb-1">{title}</h4>
            <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${isActive ? 'bg-green-400' : 'bg-gray-500'}`} />
                <span className="text-xs text-gray-400 truncate">{value}</span>
            </div>
        </div>
    </div>
);

const OrderCard = memo(({ order }: { order: OrderRead }) => {
    const firstItem = order.items?.[0];
    const productName = firstItem?.product?.name || `Order #${order.id}`;
    
    const getStatusStyle = (status: string) => {
        const s = status.toLowerCase();
        if (['processing', 'paid', 'ordered', 'confirmed'].includes(s)) return 'text-blue-400 bg-blue-400/10 border-blue-400/20';
        if (s === 'delivered') return 'text-green-400 bg-green-400/10 border-green-400/20';
        if (s === 'cancelled') return 'text-red-400 bg-red-400/10 border-red-400/20';
        return 'text-gray-400 bg-gray-400/10 border-gray-400/20';
    };

    const statusStyle = getStatusStyle(order.status);
    const isCancelled = order.status.toLowerCase() === 'cancelled';

    return (
        <div className="group flex items-center justify-between p-4 rounded-2xl bg-white/[0.02] border border-white/[0.05] hover:border-white/10 transition-all">
            <div className="flex items-center gap-4">
                <div className="shrink-0 w-12 h-12 rounded-xl bg-white/[0.05] border border-white/[0.05] flex items-center justify-center">
                    <Package className={`w-5 h-5 ${isCancelled ? 'text-gray-600' : 'text-gray-300'}`} />
                </div>
                <div className="min-w-0">
                    <h4 className={`font-medium break-words text-sm md:text-base ${isCancelled ? 'text-gray-500' : 'text-gray-200'}`}>
                        {productName}
                    </h4>
                    <p className="text-xs text-gray-500 mt-0.5">
                        {new Date(order.created_at).toLocaleDateString()} • {order.items.length} {order.items.length === 1 ? 'Item' : 'Items'}
                    </p>
                </div>
            </div>

            <div className="text-right flex flex-col items-end gap-1.5 shrink-0 ml-4">
                <span className={`text-[11px] font-semibold uppercase tracking-wider px-2.5 py-1 rounded-md border ${statusStyle}`}>
                    {order.status}
                </span>
                <p className={`text-sm font-semibold ${isCancelled ? 'text-gray-600' : 'text-gray-300'}`}>
                    ${order.total_price.toFixed(2)}
                </p>
            </div>
        </div>
    );
});
OrderCard.displayName = "OrderCard";

const SettingMenuButton = ({ icon, title, onClick }: { icon: React.ReactNode, title: string, onClick: () => void }) => (
    <button onClick={onClick} className="w-full flex items-center justify-between p-3.5 rounded-xl hover:bg-white/[0.05] transition-colors text-left group">
        <div className="flex items-center gap-3">
            <div className="text-gray-400 group-hover:text-white transition-colors">{icon}</div>
            <span className="text-sm font-medium text-gray-300 group-hover:text-white transition-colors">{title}</span>
        </div>
        <ChevronRight className="w-4 h-4 text-gray-600 group-hover:text-gray-400 transition-colors" />
    </button>
);
