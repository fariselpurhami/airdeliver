'use client';

import React, { useMemo, useRef, useEffect, useState, Suspense } from 'react';
import { useSession, signOut } from "next-auth/react";
import { motion, useMotionValue, useSpring, useInView, AnimatePresence } from "framer-motion";
import Image from 'next/image';
import useSWR, { mutate } from 'swr';
import { api } from '@/lib/api'; 
import { redirect } from 'next/navigation';
import { toast } from 'sonner'; 
import {
    User, Mail, MapPin, Phone, Clock, Loader2, LogOut, AlertCircle,
    CreditCard, Package, ShieldCheck, Edit3, KeyRound, Settings, Camera, ChevronRight
} from 'lucide-react';
import ChangePasswordModal from '@/components/profile/ChangePasswordModal';
import ViewOrdersModal from '@/components/profile/ViewOrdersModal';
import EditProfileDetailsModal from '@/components/profile/EditProfileDetailsModal';
import dynamic from 'next/dynamic';
import { Canvas, useFrame } from '@react-three/fiber';
import { Stars } from '@react-three/drei';
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
// --- 1. (New) Profile Background Component ---
// ============================================================================
const ProfileBackground = () => {
    const light1Ref = useRef<THREE.PointLight>(null!);
    const light2Ref = useRef<THREE.PointLight>(null!);

    useFrame((state) => {
        const time = state.clock.elapsedTime;
        if (light1Ref.current) {
            light1Ref.current.position.x = Math.sin(time * 0.5) * 15;
            light1Ref.current.position.y = Math.cos(time * 0.5) * 15;
            light1Ref.current.position.z = Math.cos(time * 0.5) * 10;
        }
        if (light2Ref.current) {
            light2Ref.current.position.x = Math.sin(time * 0.3) * -15;
            light2Ref.current.position.y = Math.cos(time * 0.3) * -15;
            light2Ref.current.position.z = Math.sin(time * 0.3) * 5;
        }
    });

    return (
        <>
            <fog attach="fog" args={['#000000', 10, 30]} />
            <ambientLight intensity={1.0} />
            <pointLight ref={light1Ref} position={[10, 10, 10]} intensity={200} color="#00C6FF" />
            <pointLight ref={light2Ref} position={[-10, -10, 5]} intensity={150} color="#7F00FF" />
            <Stars radius={100} depth={50} count={5000} factor={4} saturation={0} fade speed={1} />
        </>
    );
};

const DynamicProfileBackground = dynamic(() => Promise.resolve(ProfileBackground), { 
    ssr: false,
    loading: () => null
});

