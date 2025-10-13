'use client';

import React, { useState, useEffect, Suspense, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Canvas, useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import ProductList from '@/components/products/ProductList';
import { type Product } from '@/components/products/ProductCard';
import { useSession } from 'next-auth/react';

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

// --- Predictive Recommendations Component ---
const PersonalizedRecommendations = () => {
    const [recommendations, setRecommendations] = useState<Product[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const { data: session, status } = useSession();

    useEffect(() => {
        if (status === 'authenticated') {
            const fetchRecommendations = async () => {
                try {
                    const userId = (session?.user as any)?.id; 
                    if (!userId) return;

                    const response = await fetch(`http://127.0.0.1:8000/api/v1/products/suggestions?product_id=1&user_id=${userId}`);
                    if (!response.ok) throw new Error('Failed to fetch recommendations');
                    const data = await response.json();
                    setRecommendations(data.map((p: any) => ({...p, isAIRec: true})));
                } catch (error) {
                    console.error("Failed to fetch recommendations:", error);
                } finally {
                    setIsLoading(false);
                }
            };
            fetchRecommendations();
        } else if (status === 'unauthenticated') {
            setIsLoading(false);
        }
    }, [status, session]);

    if (status !== 'authenticated' || isLoading || recommendations.length === 0) {
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

// --- Loading Spinner Component ---
const LoadingSpinner = () => (
    <div className="flex justify-center items-center h-64">
        <div className="w-12 h-12 border-4 border-cyan-400 border-t-transparent rounded-full animate-spin" />
    </div>
);

// --- Main Page Component ---
export default function ProductsPage() {
    const [products, setProducts] = useState<Product[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [timeOfDay, setTimeOfDay] = useState<'day' | 'night'>('day');

    useEffect(() => {
        const currentHour = new Date().getHours();
        setTimeOfDay(currentHour > 18 || currentHour < 6 ? 'night' : 'day');

        const fetchProducts = async () => {
            setIsLoading(true);
            try {
                const response = await fetch('http://127.0.0.1:8000/api/v1/products/'); 
                if (!response.ok) throw new Error(`Network response was not ok`);
                const data = await response.json();
                setProducts(data);
            } catch (error) {
                console.error("Failed to fetch products:", error);
            } finally {
                setIsLoading(false);
            }
        };
        fetchProducts();
    }, []);

    return (
        <div className="min-h-screen w-full bg-black text-gray-100">
            <div className="fixed inset-0 -z-10">
                <Canvas camera={{ position: [0, 0, 15], fov: 75 }}>
                    <Suspense fallback={null}><LightGrid timeOfDay={timeOfDay} /></Suspense>
                </Canvas>
            </div>

            <main className="container mx-auto px-4 pb-24">
                <section className="relative text-center py-32 md:py-48">
                    <DynamicBanner />
                    <motion.p
                        initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8, delay: 0.2, ease: "easeOut" }}
                        className="mt-4 text-lg text-gray-400"
                    >
                        Curated by intelligence. Delivered by drones.
                    </motion.p>
                </section>

                <PersonalizedRecommendations />

                <h2 className="text-3xl font-bold mb-12 text-center" style={{ fontFamily: "'Orbitron', sans-serif" }}>All Products</h2>
                {isLoading ? (
                    <LoadingSpinner />
                ) : (
                    <ProductList products={products} />
                )}
            </main>
        </div>
    );
}
