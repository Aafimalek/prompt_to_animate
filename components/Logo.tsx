import { FC } from 'react';
import { cn } from '@/lib/utils';
import { motion } from 'framer-motion';

interface LogoProps {
    className?: string;
    showText?: boolean;
    animated?: boolean;
}

export const Logo: FC<LogoProps> = ({ className, showText = true, animated = false }) => {
    return (
        <div className={cn("flex items-center space-x-2", className)}>
            <div className="relative w-8 h-8 flex items-center justify-center">
                {/* Background Gradient Blob */}
                <div className="absolute inset-0 bg-gradient-to-tr from-purple-600 to-blue-500 rounded-lg blur-[2px] opacity-80" />

                {/* Custom Icon: Wand + Motion Curve */}
                <svg viewBox="0 0 24 24" fill="none" className="relative w-5 h-5 text-white" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    {/* Wand */}
                    <path d="M14.5 4l-10.5 10.5a2.121 2.121 0 0 0 3 3l10.5-10.5" />
                    <path d="M20 2l-3.5 3.5" />
                    {/* Stars/Sparkles around wand tip */}
                    <path d="M21 7l1 1" />
                    <path d="M17 3l1 1" />
                    {/* Motion Curve (Animate aspect) */}
                    <path d="M3 20c2 0 5-1 7-4" className="opacity-70" />
                </svg>
            </div>

            {showText && (
                <span className={cn(
                    "font-bold text-xl tracking-tight select-none font-logo bg-gradient-to-r from-white to-zinc-400 bg-clip-text text-transparent",
                    animated && "animate-in fade-in slide-in-from-left-2 duration-500"
                )}>
                    Manimancer
                </span>
            )}
        </div>
    );
};
