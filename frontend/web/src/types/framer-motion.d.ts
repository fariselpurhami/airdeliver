// frontend/web/types/framer-motion.d.ts

import 'framer-motion';

declare module 'framer-motion' {
  
  interface Transition {
  
    ease?: 
      | 'linear'
      | 'easeIn'
      | 'easeOut'
      | 'easeInOut'
      | 'circIn'
      | 'circOut'
      | 'circInOut'
      | 'backIn'
      | 'backOut'
      | 'backInOut'
      | 'anticipate'
      | number[] 
      | ((t: number) => number); 
  }
}
