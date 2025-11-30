//** apps/web/app/(main)/profile/page.tsx **//

'use client';

import React, { useMemo, useRef, useEffect, useState, Suspense } from 'react';
import { useSession, signOut } from "next-auth/react";
import { motion, AnimatePresence } from "framer-motion";
import Image from 'next/image';
import useSWR, { mutate } from 'swr';
import { api } from '@/lib/api'; 
import { redirect } from 'next/navigation';
import { toast } from 'sonner'; 
import {
    User, Mail, MapPin, Phone, Clock, Loader2, LogOut, AlertCircle,
    CreditCard, Package, ShieldCheck, Edit3, KeyRound, Settings, Camera, ChevronRight, Zap
} from 'lucide-react';
import ChangePasswordModal from '@/components/profile/ChangePasswordModal';
import ViewOrdersModal from '@/components/profile/ViewOrdersModal';
import EditProfileDetailsModal from '@/components/profile/EditProfileDetailsModal';
import dynamic from 'next/dynamic';
import { Canvas, useFrame } from '@react-three/fiber';
import { Stars, Float } from '@react-three/drei';
import * as THREE from 'three';

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
// --- 1. ARCHITECTURAL BACKGROUND (The Deep Void) ---
// ============================================================================
const ProfileBackground = () => {
    const lightRef = useRef<THREE.PointLight>(null!);

    useFrame(({ clock }) => {
        if (lightRef.current) {
            lightRef.current.position.x = Math.sin(clock.elapsedTime * 0.5) * 10;
            lightRef.current.position.z = Math.cos(clock.elapsedTime * 0.5) * 10;
        }
    });

    return (
        <>
            <fog attach="fog" args={['#000000', 5, 30]} />
            <ambientLight intensity={0.2} />
            <pointLight ref={lightRef} position={[10, 10, 10]} intensity={1.5} color="#00C6FF" />
            <Stars radius={80} depth={40} count={3000} factor={4} saturation={0} fade speed={0.5} />
            <Float speed={2} rotationIntensity={0.5} floatIntensity={0.5}>
            </Float>
        </>
    );
};

const DynamicProfileBackground = dynamic(() => Promise.resolve(ProfileBackground), { 
    ssr: false,
    loading: () => null
});

