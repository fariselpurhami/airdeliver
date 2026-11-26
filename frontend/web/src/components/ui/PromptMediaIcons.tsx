import { Camera, Mic } from 'lucide-react';

/**
 * Camera and microphone marks at the end of the prompt bars, drawn like the ones inside the
 * Order with Air overlay (same icons, sizes and strokes). They are decorative here: the whole
 * bar is one button that opens the overlay, where the real camera upload and voice controls live.
 */
export function PromptMediaIcons() {
  return (
    <span className="mr-2 flex shrink-0 items-center gap-1 sm:mr-3" aria-hidden="true" data-testid="prompt-media-icons">
      <span className="flex h-8 w-8 items-center justify-center rounded-full bg-white/[0.08] text-white/75 shadow-[inset_0_1px_1px_rgba(255,255,255,0.12)] sm:h-9 sm:w-9">
        <Camera size={17} strokeWidth={1.8} />
      </span>
      <span className="flex h-8 w-8 items-center justify-center rounded-full text-white/60 sm:h-9 sm:w-9">
        <Mic size={18} strokeWidth={1.8} />
      </span>
    </span>
  );
}
