'use client';

import React, { useState, useEffect, Suspense, useRef, useMemo } from 'react'; // <-- تم إضافة useMemo
import { motion, AnimatePresence } from 'framer-motion';
import { Canvas, useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import ProductList from '@/components/products/ProductList';
import { type Product } from '@/types';
import { useSession } from 'next-auth/react';
import useSWR from 'swr';
import { api } from '@/lib/api';
import { AlertTriangle } from 'lucide-react';

// --- دالة الجلب لـ SWR ---
const fetcher = (url: string) => api.get(url).then(res => res.data);

// --- مكونات الهياكل العظمية (Skeletons) ---
const BannerSkeleton = () => (
    <div className="animate-pulse">
        <div className="h-16 md:h-24 bg-gray-700/50 rounded w-3/4 mx-auto mb-4"></div>
        <div className="h-6 bg-gray-600/50 rounded w-1/2 mx-auto"></div>
    </div>
);

const ProductCardSkeleton = () => (
    <div className="relative animate-pulse w-full rounded-2xl bg-black/40 backdrop-blur-xl border border-white/10 p-6 flex flex-col justify-between aspect-[3/4]">
        <div className="h-32 bg-gray-700/50 rounded mb-4"></div>
        <div className="space-y-3">
            <div className="h-4 bg-gray-600/50 rounded w-3/4"></div>
            <div className="h-6 bg-gray-500/50 rounded w-1/2"></div>
            <div className="h-3 bg-gray-700/50 rounded w-full"></div>
        </div>
    </div>
);

const ProductListSkeleton = () => (
    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
        {[...Array(8)].map((_, i) => <ProductCardSkeleton key={i} />)}
    </div>
);

// --- مكون التوصيات الشخصية (يستخدم SWR الآن) ---
const PersonalizedRecommendations = () => {
    const { data: session, status } = useSession();
    const userId = (session?.user as any)?.id;

    const apiUrl = status === 'authenticated' && userId
        ? `/products/suggestions?product_id=1&user_id=${userId}`
        : null;

    const { data: recommendationsData, error, isLoading } = useSWR<Product[]>(apiUrl, fetcher, {
        revalidateOnFocus: false,
        shouldRetryOnError: false
    });

    const recommendations = useMemo(() => {
        if (!recommendationsData) return [];
        const items = Array.isArray(recommendationsData) ? recommendationsData : (recommendationsData as any).items || [];
        return items.map((p: any) => ({ ...p, isAIRec: true }));
    }, [recommendationsData]);

    if (isLoading || error || recommendations.length === 0 || status !== 'authenticated') {
        return null;
    }

    return (
        <section className="mb-24">
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }}>
                <h2 className="text-2xl font-bold mb-8 text-center" style={{ fontFamily: "'Orbitron', sans-serif" }}>Based on Your Activity, You Might Like...</h2>
                <ProductList products={recommendations} />
            </motion.div>
        </section>
    );
};

// --- مكون عرض الخطأ ---
const ErrorDisplay = ({ error }: { error: any }) => (
    <div className="flex flex-col items-center justify-center text-center text-red-400 my-16 p-6 border border-red-500/30 bg-red-500/10 rounded-lg">
        <AlertTriangle className="w-12 h-12 mb-4" />
        <h3 className="text-xl font-bold mb-2">Failed to Load Products</h3>
        <p className="text-sm">{error?.message || 'An unknown error occurred.'}</p>
        <p className="text-xs mt-2">Please try refreshing the page or check back later.</p>
    </div>
);


