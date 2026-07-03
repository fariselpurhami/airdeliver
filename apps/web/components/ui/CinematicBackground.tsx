// apps/web/components/ui/CinematicBackground.tsx

'use client';

import React, { useRef, Suspense } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Stars } from '@react-three/drei';
import * as THREE from 'three';

const BackgroundLogic = () => {
    // 1. تصحيح أسماء المراجع (Refs) لتطابق الاستخدام بالأسفل
    const light1Ref = useRef<THREE.PointLight>(null!);
    const light2Ref = useRef<THREE.PointLight>(null!);

    useFrame((state) => {
        // 2. الحل: نمرر state كمتغير كامل للوصول لـ state.clock.elapsedTime
        const time = state.clock.elapsedTime;

        // تحريك الضوء الأول (Cyan)
        if (light1Ref.current) {
            light1Ref.current.position.set(
                Math.sin(time * 0.5) * 20,
                Math.cos(time * 0.5) * 20,
                Math.cos(time * 0.5) * 15
            );
        }
        
        // تحريك الضوء الثاني (Purple)
        if (light2Ref.current) {
            light2Ref.current.position.set(
                Math.sin(time * 0.3) * -20,
                Math.cos(time * 0.3) * -20,
                Math.sin(time * 0.3) * 10
            );
        }
    });

    return (
        <>
            {/* تأثير الضباب (Fog) ليطابق صفحة الـ Products */}
            <fog attach="fog" args={['#000000', 15, 50]} /> 
            
            <ambientLight intensity={0.8} />
            
            {/* 3. ربط المراجع (Refs) بأسماء صحيحة */}
            <pointLight ref={light1Ref} position={[10, 10, 10]} intensity={300} color="#00C6FF" distance={50} />
            <pointLight ref={light2Ref} position={[-10, -10, 5]} intensity={200} color="#7F00FF" distance={50} />
            
            {/* إضافة النجوم لتعطي نفس الشكل الجمالي */}
            <Stars radius={120} depth={60} count={5000} factor={4} saturation={0.5} fade speed={0.5} />
        </>
    );
};

const CinematicBackground = () => {
    return (
        <div className="fixed inset-0 z-0 pointer-events-none">
            {/* الكاميرا عند مسافة 20 ليتناسب مع إعدادات الـ Fog */}
            <Canvas camera={{ position: [0, 0, 20], fov: 45 }} dpr={[1, 2]}>
                <Suspense fallback={null}>
                    <BackgroundLogic />
                </Suspense>
            </Canvas>
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_transparent_0%,_black_100%)] opacity-1" />
            {/* تدرج أسود للدمج مع محتوى الصفحة */}
          
	    <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-black/60" />
        </div>
    );
};

export default CinematicBackground;
