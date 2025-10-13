import { motion, AnimatePresence } from 'framer-motion';
import { useAIOrderingStore } from '@/hooks/useAIOrderingStore';

const thinkingSteps = ["Analyzing order...", "Matching inventory...", "Personalizing suggestions...", "✅ Ready!"];

export const CinematicLoader = () => {
    const isProcessing = useAIOrderingStore((state) => state.isProcessing); // We'll add this state
    
    // This component will use Framer Motion to animate through the `thinkingSteps` array
    // ... animation logic ...

    return (
        <AnimatePresence>
            {isProcessing && (
                <motion.div className="absolute inset-0 bg-black/50 flex items-center justify-center">
                    {/* Animate text here */}
                </motion.div>
            )}
        </AnimatePresence>
    );
};