// ============================================================================
// --- 2. (Main Page Component) ---
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


    const handleOpenEditDetailsModal = () => setIsEditDetailsModalOpen(true);
    const handleCloseEditDetailsModal = () => setIsEditDetailsModalOpen(false);
    const handleOpenPasswordModal = () => setIsPasswordModalOpen(true);
    const handleClosePasswordModal = () => setIsPasswordModalOpen(false);
    const handleOpenOrdersModal = () => setIsOrdersModalOpen(true);
    const handleCloseOrdersModal = () => setIsOrdersModalOpen(false);

    const handleProfileDetailsSave = async (updatedData: Partial<UserProfileData>) => {
        if (!session?.accessToken) {
            toast.error("Authentication error. Please log in again.");
            return;
        }
        toast.promise(
            (async () => {
                const response = await api.put<UserProfileData>(profileApiUrl, updatedData);
                const updatedUser = response.data;
                mutateProfile(updatedUser, false);
                if (updatedData.full_name && session?.user) {
                    await updateSession({ user: { ...session.user, name: updatedData.full_name } });
                }
                handleCloseEditDetailsModal();
                return updatedUser;
            })(),
            {
                loading: 'Saving profile details...',
                success: 'Profile updated successfully!',
                error: (err: any) => `Save failed: ${err.response?.data?.detail || err.message || 'Unknown error'}`,
            }
        );
    };

    const handlePasswordSave = async (currentPassword: string, newPassword: string) => {
        if (!session?.accessToken) {
            toast.error("Authentication error. Please log in again.");
            return;
        }
        toast.promise(
             (async () => {
                await api.post('/users/me/change-password', { 
                     current_password: currentPassword,
                     new_password: newPassword
                 });
                handleClosePasswordModal();
             })(),
            {
                loading: 'Changing password...',
                success: 'Password changed successfully!',
                error: (err: any) => `Failed: ${err.response?.data?.detail || err.message || 'Unknown error'}`,
            }
        );
    };

    const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file || !session?.accessToken) {
            if (!session?.accessToken) toast.error("Authentication error.");
             return;
        }
        const formData = new FormData();
        formData.append('file', file);
        toast.promise(
            (async () => {
                 const response = await api.post<UserProfileData>('/users/me/avatar', formData, { 
                     headers: { 'Content-Type': 'multipart/form-data' }
                 });
                 const updatedUser = response.data;
                 mutateProfile(updatedUser, false);
                 if (updatedUser.avatar_url && session?.user && session.user.image !== updatedUser.avatar_url) {
                    await updateSession({ user: { ...session.user, image: updatedUser.avatar_url } });
                 }
                 return updatedUser;
            })(),
            {
                loading: 'Uploading avatar...',
                success: 'Avatar updated successfully!',
                error: (err: any) => `Upload failed: ${err.response?.data?.detail || err.message || 'Unknown error'}`,
                finally: () => { if (fileInputRef.current) fileInputRef.current.value = ''; }
            }
        );
    };

    const containerVariants = {
        hidden: { opacity: 0 },
        visible: { opacity: 1, transition: { staggerChildren: 0.08 } }
    };

    const isLoading = !isClient || sessionStatus === 'loading' ||
                      (sessionStatus === 'authenticated' && (isLoadingUser || isLoadingPayment)); 

    if (isLoading) return <LoadingSpinner />;
    if (isClient && sessionStatus === 'unauthenticated') redirect('/login');

    if (isClient && userError) {
        return (
            <div className="min-h-screen bg-black text-white flex flex-col items-center justify-center p-4">
                 <AlertCircle className="h-10 w-10 text-red-500 mb-3"/>
                <h2 className="text-xl font-bold text-red-500 mb-2">Error Loading Profile</h2>
                <p className='text-red-400 text-sm bg-red-900/50 p-3 rounded-md border border-red-800'>
                  
                    {(userError as any)?.message || 'Could not fetch profile data.'}
                </p>
            </div>
        );
    }

    const profileData = userData!; 
    const userImage = profileData?.avatar_url || session?.user?.image || `https://ui-avatars.com/api/?name=${encodeURIComponent(profileData?.full_name || session?.user?.email || 'A')}&background=0a0f28&color=06b6d4&bold=true&size=128`;
    if (profileData?.avatar_url) {
      console.log("Attempting to load image:", userImage);
    }
    const subtext = [joinedDate ? `Member since ${joinedDate}` : null, location]
        .filter(Boolean).join(' | ');
    const recentOrders = ordersData?.orders || [];
    const handleAvatarUpload = () => fileInputRef.current?.click();

    return (
        <>
            <input
                type="file" ref={fileInputRef} onChange={handleFileChange}
                accept="image/*" style={{ display: 'none' }}
            />

            <main
                className="relative min-h-screen w-full bg-black text-gray-200 py-24 md:py-32 px-4 overflow-hidden"
                style={{ fontFamily: "'Inter', sans-serif" }}
            >
                {/* --- New 3D Background --- */}
                <div className="fixed inset-0 z-0 opacity-70">
                    <Canvas>
                        <Suspense fallback={null}>
                            <DynamicProfileBackground />
                        </Suspense>
                    </Canvas>
                </div>

                <motion.div variants={containerVariants} initial="hidden" animate="visible" className="relative z-10 w-full max-w-4xl mx-auto space-y-12">

                    
                    <motion.div variants={{ hidden: { opacity: 0, y: -20 }, visible: { opacity: 1, y: 0 } }} transition={{ duration: 0.4, ease: 'easeOut' }} className="flex flex-col items-center text-center">
                        <div className="relative group mb-5">
                            <motion.div 
                                className="absolute -inset-1.5 rounded-full bg-cyan-400 blur-xl"
                                animate={{ 
                                    opacity: [0.6, 1, 0.6],
                                    scale: [1, 1.05, 1]
                                }}
                                transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
                            />
                            <div className="relative z-10 rounded-full p-1 bg-gradient-to-tr from-cyan-900/60 via-black/30 to-cyan-900/60">
                                <Image
                                    src={userImage} alt={profileData?.full_name || 'User Avatar'}
                                    width={128} height={128} className="rounded-full border-2 border-black/50"
                                    unoptimized={true}
                                    onError={(e) => { e.currentTarget.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(profileData?.full_name || session?.user?.email || 'E')}&background=ff0000&color=ffffff&bold=true&size=128`; }} 
                                />
                            </div>
                             <button className="absolute inset-0 flex items-center justify-center bg-black/70 rounded-full opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer z-20" onClick={handleAvatarUpload}>
                                <Camera size={32} className="text-cyan-400" />
                            </button>
                        </div>
                        <h1 className="text-4xl md:text-5xl font-black text-white" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                             <motion.span
                                className="text-transparent bg-clip-text bg-gradient-to-br from-cyan-400 to-purple-600"
                                animate={{
                                filter: [
                                    'drop-shadow(0 0 4px rgba(0, 198, 255, 0.4)) drop-shadow(0 0 4px rgba(168, 85, 247, 0.4))',
                                    'drop-shadow(0 0 16px rgba(0, 198, 255, 0.8)) drop-shadow(0 0 16px rgba(168, 85, 247, 0.8))',
                                    'drop-shadow(0 0 4px rgba(0, 198, 255, 0.4)) drop-shadow(0 0 4px rgba(168, 85, 247, 0.4))'
                                ]
                                }}
                                transition={{
                                duration: 3,
                                repeat: Infinity,
                                ease: "easeInOut"
                                }}
                            >
                                {profileData?.full_name || session?.user?.email?.split('@')[0]}
                            </motion.span>
                        </h1>
                        {subtext && (<p className="mt-2 text-base text-gray-400">{subtext}</p>)}
                         {profileData?.role && (
                             <span className="mt-3 inline-flex items-center gap-1.5 rounded-full bg-gradient-to-r from-cyan-600 to-blue-600 px-3 py-1 text-xs font-semibold text-white shadow-md shadow-cyan-500/20">
                                <ShieldCheck size={14} />
                                {profileData.role.charAt(0).toUpperCase() + profileData.role.slice(1)}
                            </span>
                        )}
                    </motion.div>

                
                    <motion.div variants={{ hidden: { opacity: 0, scale: 0.95 }, visible: { opacity: 1, scale: 1 } }} transition={{ duration: 0.4, ease: 'easeOut' }} className="bg-black/30 backdrop-blur-lg border border-cyan-400/30 rounded-2xl shadow-xl shadow-cyan-500/10 p-6 md:p-8">
                        <h2 className="text-xl font-semibold text-cyan-400 mb-6 pb-4 border-b border-white/10" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                            Account Information
                        </h2>
                        <motion.div variants={containerVariants} className="grid grid-cols-1 md:grid-cols-2 gap-x-12 gap-y-6 relative">
                            <div className="absolute left-1/2 top-0 bottom-0 w-px bg-white/5 hidden md:block -ml-6"></div>
                            <InfoItem icon={<User size={18} />} label="Full Name" value={profileData?.full_name} />
                            <InfoItem icon={<Mail size={18} />} label="Email Address" value={profileData?.email} />
                            <InfoItem icon={<Phone size={18} />} label="Phone Number" value={profileData?.phone_number} />
                            <InfoItem icon={<MapPin size={18} />} label="Primary Address" value={profileData?.address} />
                            <InfoItem icon={<MapPin size={18} />} label="Country / City" value={location} />
                            <InfoItem icon={<Clock size={18} />} label="Joined Date" value={joinedDate} />
                        </motion.div>
                    </motion.div>

           
                    <motion.div variants={{ hidden: { opacity: 0, scale: 0.95 }, visible: { opacity: 1, scale: 1 } }} transition={{ duration: 0.4, ease: 'easeOut' }} className="bg-black/30 backdrop-blur-lg border border-cyan-400/30 rounded-2xl shadow-xl shadow-cyan-500/10 p-6 md:p-8">
                         <h2 className="text-xl font-semibold text-cyan-400 mb-6 pb-4 border-b border-white/10" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                            Settings
                        </h2>
                         <motion.div variants={containerVariants} className="space-y-3">
                            <SettingsButton icon={<Edit3 size={20} />} label="Edit Profile Details" onClick={handleOpenEditDetailsModal} />
                            <SettingsButton icon={<KeyRound size={20} />} label="Change Password" onClick={handleOpenPasswordModal} />
                         </motion.div>
                    </motion.div>

               
                    <motion.div variants={{ hidden: { opacity: 0, scale: 0.95 }, visible: { opacity: 1, scale: 1 } }} transition={{ duration: 0.4, ease: 'easeOut' }} className="bg-black/30 backdrop-blur-lg border border-cyan-400/30 rounded-2xl shadow-xl shadow-cyan-500/10 p-6 md:p-8">
                        <div className="mb-5 flex justify-between items-center">
                            <h2 className="text-xl font-semibold text-cyan-400 inline-block" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                                Your Recent Orders
                            </h2>
                            <span className="block h-0.5 w-16 bg-cyan-400/50 mt-2 shadow-[0_0_10px_theme(colors.cyan.400)]" />
                        </div>
                        {isLoadingOrders && !ordersData && (
                            <div className="flex justify-center items-center h-32"> <Loader2 className="h-6 w-6 animate-spin text-cyan-400" /> </div>
                        )}
                        {ordersError && (
                            <p className="text-center text-red-400 italic py-8"> Error loading recent orders.</p>
                        )}
                        {!isLoadingOrders && recentOrders.length > 0 && (
                            <motion.div variants={containerVariants} className="flex gap-4 overflow-x-auto pb-4 -mx-2 px-2">
                                {recentOrders.map(order => (<OrderCard key={order.id} order={order} />))}
                            </motion.div>
                        )}
                        {!isLoadingOrders && recentOrders.length === 0 && (
                             <motion.p variants={{ hidden: { opacity: 0 }, visible: { opacity: 1 } }} className="text-center text-gray-500 italic py-8"> No recent orders found. </motion.p>
                        )}
                    </motion.div>

                    <motion.div variants={{ hidden: { opacity: 0, scale: 0.95 }, visible: { opacity: 1, scale: 1 } }} transition={{ duration: 0.4, ease: 'easeOut' }}>
                        <motion.div variants={containerVariants} className="grid grid-cols-1 md:grid-cols-2 gap-6">
                           
                            <motion.div variants={{ hidden: { opacity: 0, x: -20 }, visible: { opacity: 1, x: 0 } }} className="bg-black/30 backdrop-blur-lg border border-cyan-400/30 rounded-2xl p-6 flex items-start gap-4">
                                <CreditCard size={20} className="text-cyan-400/80 mt-1 flex-shrink-0" />
                                <div>
                                    <h3 className="text-base font-semibold text-white mb-1">Default Payment</h3>
                       
                                    {isLoadingPayment ? (
                                        <p className="text-sm text-gray-500 italic">Loading...</p>
                                    ) : paymentError ? (
                                        <p className="text-sm text-red-400 italic">Could not load</p>
                                    ) : paymentData?.brand && paymentData?.last4 ? (
                                        <p className="text-sm text-gray-300 capitalize">
                                            {paymentData.brand} ending in {paymentData.last4}
                                        </p>
                                    ) : (
                                         <p className="text-sm text-gray-500 italic">No default method set</p>
                                    )}
                                
                                </div>
                            </motion.div>
                            <motion.div variants={{ hidden: { opacity: 0, x: 20 }, visible: { opacity: 1, x: 0 } }} className="bg-black/30 backdrop-blur-lg border border-cyan-400/30 rounded-2xl p-6 flex items-start gap-4">
                                <MapPin size={20} className="text-cyan-400/80 mt-1 flex-shrink-0" />
                                <div>
                                    <h3 className="text-base font-semibold text-white mb-1">Default Shipping</h3>
                                    <p className="text-sm text-gray-300 leading-snug">
                                        {realShippingInfo || <span className="text-gray-500 italic">No address set</span>}
                                    </p>
                                </div>
                            </motion.div>
                        </motion.div>
                    </motion.div>

                    <motion.div variants={{ hidden: { opacity: 0, y: 20 }, visible: { opacity: 1, y: 0 } }} transition={{ duration: 0.4, ease: 'easeOut' }} className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-8">
                        <motion.button
                            onClick={handleOpenOrdersModal}
                            className="w-full sm:w-auto px-10 py-3 text-sm font-semibold rounded-lg text-cyan-300 bg-cyan-900/30 border-2 border-cyan-400 transition-colors duration-300 hover:bg-cyan-800/40 hover:text-white block text-center"
                            whileHover={{ scale: 1.03, y: -2 }} whileTap={{ scale: 0.98 }}
                            animate={{ boxShadow: [ '0 0 0px theme(colors.cyan.500)', '0 0 20px theme(colors.cyan.500)', '0 0 0px theme(colors.cyan.500)' ] }}
                            transition={{ duration: 2.5, repeat: Infinity, ease: 'easeInOut' }}
                        > View All Orders </motion.button>
                        <motion.button
                            onClick={() => signOut({ callbackUrl: '/login' })}
                            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-10 py-3 text-sm font-medium rounded-lg text-red-400 bg-red-900/30 border border-red-500/50 transition-colors duration-300 hover:bg-red-800/40 hover:text-red-300"
                            whileHover={{ scale: 1.03, y: -2, boxShadow: '0 0 15px rgba(239, 68, 68, 0.3)' }}
                            whileTap={{ scale: 0.98 }}
                        > <LogOut size={16} /> Sign Out </motion.button>
                    </motion.div>

                </motion.div>
            </main>

             <EditProfileDetailsModal
                isOpen={isEditDetailsModalOpen}
                onClose={handleCloseEditDetailsModal}
                userData={profileData!}
                onSave={handleProfileDetailsSave}
            />
             <ChangePasswordModal
                isOpen={isPasswordModalOpen}
                onClose={handleClosePasswordModal}
                onSave={handlePasswordSave}
            />
             <ViewOrdersModal
                isOpen={isOrdersModalOpen}
                onClose={handleCloseOrdersModal}
            />
        </>
    );
}


const LoadingSpinner = () => (
    <div className="flex min-h-screen w-full items-center justify-center bg-black">
        <Loader2 className="h-12 w-12 animate-spin text-cyan-400" />
    </div>
);

const AnimatedCounter = ({ value }: { value: number }) => {
    const ref = useRef<HTMLSpanElement>(null);
    const motionValue = useMotionValue(0);
    const springValue = useSpring(motionValue, { damping: 50, stiffness: 100 });
    const isInView = useInView(ref, { once: true, margin: "0px 0px -50px 0px" });
    useEffect(() => { if (isInView) motionValue.set(value); }, [motionValue, isInView, value]);
    useEffect(() => {
        const unsubscribe = springValue.on("change", (latest) => {
            if (ref.current) ref.current.textContent = Intl.NumberFormat('en-US').format(Math.round(latest));
        }); return unsubscribe;
    }, [springValue]);
    return <span ref={ref}>{value}</span>;
};

const InfoItem = ({ icon, label, value }: {
    icon: React.ReactNode; label: string; value: string | undefined | null;
}) => (
    <motion.div
        variants={{ hidden: { opacity: 0, y: 10 }, visible: { opacity: 1, y: 0 } }}
        className="flex items-start gap-3 group py-3 border-b border-white/5"
    >
        <span className="text-cyan-400/80 mt-1 transition-colors group-hover:text-cyan-300">{icon}</span>
        <div>
            <p className="text-xs text-gray-400 mb-0.5 opacity-90">{label}</p>
            <p className="text-white font-medium text-base transition-colors group-hover:text-gray-200">
                {value || <span className="text-gray-500 italic flex items-center gap-1"><Settings size={12} className="opacity-50"/> Not set</span>}
            </p>
        </div>
    </motion.div>
);

const OrderCard = ({ order }: { order: OrderRead }) => {
    const statusColor = {
        Delivered: 'text-green-400 bg-green-900/50 border-green-700/50',
        Shipped: 'text-cyan-400 bg-cyan-900/50 border-cyan-700/50',
        Processing: 'text-yellow-400 bg-yellow-900/50 border-yellow-700/50',
    } as Record<string, string>;
    const defaultColor = 'text-gray-400 bg-gray-900/50 border-gray-700/50';
    const firstItem = order.items?.[0];
    const productName = firstItem?.product?.name || `Order #${order.id}`;
    const productImageUrl = firstItem?.product?.image_url || 'https://placehold.co/256x144/000000/FFF?text=Image';

    return (
        <motion.div
            variants={{ hidden: { opacity: 0, x: 20 }, visible: { opacity: 1, x: 0 } }}
            whileHover={{ y: -6, transition: { duration: 0.2, ease: 'easeOut' } }}
            className="w-64 flex-shrink-0 bg-black/30 backdrop-blur-lg border border-cyan-400/30 rounded-xl overflow-hidden shadow-lg shadow-cyan-500/10"
        >
            
             <div className="relative w-full h-36">
                <Image
                    src={productImageUrl} alt={productName} fill
                    className="object-cover"
                    sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw" 
                    unoptimized={productImageUrl.startsWith('https://placehold.co')} 
                    onError={(e) => { e.currentTarget.src = 'https://placehold.co/256x144/000000/FFF?text=Error'; }} 
                />
             </div>
            <div className="p-4 space-y-2">
                <h4 className="text-white font-semibold truncate">{productName}</h4>
                <p className="text-gray-300 font-mono text-sm">${order.total_price.toFixed(2)}</p>
                <span className={`text-xs font-semibold px-2 py-0.5 rounded-full border ${statusColor[order.status] || defaultColor}`}>
                    {order.status}
                </span>
            </div>
        </motion.div>
    );
};

const SettingsButton = ({ icon, label, onClick }: {
    icon: React.ReactNode; label: string; onClick: () => void;
}) => (
     <motion.button
        onClick={onClick}
        variants={{ hidden: { opacity: 0, scale: 0.9 }, visible: { opacity: 1, scale: 1 } }}
        whileHover={{ scale: 1.02, x: 2, boxShadow: '0 0 15px rgba(6, 182, 212, 0.3)' }}
        whileTap={{ scale: 0.98 }}
        className="flex w-full items-center justify-between gap-4 rounded-lg bg-white/5 p-4 border border-white/10 transition-all duration-200 group hover:border-cyan-700/50 hover:bg-gradient-to-r hover:from-cyan-900/30 hover:to-transparent"
    >
        <div className="flex items-center gap-4">
            <span className="text-cyan-400">{icon}</span>
            <span className="text-white font-medium">{label}</span>
        </div>
        <ChevronRight size={16} className="text-gray-600 group-hover:text-cyan-400 transition-colors" />
    </motion.button>
);
