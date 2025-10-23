'use client';

import React, { useState } from 'react';
import { useSession, signOut } from "next-auth/react";
import { motion } from "framer-motion";
import Image from 'next/image';
import { 
    User, 
    Mail, 
    ShieldCheck, 
    MapPin, 
    Phone, 
    Edit3, 
    LogOut, 
    Camera, 
    Loader2 
} from 'lucide-react';
import useSWR from 'swr';
import { fetcher } from '@/lib/fetcher';

interface UserProfileData {
    id: number;
    email: string;
    full_name?: string | null;
    role?: string | null;
    phone_number?: string | null;
    address?: string | null;
    avatar_url?: string | null;
}

const LoadingSpinner = () => (
    <div className="flex min-h-screen w-full items-center justify-center bg-black">
        <Loader2 className="h-12 w-12 animate-spin text-cyan-400" />
    </div>
);

const ProfileField = ({ icon, label, value, onEdit }: { 
    icon: React.ReactNode; 
    label: string; 
    value: string | undefined | null; 
    onEdit?: () => void;
}) => (
    <motion.div 
        variants={{ hidden: { opacity: 0, x: -20 }, visible: { opacity: 1, x: 0 } }}
        className="flex items-center justify-between py-4 border-b border-white/10"
    >
        <div className="flex items-center gap-4">
            <span className="text-cyan-400">{icon}</span>
            <div>
                <p className="text-xs text-gray-400">{label}</p>
                <p className="text-white font-medium">{value || 'Not set'}</p>
            </div>
        </div>
        {onEdit && (
            <button onClick={onEdit} className="text-gray-500 hover:text-cyan-400 transition-colors">
                <Edit3 size={18} />
            </button>
        )}
    </motion.div>
);

export default function ProfilePage() {
    const { data: session, status: sessionStatus } = useSession(); 
    
    const { data: userData, error: userError, isLoading: isLoadingUser } = useSWR<UserProfileData>(
        sessionStatus === 'authenticated' ? '/api/v1/users/me' : null, 
        fetcher 
    );

    const [isEditing, setIsEditing] = useState<string | null>(null); 
    const handleEdit = (fieldName: string) => setIsEditing(fieldName);
    const containerVariants = {
        hidden: { opacity: 0 },
        visible: { 
            opacity: 1,
            transition: { staggerChildren: 0.1, delayChildren: 0.2 }
        }
    };

    if (sessionStatus === 'loading' || (sessionStatus === 'authenticated' && isLoadingUser)) {
        return <LoadingSpinner />;
    }

    if (sessionStatus === 'unauthenticated') {
        return <div className="min-h-screen bg-black text-white flex items-center justify-center">Please log in to view your profile.</div>;
    }

    if (userError) {
         return <div className="min-h-screen bg-black text-white flex flex-col items-center justify-center">
            <p className='text-red-500'>Error loading profile data:</p> 
            <p className='text-red-400 text-sm'>{userError.message}</p>
         </div>;
    }

    const user = session?.user;
    const profileData = userData;

    const userImage = profileData?.avatar_url || user?.image || `https://ui-avatars.com/api/?name=${encodeURIComponent(profileData?.full_name || user?.email || 'A')}&background=0D1117&color=00c6ff&bold=true`;

    return (
        <main className="relative min-h-screen w-full bg-black text-gray-100 py-16 overflow-hidden">
            <div className="absolute inset-0 bg-grid-white/[0.05] -z-10" />
            <motion.div 
                variants={containerVariants}
                initial="hidden"
                animate="visible"
                className="w-full max-w-4xl mx-auto px-4 md:px-8"
            >
                <motion.div 
                    variants={{ hidden: { opacity: 0, y: -30 }, visible: { opacity: 1, y: 0 } }}
                    className="flex flex-col md:flex-row items-center gap-6 md:gap-8 mb-12"
                >
                    <div className="relative group">
                        <Image 
                            src={userImage} 
                            alt={profileData?.full_name || 'User Avatar'} 
                            width={120} 
                            height={120} 
                            className="rounded-full border-4 border-white/10 shadow-lg"
                            priority
                        />
                        <button 
                            className="absolute inset-0 flex items-center justify-center bg-black/70 rounded-full opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer"
                            onClick={() => alert('Avatar upload functionality to be implemented!')}
                        >
                            <Camera size={32} className="text-cyan-400" />
                        </button>
                    </div>
                    
                    <div className="text-center md:text-left">
                        <h1 
                            className="text-4xl font-black text-white" 
                            style={{ fontFamily: "'Orbitron', sans-serif" }}
                        >
                            {profileData?.full_name || user?.email?.split('@')[0]}
                        </h1>
                        <p className="text-gray-400 mt-1">{profileData?.email}</p>
                        {profileData?.role && (
                            <span className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-yellow-500/10 px-3 py-1 text-xs font-medium text-yellow-300 border border-yellow-500/30">
                                <ShieldCheck size={14} />
                                {profileData.role.charAt(0).toUpperCase() + profileData.role.slice(1)}
                            </span>
                        )}
                    </div>
                    <motion.button 
                        onClick={() => signOut({ callbackUrl: '/' })} 
                        whileHover={{ scale: 1.05 }} 
                        whileTap={{ scale: 0.95 }}
                        className="ml-auto flex items-center gap-2 rounded-lg bg-red-600/20 px-4 py-2 text-sm font-medium text-red-400 border border-red-600/50 hover:bg-red-600/30 transition-colors"
                    >
                        <LogOut size={16} />
                        Sign Out
                    </motion.button>
                </motion.div>

                <motion.div 
                    variants={{ hidden: { opacity: 0, scale: 0.95 }, visible: { opacity: 1, scale: 1 } }}
                    className="bg-black/30 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl shadow-black/50 p-6 md:p-8"
                >
                    <h2 
                        className="text-2xl font-bold text-white mb-6 pb-4 border-b border-white/10" 
                        style={{ fontFamily: "'Orbitron', sans-serif" }}
                    >
                        Account Details
                    </h2>
                    <motion.div variants={containerVariants}>
                        <ProfileField icon={<User size={20} />} label="Full Name" value={profileData?.full_name} onEdit={() => handleEdit('name')} />
                        <ProfileField icon={<Mail size={20} />} label="Email Address" value={profileData?.email} /> 
                        <ProfileField 
                            icon={<Phone size={20} />} 
                            label="Phone Number" 
                            value={profileData?.phone_number} 
                            onEdit={() => handleEdit('phone')} 
                        />
                        <ProfileField 
                            icon={<MapPin size={20} />} 
                            label="Primary Address" 
                            value={profileData?.address} 
                            onEdit={() => handleEdit('address')} 
                        />
                    </motion.div>
                </motion.div>
            </motion.div>
        </main>
    );
}