// --- المكون الرئيسي للصفحة (يستخدم SWR الآن) ---
export default function ProductsPage() {
    const [timeOfDay, setTimeOfDay] = useState<'day' | 'night'>('day');

    useEffect(() => {
        const currentHour = new Date().getHours();
        setTimeOfDay(currentHour > 18 || currentHour < 6 ? 'night' : 'day');
    }, []);

    // --- جلب المنتجات باستخدام SWR ---
    const { data: productsData, error, isLoading } = useSWR<Product[] | { items: Product[] }>(
        '/products/', // المسار النسبي صحيح بفضل الـ proxy
        fetcher,
        { revalidateOnFocus: false }
    );

    // استخراج القائمة الفعلية للمنتجات
    const products = useMemo(() => {
        if (!productsData) return [];
        return Array.isArray(productsData) ? productsData : productsData.items || [];
    }, [productsData]);

    return (
        <div className="min-h-screen w-full bg-black text-gray-100">
            <div className="fixed inset-0 -z-10">
                 <Suspense fallback={<div className="w-full h-full bg-black" />}>
                    <Canvas camera={{ position: [0, 0, 15], fov: 75 }}>
                        <LightGrid timeOfDay={timeOfDay} />
                    </Canvas>
                </Suspense>
            </div>

            <main className="container mx-auto px-4 pb-24">
                <section className="relative text-center py-32 md:py-48">
                    {isLoading && !productsData && !error ? <BannerSkeleton /> : <DynamicBanner />}
                    <motion.p
                        initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8, delay: 0.2, ease: "easeOut" }}
                        className="mt-4 text-lg text-gray-400"
                    >
                        Curated by intelligence. Delivered by drones.
                    </motion.p>
                </section>

                <PersonalizedRecommendations />

                <h2 className="text-3xl font-bold mb-12 text-center" style={{ fontFamily: "'Orbitron', sans-serif" }}>All Products</h2>

                {/* --- منطق العرض الجديد --- */}
                {error ? (
                    <ErrorDisplay error={error} />
                ) : isLoading && !productsData ? (
                    <ProductListSkeleton />
                ) : products.length > 0 ? (
                    <ProductList products={products} />
                ) : (
                    <p className="text-center text-gray-500">No products available at the moment.</p>
                )}
            </main>
        </div>
    );
}

// --- إعادة لصق الكود الكامل للمكونات الفرعية ---

// --- Upgraded background component that changes based on time of day ---
const LightGrid = ({ timeOfDay }: { timeOfDay: 'day' | 'night' }) => {
    const materialRef = useRef<THREE.ShaderMaterial>(null!);
    useFrame(({ clock }) => {
        if (materialRef.current) {
            materialRef.current.uniforms.time.value = clock.getElapsedTime();
        }
    });

    const dayColor = new THREE.Color(0.1, 0.7, 1.0); // Blueish tint for day
    const nightColor = new THREE.Color(0.5, 0.3, 1.0); // Purplish tint for night

    const shader = {
        uniforms: {
            time: { value: 0 },
            color: { value: timeOfDay === 'day' ? dayColor : nightColor }
        },
        vertexShader: `varying vec2 vUv; void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
        fragmentShader: `
            uniform float time;
            uniform vec3 color;
            varying vec2 vUv;
            void main() {
                vec2 grid = fract(vUv * vec2(30.0, 15.0) + vec2(time * 0.1, 0.0));
                float line = min(grid.x, grid.y);
                float strength = smoothstep(0.01, 0.02, line) * 0.3;
                gl_FragColor = vec4(color, strength);
            }`
    };

    return (
        <mesh position={[0, 0, -10]}>
            <planeGeometry args={[100, 100]} />
            <shaderMaterial ref={materialRef} args={[shader]} transparent depthWrite={false} />
        </mesh>
    );
};

// --- Dynamic AI Banner Component ---
const headlines = [
  "Analyzing Real-Time Trends...",
  "Drone Fleets Ready to Deliver.",
  "Your AI-Optimized Marketplace is Active.",
  "Welcome to the Future of Commerce."
];

const DynamicBanner = () => {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setIndex((prevIndex) => (prevIndex + 1) % headlines.length);
    }, 4000);
    return () => clearInterval(interval);
  }, []);

  return (
    <AnimatePresence mode="wait">
      <motion.h1
        key={headlines[index]}
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: 20 }}
        transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
        className="text-5xl md:text-7xl font-black uppercase text-white" style={{ fontFamily: "'Orbitron', sans-serif" }}
      >
        {headlines[index]}
      </motion.h1>
    </AnimatePresence>
  );
};
