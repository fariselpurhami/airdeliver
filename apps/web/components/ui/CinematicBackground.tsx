// apps/web/components/ui/CinematicBackground.tsx

'use client';

import React, { useRef, Suspense } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Stars, Float } from '@react-three/drei';
import * as THREE from 'three';

const BackgroundLogic = () => {
    const lightRef = useRef<THREE.PointLight>(null!);
    const light2Ref = useRef<THREE.PointLight>(null!);

    useFrame(({ clock }) => {
        if (lightRef.current) {
          
            lightRef.current.position.x = Math.sin(clock.elapsedTime * 0.5) * 20;
            lightRef.current.position.z = Math.cos(clock.elapsedTime * 0.5) * 20;
	    lightRef.current.position.y = Math.cos(clock.elapsedTime * 0.5) * 15;
        }
	if (light2Ref.current) {
            light2Ref.current.position.x = Math.sin(clock.elapsedTime * 0.3) * 20;
	    light2Ref.current.position.z = Math.cos(clock.elapsedTime * 0.3) * 20;
	    light2Ref.current.position.y = Math.cos(clock.elapsedTime * 0.3) * 15;
	}
    });

    return (
        <>
            <fog attach="fog" args={['#000000', 15, 50]} /> 
            
            <ambientLight intensity={0.8} />
            <pointLight ref={lightRef} position={[10, 10, 10]} intensity={300} color="#00C6FF" distance={50} />
	    <pointLight ref={lightRef} position={[-10, -10, 5]} intensity={200} color="#7F00FF" distance={50} />
          
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
