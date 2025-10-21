'use client';

import React, { useEffect } from 'react'; // <-- تم إضافة useEffect
import { useSession, signOut } from "next-auth/react";
import { useRouter } from 'next/navigation';
import { motion } from "framer-motion";
import { User, LogOut, Shield } from 'lucide-react';

// --- مكون لإظهار حالة التحميل ---
const LoadingSpinner = () => (
    <div className="flex justify-center items-center h-full">
        <div className="w-12 h-12 border-4 border-cyan-400 border-t-transparent rounded-full animate-spin" />
    </div>
);

// --- صفحة البروفايل الرئيسية ---
export default function ProfilePage() {
    const { data: session, status } = useSession();
    const router = useRouter();

    // --- هذا هو الكود الجديد للـ Redirect ---
    useEffect(() => {
        // إذا انتهى التحميل والمستخدم غير مسجل دخوله
        if (status === "unauthenticated") {
            // قم بإعادة التوجيه لصفحة تسجيل الدخول
            // مع إضافة ?callbackUrl=/profile عشان يرجع هنا بعد اللوجن
            router.push('/login?callbackUrl=/profile');
        }
    }, [status, router]); // يعتمد على status و router

    // حالة التحميل: جاري جلب بيانات المستخدم
    if (status === "loading" || status === "unauthenticated") {
        // نعرض التحميل طالما جاري التحقق أو جاري إعادة التوجيه
        return (
            <main className="min-h-screen w-full bg-black flex items-center justify-center">
                <LoadingSpinner />
            </main>
        );
    }

    // حالة تسجيل الدخول بنجاح: عرض بيانات المستخدم
    // (هذا الجزء لم يتغير)
    return (
        <main className="min-h-screen w-full bg-black text-white pt-32 px-4">
            <div className="container mx-auto max-w-2xl">
                <motion.div
                    initial={{ opacity: 0, y: 50 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8, ease: "easeOut" }}
                    className="bg-black/30 backdrop-blur-xl border border-white/10 rounded-2xl p-8"
                >
                    <div className="flex flex-col items-center text-center">
                        <div className="w-24 h-24 rounded-full bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center mb-6">
                            <User size={48} />
                        </div>

                        <h1 className="text-4xl font-bold" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                            {session?.user?.name || 'User Profile'}
                        </h1>
                        <p className="text-gray-400 mt-2">{session?.user?.email}</p>

                        {(session?.user as any)?.role === 'admin' && (
                             <div className="mt-4 flex items-center gap-2 text-sm bg-yellow-500/10 text-yellow-300 px-3 py-1 rounded-full">
                                <Shield size={14} />
                                <span>Administrator</span>
                            </div>
                        )}

                        <div className="w-full h-px bg-white/10 my-8" />

                        <motion.button
                            whileHover={{ scale: 1.05 }}
                            whileTap={{ scale: 0.95 }}
                            onClick={() => signOut({ callbackUrl: '/login' })}
                            className="flex items-center justify-center gap-2 bg-red-600/80 hover:bg-red-600 transition-colors px-8 py-3 rounded-full font-bold"
                        >
                            <LogOut size={18} />
                            Sign Out
                        </motion.button>
                    </div>
                </motion.div>
            </div>
        </main>
    );
}
