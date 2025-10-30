// apps/web/components/ui/ThemeToggle.tsx

'use client';

import { useTheme } from 'next-themes';
import { FiSun, FiMoon } from 'react-icons/fi';
import { Button } from './Button';
import { useEffect, useState } from 'react';

export function ThemeToggle() {
  const { setTheme, resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  if (!mounted) {
    return <div className="w-9 h-9" />; 
  }

  return (
    <Button
      variant="outline"
      size="sm"
      onClick={() => setTheme(resolvedTheme === 'dark' ? 'light' : 'dark')}
      className="p-2"
    >
      {resolvedTheme === 'dark' ? (
        <FiSun className="h-5 w-5" />
      ) : (
        <FiMoon className="h-5 w-5" />
      )}
      <span className="sr-only">Toggle theme</span>
    </Button>
  );
}