// ============================================================================
// --- 2. MAIN PROFILE COMPONENT (Command Center) ---
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
    const { data: ordersData, error: ordersError, isLoading: isLoadingOrders } = useSWR<PaginatedOrdersResponse>(
        sessionStatus === 'authenticated' ? ordersApiUrl : null, swrFetcher, { revalidateOnFocus: false }
    );
    const { data: paymentData, error: paymentError, isLoading: isLoadingPayment } = useSWR<DefaultPaymentData>(
        sessionStatus === 'authenticated' ? paymentApiUrl : null, swrFetcher, { revalidateOnFocus: false }
    );

    const [isClient, setIsClient] = useState(false);
    const [isEditDetailsModalOpen, setIsEditDetailsModalOpen] = useState(false);
    const [isPasswordModalOpen, setIsPasswordModalOpen] = useState(false);
    const [isOrdersModalOpen, setIsOrdersModalOpen] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    useEffect(() => { setIsClient(true); }, []);

    const joinedDate = useMemo(() => (
        userData?.created_at
            ? new Date(userData.created_at).toLocaleDateString('en-US', { year: 'numeric', month: 'long' })
            : null
    ), [userData?.created_at]);

    const location = useMemo(() => (
        [userData?.city, userData?.country].filter(Boolean).join(', ') || null
    ), [userData?.city, userData?.country]);

    const realShippingInfo = useMemo(() => (
        [userData?.address, userData?.city, userData?.country].filter(Boolean).join(', ') || null
    ), [userData?.address, userData?.city, userData?.country]);

    const recentOrders = useMemo(() => {
        if (!ordersData?.orders) return [];
        return ordersData.orders;
    }, [ordersData]);

    const handleOpenEditDetailsModal = () => setIsEditDetailsModalOpen(true);
    const handleCloseEditDetailsModal = () => setIsEditDetailsModalOpen(false);
    const handleOpenPasswordModal = () => setIsPasswordModalOpen(true);
    const handleClosePasswordModal = () => setIsPasswordModalOpen(false);
    const handleOpenOrdersModal = () => setIsOrdersModalOpen(true);
    const handleCloseOrdersModal = () => setIsOrdersModalOpen(false);

    const handleProfileDetailsSave = async (updatedData: Partial<UserProfileData>) => {
        if (!session?.accessToken) { toast.error("Authentication error."); return; }
        toast.promise((async () => {
                const response = await api.put<UserProfileData>(profileApiUrl, updatedData);
                const updatedUser = response.data;
                mutateProfile(updatedUser, false);
                if (updatedData.full_name && session?.user) {
                    await updateSession({ user: { ...session.user, name: updatedData.full_name } });
                }
                handleCloseEditDetailsModal();
                return updatedUser;
            })(), { loading: 'Updating system records...', success: 'Profile synchronized!', error: 'Update failed.' }
        );
    };

    const handlePasswordSave = async (currentPassword: string, newPassword: string) => {
        if (!session?.accessToken) { toast.error("Authentication error."); return; }
        toast.promise((async () => {
                await api.post('/users/me/change-password', { current_password: currentPassword, new_password: newPassword });
                handleClosePasswordModal();
             })(), { loading: 'Encrypting new credentials...', success: 'Security updated!', error: 'Failed to update password.' }
        );
    };

    const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file || !session?.accessToken) return;
        const formData = new FormData();
        formData.append('file', file);
        toast.promise((async () => {
                 const response = await api.post<UserProfileData>('/users/me/avatar', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
                 const updatedUser = response.data;
                 mutateProfile(updatedUser, false);
                 if (updatedUser.avatar_url && session?.user) await updateSession({ user: { ...session.user, image: updatedUser.avatar_url } });
                 return updatedUser;
            })(), { loading: 'Uploading bio-metric data...', success: 'Avatar updated!', error: 'Upload failed.' }
        );
    };

    const isLoading = !isClient || sessionStatus === 'loading' || (sessionStatus === 'authenticated' && (isLoadingUser || isLoadingPayment)); 

    if (isLoading) return <LoadingSpinner />;
    if (isClient && sessionStatus === 'unauthenticated') redirect('/login');
    if (isClient && userError) return <ErrorDisplay message={(userError as any)?.message} />;

    const profileData = userData!; 
    const userImage = profileData?.avatar_url || session?.user?.image || `https://ui-avatars.com/api/?name=${encodeURIComponent(profileData?.full_name || session?.user?.email || 'A')}&background=0a0f28&color=06b6d4&bold=true&size=128`;
    const subtext = [joinedDate ? `Operative since ${joinedDate}` : null, location].filter(Boolean).join(' | ');
    const handleAvatarUpload = () => fileInputRef.current?.click();

    return (
        <>
            <input type="file" ref={fileInputRef} onChange={handleFileChange} accept="image/*" style={{ display: 'none' }} />

            <main className="relative min-h-screen w-full bg-black text-gray-200 py-28 px-4 overflow-hidden font-sans selection:bg-cyan-500/30">
                <div className="fixed inset-0 z-0 opacity-60">
                    <Canvas camera={{ position: [0, 0, 10], fov: 45 }}>
                        <Suspense fallback={null}>
                            <DynamicProfileBackground />
                        </Suspense>
                    </Canvas>
                    <div className="absolute inset-0 bg-gradient-to-b from-black via-transparent to-black pointer-events-none" />
                </div>

                <motion.div 
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6, ease: "easeOut" }}
                    className="relative z-10 w-full max-w-5xl mx-auto space-y-8"
                >
                    <div className="flex flex-col md:flex-row items-center gap-8 md:gap-12 pb-8 border-b border-white/5">
                        <div className="relative group">
                            <motion.div 
                                className="absolute -inset-1 rounded-full bg-gradient-to-br from-cyan-500/50 to-purple-600/50 blur-lg"
                                animate={{ opacity: [0.5, 0.8, 0.5], scale: [1, 1.02, 1] }}
                                transition={{ duration: 4, repeat: Infinity }}
                            />
                            <div className="relative h-32 w-32 md:h-40 md:w-40 rounded-full p-[2px] bg-gradient-to-br from-white/20 to-white/0 overflow-hidden">
                                <Image
                                    src={userImage} alt={profileData?.full_name || 'User'}
                                    fill className="rounded-full object-cover"
                                    unoptimized={true}
                                    onError={(e) => { e.currentTarget.src = `https://ui-avatars.com/api/?name=${encodeURIComponent('User')}&background=333&color=fff`; }}
                                />
                                <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center cursor-pointer" onClick={handleAvatarUpload}>
                                    <Camera className="text-white h-8 w-8" />
                                </div>
                            </div>
                        </div>
                        
                        <div className="flex-1 text-center md:text-left space-y-2">
                            <div className="flex flex-col md:flex-row items-center gap-4 justify-center md:justify-start">
                                <h1 className="text-4xl md:text-5xl font-bold text-white tracking-tight" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                                    {profileData?.full_name || 'Anonymous Operative'}
                                </h1>
                                {profileData?.role && (
                                    <span className="px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 text-xs font-mono uppercase tracking-wider">
                                        {profileData.role}
                                    </span>
                                )}
                            </div>
                            <p className="text-gray-400 font-light">{subtext}</p>
                            <div className="flex items-center justify-center md:justify-start gap-6 pt-2">
                                <StatBadge label="Orders" value={profileData?.orders_completed || 0} />
                                <StatBadge label="Favorites" value={profileData?.items_favorited || 0} />
                            </div>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                        <div className="lg:col-span-2 space-y-8">
                            
                            <SectionContainer title="Personal Information" icon={<User className="text-cyan-400" />}>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                    <InfoField label="Full Identity" value={profileData?.full_name} />
                                    <InfoField label="Contact Email" value={profileData?.email} />
                                    <InfoField label="Comms Link" value={profileData?.phone_number} />
                                    <InfoField label="Base Location" value={location} />
                                </div>
                            </SectionContainer>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <StatusCard 
                                    icon={<CreditCard className="text-purple-400" />}
                                    title="Default Payment"
                                    status={paymentData?.brand ? 'Active' : 'Not Set'}
                                    detail={paymentData?.brand ? `**** ${paymentData.last4}` : 'Configure method'}
                                />
                                <StatusCard 
                                    icon={<MapPin className="text-cyan-400" />}
                                    title="Primary Shipping"
                                    status={realShippingInfo ? 'Verified' : 'Pending'}
                                    detail={realShippingInfo || 'Add shipping address'}
                                />
                            </div>

                            <SectionContainer title="Recent Orders" icon={<Package className="text-cyan-400" />}>
                                {isLoadingOrders ? (
                                    <div className="py-8 flex justify-center"><Loader2 className="animate-spin text-cyan-500" /></div>
                                ) : recentOrders.length > 0 ? (
                                    <div className="space-y-4">
                                        {recentOrders.map(order => <OrderRow key={order.id} order={order} />)}
                                    </div>
                                ) : (
                                    <div className="text-center py-8 text-gray-500 italic">No recent activity detected.</div>
                                )}
                                <div className="mt-6 pt-4 border-t border-white/5 flex justify-center">
                                    <button 
                                        onClick={handleOpenOrdersModal}
                                        className="text-sm text-cyan-400 hover:text-cyan-300 transition-colors flex items-center gap-2 group"
                                    >
                                        View all Orders <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                                    </button>
                                </div>
                            </SectionContainer>
                        </div>

                        <div className="lg:col-span-1 space-y-6">
                            <div className="bg-black/30 backdrop-blur-xl border border-white/10 rounded-[40px] p-6 space-y-4 sticky top-32">
                                <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                                    <Settings className="w-5 h-5 text-gray-400" /> System Control
                                </h3>
                                
                                <ControlAction 
                                    icon={<Edit3 size={18} />} 
                                    label="Update Profile" 
                                    desc="Modify personal data"
                                    onClick={handleOpenEditDetailsModal} 
                                />
                                <ControlAction 
                                    icon={<KeyRound size={18} />} 
                                    label="Update Password" 
                                    desc="Change your password"
                                    onClick={handleOpenPasswordModal} 
                                />
                                
                                <div className="h-px bg-white/10 my-4" />
                                
                                <button 
                                    onClick={() => signOut({ callbackUrl: '/login' })}
                                    className="w-full flex items-center justify-between p-4 rounded-2xl bg-red-500/10 border border-red-500/20 text-red-400 hover:bg-red-500/20 transition-all group"
                                >
                                    <span className="font-medium">Log Out</span>
                                    <LogOut size={18} className="group-hover:translate-x-1 transition-transform" />
                                </button>
                            </div>
                        </div>
                    </div>

                </motion.div>
            </main>

            <EditProfileDetailsModal isOpen={isEditDetailsModalOpen} onClose={handleCloseEditDetailsModal} userData={profileData!} onSave={handleProfileDetailsSave} />
            <ChangePasswordModal isOpen={isPasswordModalOpen} onClose={handleClosePasswordModal} onSave={handlePasswordSave} />
            <ViewOrdersModal isOpen={isOrdersModalOpen} onClose={handleCloseOrdersModal} />
        </>
    );
}

