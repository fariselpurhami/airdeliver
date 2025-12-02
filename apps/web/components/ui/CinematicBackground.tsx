// apps/web/components/ui/CinematicBackground.tsx

'use client';

import React, { useRef, Suspense } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Stars, Float } from '@react-three/drei';
import * as THREE from 'three';

const BackgroundLogic = () => {
    const lightRef = useRef<THREE.PointLight>(null!);

    useFrame(({ clock }) => {
        if (lightRef.current) {
          
            lightRef.current.position.x = Math.sin(clock.elapsedTime * 0.5) * 10;
            lightRef.current.position.z = Math.cos(clock.elapsedTime * 0.5) * 10;
        }
    });

    return (
        <>
            <fog attach="fog" args={['#050505', 5, 30]} /> 
            
            <ambientLight intensity={0.2} />
            <pointLight ref={lightRef} position={[10, 10, 10]} intensity={1.5} color="#00C6FF" />
            
            <Stars radius={80} depth={40} count={3000} factor={4} saturation={0} fade speed={0.5} />
            <Float speed={2} rotationIntensity={0.5} floatIntensity={0.5} />
        </>
    );
};

const CinematicBackground = () => {
    return (
        <div className="fixed inset-0 z-0 opacity-60 pointer-events-none">
            <Canvas camera={{ position: [0, 0, 10], fov: 45 }}>
                <Suspense fallback={null}>
                    <BackgroundLogic />
                </Suspense>
            </Canvas>
           
            <div className="absolute inset-0 bg-gradient-to-b from-black via-transparent to-black" />
        </div>
    );
};

export default CinematicBackground;