// ============================================================================
// --- 3. SUB-COMPONENTS (The Design System) ---
// ============================================================================

const LoadingSpinner = () => (
    <div className="flex min-h-screen w-full items-center justify-center bg-black">
        <Loader2 className="h-12 w-12 animate-spin text-cyan-400" />
    </div>
);

const ErrorDisplay = ({ message }: { message: string }) => (
    <div className="min-h-screen bg-black text-white flex flex-col items-center justify-center p-4">
        <AlertCircle className="h-12 w-12 text-red-500 mb-4"/>
        <h2 className="text-2xl font-bold text-white mb-2" style={{ fontFamily: "'Orbitron', sans-serif" }}>System Malfunction</h2>
        <p className='text-gray-400'>{message || 'Unknown error occurred.'}</p>
    </div>
);

const StatBadge = ({ label, value }: { label: string, value: number }) => (
    <div className="flex flex-col items-center md:items-start">
        <span className="text-2xl font-bold text-white tabular-nums">{value}</span>
        <span className="text-[10px] uppercase tracking-widest text-gray-500">{label}</span>
    </div>
);

const SectionContainer = ({ title, icon, children }: { title: string, icon: React.ReactNode, children: React.ReactNode }) => (
    <motion.div 
        initial={{ opacity: 0, y: 10 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        className="bg-black/30 backdrop-blur-xl border border-white/10 rounded-[40px] p-8 shadow-2xl shadow-black/50"
    >
        <div className="flex items-center gap-3 mb-6 pb-4 border-b border-white/5">
            <div className="p-2 rounded-full bg-white/5">{icon}</div>
            <h2 className="text-xl font-bold text-white" style={{ fontFamily: "'Orbitron', sans-serif" }}>{title}</h2>
        </div>
        {children}
    </motion.div>
);

const InfoField = ({ label, value }: { label: string, value?: string | null }) => (
    <div>
        <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">{label}</p>
        <p className="text-gray-200 font-medium truncate">{value || <span className="text-gray-600 italic">Not specified</span>}</p>
    </div>
);

const StatusCard = ({ icon, title, status, detail }: { icon: React.ReactNode, title: string, status: string, detail: string }) => (
    <div className="bg-black/40 border border-white/10 rounded-[30px] p-6 flex items-start gap-4 hover:border-cyan-500/30 transition-colors group">
        <div className="p-3 rounded-2xl bg-white/5 group-hover:bg-cyan-500/10 transition-colors">
            {icon}
        </div>
        <div>
            <h4 className="text-sm text-gray-400 font-medium mb-1">{title}</h4>
            <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${status === 'Active' || status === 'Verified' ? 'bg-green-500' : 'bg-yellow-500'}`} />
                <span className="text-white font-bold">{status}</span>
            </div>
            <p className="text-xs text-gray-500 mt-1 truncate max-w-[150px]">{detail}</p>
        </div>
    </div>
);

const OrderRow = ({ order }: { order: OrderRead }) => {
    const firstItem = order.items?.[0];
    const productName = firstItem?.product?.name || `Order #${order.id}`;
    const statusColor = order.status === 'Delivered' ? 'text-green-400 border-green-500/30' : 'text-cyan-400 border-cyan-500/30';

    return (
        <div className="flex items-center justify-between p-4 rounded-2xl bg-white/5 border border-white/5 hover:border-white/20 transition-all">
            <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-black/50 border border-white/10 flex items-center justify-center">
                    <Package className="text-gray-400 w-6 h-6" />
                </div>
                <div>
                    <h4 className="text-white font-medium">{productName}</h4>
                    <p className="text-xs text-gray-500">{new Date(order.created_at).toLocaleDateString()}</p>
                </div>
            </div>
            <div className="text-right">
                <span className={`text-xs font-bold px-2 py-1 rounded-full border bg-black/20 ${statusColor}`}>
                    {order.status}
                </span>
                <p className="text-sm text-gray-300 font-mono mt-1">${order.total_price.toFixed(2)}</p>
            </div>
        </div>
    );
};

const ControlAction = ({ icon, label, desc, onClick }: { icon: React.ReactNode, label: string, desc: string, onClick: () => void }) => (
    <button 
        onClick={onClick}
        className="w-full flex items-center gap-4 p-4 rounded-2xl hover:bg-white/5 border border-transparent hover:border-white/10 transition-all text-left group"
    >
        <div className="text-gray-400 group-hover:text-cyan-400 transition-colors">{icon}</div>
        <div className="flex-1">
            <h4 className="text-white font-medium">{label}</h4>
            <p className="text-xs text-gray-500">{desc}</p>
        </div>
        <ChevronRight className="w-4 h-4 text-gray-600 group-hover:text-white transition-colors" />
    </button>
);
