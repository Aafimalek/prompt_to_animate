import { useState, useEffect } from 'react';
import { Wand2, ChevronDown, Download, Loader2, Code, Share2, Check, Sparkles, Film, Package, LogIn, Crown, Zap, Lock } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { HistoryItem } from './Sidebar';
import { useUser, SignInButton } from '@clerk/nextjs';
import { API_BASE_URL } from '@/lib/api';

interface AnimationGeneratorProps {
    initialData?: HistoryItem | null;
    onGenerateComplete: (data: HistoryItem) => void;
    onUpgradeClick?: () => void;
    usageRefreshTrigger?: number;
}

interface ProgressStep {
    step: number;
    status: string;
    message: string;
    video_url?: string;
    code?: string;
    chat_id?: string;  // MongoDB chat ID
}

interface UsageInfo {
    tier: string;
    used: number;
    limit: number;
    remaining: number;
    basic_credits: number;
}

const PROGRESS_STEPS = [
    { id: 1, label: 'Analyzing Prompt', icon: Sparkles },
    { id: 2, label: 'Generating Code', icon: Code },
    { id: 3, label: 'Code Ready', icon: Check },
    { id: 4, label: 'Rendering Frames', icon: Film },
    { id: 5, label: 'Finalizing Video', icon: Package },
    { id: 6, label: 'Complete', icon: Check },
];

// Resolution options with tier requirements and costs
const RESOLUTIONS = [
    { id: '720p', label: '720p 30fps', minTier: 'free', cost: 1, costLabel: '' },
    { id: '1080p', label: '1080p 60fps', minTier: 'basic', cost: 1, costLabel: '' },
    { id: '4k', label: '4K 60fps', minTier: 'basic', cost: 2.5, costLabel: '2.5x' },
];

export function AnimationGenerator({ initialData, onGenerateComplete, onUpgradeClick, usageRefreshTrigger }: AnimationGeneratorProps) {
    const { user, isSignedIn } = useUser();
    const [prompt, setPrompt] = useState('');
    const [length, setLength] = useState('Medium (15s)');
    const [resolution, setResolution] = useState('720p');
    const [loading, setLoading] = useState(false);
    const [videoUrl, setVideoUrl] = useState<string | null>(null);
    const [code, setCode] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [isDropdownOpen, setIsDropdownOpen] = useState(false);
    const [isResolutionDropdownOpen, setIsResolutionDropdownOpen] = useState(false);
    const [currentProgress, setCurrentProgress] = useState<ProgressStep | null>(null);
    const [usage, setUsage] = useState<UsageInfo | null>(null);

    // Fetch usage on mount and after generation
    const fetchUsage = async () => {
        if (user?.id) {
            try {
                const response = await fetch(`${API_BASE_URL}/usage/${user.id}`);
                if (response.ok) {
                    const data = await response.json();
                    setUsage(data);
                }
            } catch (error) {
                console.error('Failed to fetch usage:', error);
            }
        }
    };

    useEffect(() => {
        fetchUsage();
    }, [user?.id, usageRefreshTrigger]);

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            const target = event.target as HTMLElement;
            if (!target.closest('.custom-dropdown-container')) {
                setIsDropdownOpen(false);
            }
            if (!target.closest('.resolution-dropdown-container')) {
                setIsResolutionDropdownOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const lengths = ['Medium (15s)', 'Long (1m)', 'Deep Dive (2m)', 'Extended (5m)'];

    // Check if user can access a resolution based on their tier
    const canAccessResolution = (minTier: string): boolean => {
        if (!usage) return minTier === 'free';
        const tierOrder = ['free', 'basic', 'pro'];
        const userTierIndex = tierOrder.indexOf(usage.tier);
        const requiredTierIndex = tierOrder.indexOf(minTier);
        // Basic with credits counts as basic tier
        if (usage.basic_credits > 0) return true;
        return userTierIndex >= requiredTierIndex;
    };

    useEffect(() => {
        if (initialData) {
            setPrompt(initialData.prompt);
            setVideoUrl(initialData.videoUrl || null);
            setCode(initialData.code || null);
        } else {
            setPrompt('');
            setVideoUrl(null);
            setCode(null);
        }
    }, [initialData]);

    const handleGenerate = async () => {
        if (!prompt.trim()) return;
        setLoading(true);
        setVideoUrl(null);
        setError(null);
        setCode(null);
        setCurrentProgress(null);

        try {
            const response = await fetch(`${API_BASE_URL}/generate-stream`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    prompt,
                    length,
                    resolution,
                    clerk_id: isSignedIn ? user?.id : undefined
                }),
            });

            if (!response.ok) {
                if (response.status === 401) {
                    throw new Error('Please sign in to generate videos');
                }
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || 'Failed to start generation');
            }

            const reader = response.body?.getReader();
            const decoder = new TextDecoder();

            if (!reader) {
                throw new Error('No response body');
            }

            let buffer = '';
            let completed = false;

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                // Keep the last partial line in the buffer
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data: ProgressStep = JSON.parse(line.slice(6));
                            setCurrentProgress(data);

                            if (data.status === 'complete' && data.video_url && data.code) {
                                setVideoUrl(data.video_url);
                                setCode(data.code);
                                completed = true;

                                // Notify parent to save/update history
                                onGenerateComplete({
                                    id: data.chat_id || crypto.randomUUID(),
                                    prompt: prompt,
                                    timestamp: Date.now(),
                                    videoUrl: data.video_url,
                                    code: data.code
                                });
                            } else if (data.status === 'error') {
                                setError(data.message || 'An error occurred during generation');
                                setLoading(false);
                                return;
                            }
                        } catch (parseError) {
                            console.error('SSE parse error:', parseError, 'Line:', line);
                            // Continue processing other lines
                        }
                    }
                }
            }

            // Process any remaining data in the buffer
            if (buffer.startsWith('data: ')) {
                try {
                    const data: ProgressStep = JSON.parse(buffer.slice(6));
                    if (data.status === 'complete' && data.video_url && data.code && !completed) {
                        setVideoUrl(data.video_url);
                        setCode(data.code);
                        completed = true;
                        onGenerateComplete({
                            id: data.chat_id || crypto.randomUUID(),
                            prompt: prompt,
                            timestamp: Date.now(),
                            videoUrl: data.video_url,
                            code: data.code
                        });
                    }
                } catch {
                    // Ignore
                }
            }

            // Always set loading to false when stream ends
            setLoading(false);

            // Refresh usage after generation
            fetchUsage();

            if (!completed) {
                setError('Generation ended unexpectedly. Please try again.');
            }
        } catch (err: unknown) {
            setError((err as Error).message || 'Something went wrong');
            setLoading(false);
        }
    };

    return (
        <div className="w-full max-w-3xl mx-auto px-4 md:px-6 min-h-full flex flex-col justify-center py-6 md:py-8">
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6 }}
                className="text-center mb-10 flex flex-col items-center"
            >

                <h1 className="text-3xl sm:text-4xl md:text-5xl font-bold tracking-tight mb-3 md:mb-4 bg-gradient-to-r from-orange-500 via-orange-600 to-orange-500 bg-clip-text text-transparent font-display">
                    Manimancer
                </h1>
                <p className="text-base md:text-lg text-muted-foreground max-w-lg mx-auto px-2">
                    Turn your concepts into beautiful visualizations. Describe it, and watch the magic happen.
                </p>
            </motion.div>

            {/* Input Area */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: 0.1 }}
                className="w-full space-y-4"
            >
                <div className="relative group rounded-2xl md:rounded-3xl transition-all duration-300 shadow-2xl shadow-zinc-200/50 dark:shadow-black/50 border border-white/20 dark:border-zinc-800/50 active:scale-[0.99] duration-200">
                    <div className="bg-white/60 dark:bg-zinc-900/60 backdrop-blur-2xl rounded-2xl md:rounded-3xl p-3 sm:p-4 md:p-5 flex flex-col gap-3 md:gap-4 ring-1 ring-black/5 dark:ring-white/5">
                        <textarea
                            value={prompt}
                            onChange={(e) => setPrompt(e.target.value)}
                            placeholder="Describe your animation... e.g. 'Visualize a sorting algorithm'"
                            className="w-full bg-transparent text-base md:text-lg placeholder:text-zinc-400 dark:placeholder:text-zinc-500 text-zinc-900 dark:text-zinc-100 p-1.5 md:p-2 focus:outline-none resize-none min-h-[80px] md:min-h-[100px] font-sans"
                            onKeyDown={(e) => {
                                if (e.key === 'Enter' && !e.shiftKey) {
                                    e.preventDefault();
                                    handleGenerate();
                                }
                            }}
                        />

                        <div className="flex flex-wrap items-center justify-between gap-2 md:gap-3 border-t border-zinc-100 dark:border-zinc-800 pt-2 md:pt-3">
                            {/* Controls Row - Dropdowns */}
                            <div className="flex flex-wrap items-center gap-2">
                                {/* Custom Dropdown */}
                                <div className="relative custom-dropdown-container z-50">
                                    <button
                                        onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                                        className={cn(
                                            "flex items-center space-x-1.5 md:space-x-2 px-3 md:px-4 py-2 md:py-2.5 rounded-full text-[11px] md:text-xs font-medium transition-all duration-200 border-2 select-none",
                                            // Standard Colors
                                            "bg-zinc-50 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100",
                                            "border-zinc-200 dark:border-zinc-700",
                                            // Hover & Open States
                                            "hover:border-orange-500 hover:text-orange-600 dark:hover:text-orange-400",
                                            isDropdownOpen && "border-orange-500 ring-2 ring-orange-500/20 text-orange-600 dark:text-orange-400"
                                        )}
                                    >
                                        <span className="hidden xs:inline">{length}</span>
                                        <span className="xs:hidden">{length.split(' ')[0]}</span>
                                        <ChevronDown className={cn("w-3 md:w-3.5 h-3 md:h-3.5 transition-transform duration-200", isDropdownOpen && "rotate-180")} />
                                    </button>

                                    <AnimatePresence>
                                        {isDropdownOpen && (
                                            <motion.div
                                                initial={{ opacity: 0, y: -10, scale: 0.95 }}
                                                animate={{ opacity: 1, y: 0, scale: 1 }}
                                                exit={{ opacity: 0, y: -10, scale: 0.95 }}
                                                transition={{ duration: 0.15, ease: "easeOut" }}
                                                className="absolute bottom-full left-0 mb-2 w-40 p-1.5 rounded-xl border border-zinc-200 dark:border-zinc-700 bg-white/95 dark:bg-zinc-900/95 backdrop-blur-xl shadow-xl overflow-hidden z-50 origin-bottom-left"
                                            >
                                                <div className="flex flex-col space-y-0.5">
                                                    {lengths.map((l) => (
                                                        <button
                                                            key={l}
                                                            onClick={() => {
                                                                setLength(l);
                                                                setIsDropdownOpen(false);
                                                            }}
                                                            className={cn(
                                                                "w-full text-left px-3 py-2 rounded-lg text-xs font-medium transition-all flex items-center justify-between",
                                                                length === l
                                                                    ? "bg-orange-500 text-white shadow-md shadow-orange-500/20"
                                                                    : "text-zinc-600 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 hover:text-zinc-900 dark:hover:text-white"
                                                            )}
                                                        >
                                                            {l}
                                                            {length === l && <Wand2 className="w-3 h-3 text-white/90" />}
                                                        </button>
                                                    ))}
                                                </div>
                                            </motion.div>
                                        )}
                                    </AnimatePresence>
                                </div>

                                {/* Resolution Dropdown */}
                                <div className="relative resolution-dropdown-container z-40">
                                    <button
                                        onClick={() => setIsResolutionDropdownOpen(!isResolutionDropdownOpen)}
                                        className={cn(
                                            "flex items-center space-x-1.5 md:space-x-2 px-3 md:px-4 py-2 md:py-2.5 rounded-full text-[11px] md:text-xs font-medium transition-all duration-200 border-2 select-none",
                                            "bg-zinc-50 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100",
                                            "border-zinc-200 dark:border-zinc-700",
                                            "hover:border-orange-500 hover:text-orange-600 dark:hover:text-orange-400",
                                            isResolutionDropdownOpen && "border-orange-500 ring-2 ring-orange-500/20 text-orange-600 dark:text-orange-400"
                                        )}
                                    >
                                        <Film className="w-3 md:w-3.5 h-3 md:h-3.5" />
                                        <span className="hidden sm:inline">{RESOLUTIONS.find(r => r.id === resolution)?.label || resolution}</span>
                                        <span className="sm:hidden">{resolution}</span>
                                        <ChevronDown className={cn("w-3 md:w-3.5 h-3 md:h-3.5 transition-transform duration-200", isResolutionDropdownOpen && "rotate-180")} />
                                    </button>

                                    <AnimatePresence>
                                        {isResolutionDropdownOpen && (
                                            <motion.div
                                                initial={{ opacity: 0, y: -10, scale: 0.95 }}
                                                animate={{ opacity: 1, y: 0, scale: 1 }}
                                                exit={{ opacity: 0, y: -10, scale: 0.95 }}
                                                transition={{ duration: 0.15, ease: "easeOut" }}
                                                className="absolute bottom-full left-0 mb-2 w-44 p-1.5 rounded-xl border border-zinc-200 dark:border-zinc-700 bg-white/95 dark:bg-zinc-900/95 backdrop-blur-xl shadow-xl overflow-hidden z-50 origin-bottom-left"
                                            >
                                                <div className="flex flex-col space-y-0.5">
                                                    {RESOLUTIONS.map((r) => {
                                                        const isLocked = !canAccessResolution(r.minTier);
                                                        const isSelected = resolution === r.id;

                                                        return (
                                                            <button
                                                                key={r.id}
                                                                onClick={() => {
                                                                    if (!isLocked) {
                                                                        setResolution(r.id);
                                                                        setIsResolutionDropdownOpen(false);
                                                                    }
                                                                }}
                                                                disabled={isLocked}
                                                                className={cn(
                                                                    "w-full text-left px-3 py-2 rounded-lg text-xs font-medium transition-all flex items-center justify-between",
                                                                    isSelected && !isLocked
                                                                        ? "bg-orange-500 text-white shadow-md shadow-orange-500/20"
                                                                        : isLocked
                                                                            ? "text-zinc-400 dark:text-zinc-600 cursor-not-allowed"
                                                                            : "text-zinc-600 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 hover:text-zinc-900 dark:hover:text-white"
                                                                )}
                                                            >
                                                                <span className="flex items-center gap-2">
                                                                    {isLocked && <Lock className="w-3 h-3" />}
                                                                    {r.label}
                                                                </span>
                                                                <span className="flex items-center gap-1">
                                                                    {r.costLabel && <span className="text-[10px] opacity-70">{r.costLabel}</span>}
                                                                    {isSelected && !isLocked && <Check className="w-3 h-3 text-white/90" />}
                                                                </span>
                                                            </button>
                                                        );
                                                    })}
                                                </div>
                                            </motion.div>
                                        )}
                                    </AnimatePresence>
                                </div>
                            </div>

                            {/* Right side: Usage Display + Generate - wrapped for mobile */}
                            <div className="flex flex-wrap items-center gap-2 ml-auto">
                                {/* Usage Display */}
                                {usage && isSignedIn && (
                                    <div className="flex items-center gap-1.5 md:gap-2">
                                        {/* Plan Badge */}
                                        <div className={cn(
                                            "flex items-center gap-1 md:gap-1.5 px-2 md:px-3 py-1 md:py-1.5 rounded-full text-[10px] md:text-xs font-medium",
                                            usage.tier === 'pro'
                                                ? "bg-gradient-to-r from-orange-500 to-orange-600 text-white"
                                                : usage.basic_credits > 0
                                                    ? "bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400"
                                                    : "bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400"
                                        )}>
                                            {usage.tier === 'pro' ? (
                                                <Crown className="w-2.5 md:w-3 h-2.5 md:h-3" />
                                            ) : usage.basic_credits > 0 ? (
                                                <Zap className="w-2.5 md:w-3 h-2.5 md:h-3" />
                                            ) : (
                                                <Sparkles className="w-2.5 md:w-3 h-2.5 md:h-3" />
                                            )}
                                            <span className="hidden sm:inline">
                                                {usage.tier === 'pro'
                                                    ? `Pro: ${usage.remaining}/${usage.limit}`
                                                    : usage.basic_credits > 0
                                                        ? `${usage.basic_credits} credits`
                                                        : `${usage.used}/${usage.limit}`
                                                }
                                            </span>
                                            <span className="sm:hidden">
                                                {usage.tier === 'pro'
                                                    ? `${usage.remaining}/${usage.limit}`
                                                    : usage.basic_credits > 0
                                                        ? `${usage.basic_credits}`
                                                        : `${usage.remaining}`
                                                }
                                            </span>
                                        </div>

                                        {/* Upgrade Button for Free users - hidden on very small screens */}
                                        {usage.tier === 'free' && usage.basic_credits === 0 && onUpgradeClick && (
                                            <button
                                                onClick={onUpgradeClick}
                                                className="hidden xs:block text-[10px] md:text-xs font-medium text-orange-500 hover:text-orange-600 hover:underline"
                                            >
                                                Upgrade
                                            </button>
                                        )}
                                    </div>
                                )}

                                {isSignedIn ? (
                                    <motion.button
                                        onClick={handleGenerate}
                                        disabled={loading || !prompt}
                                        whileHover={{ scale: 1.05 }}
                                        whileTap={{ scale: 0.95 }}
                                        className={cn(
                                            "px-3 md:px-5 py-2 md:py-2.5 rounded-lg md:rounded-xl font-medium transition-all flex items-center space-x-1.5 md:space-x-2 border-2 text-sm md:text-base",
                                            loading || !prompt
                                                ? "bg-zinc-100 dark:bg-zinc-800 text-zinc-400 border-zinc-200 dark:border-zinc-700 cursor-not-allowed"
                                                : [
                                                    "bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 border-zinc-900 dark:border-white shadow-lg",
                                                    "hover:bg-white dark:hover:bg-zinc-900",
                                                    "hover:text-orange-600 dark:hover:text-orange-400",
                                                    "hover:border-orange-500 dark:hover:border-orange-500",
                                                    "hover:shadow-orange-500/20"
                                                ].join(" ")
                                        )}
                                    >
                                        {loading ? <Loader2 className="w-3.5 md:w-4 h-3.5 md:h-4 animate-spin" /> : <Wand2 className="w-3.5 md:w-4 h-3.5 md:h-4" />}
                                        <span className="hidden xs:inline">{loading ? 'Conjuring...' : 'Generate'}</span>
                                        <span className="xs:hidden">{loading ? '...' : 'Go'}</span>
                                    </motion.button>
                                ) : (
                                    <SignInButton mode="modal">
                                        <motion.button
                                            whileHover={{ scale: 1.05 }}
                                            whileTap={{ scale: 0.95 }}
                                            className={cn(
                                                "px-3 md:px-5 py-2 md:py-2.5 rounded-lg md:rounded-xl font-medium transition-all flex items-center space-x-1.5 md:space-x-2 border-2 text-sm md:text-base",
                                                "bg-orange-500 text-white border-orange-500 shadow-lg shadow-orange-500/20",
                                                "hover:bg-orange-600 hover:border-orange-600"
                                            )}
                                        >
                                            <LogIn className="w-3.5 md:w-4 h-3.5 md:h-4" />
                                            <span className="hidden xs:inline">Sign in to Generate</span>
                                            <span className="xs:hidden">Sign in</span>
                                        </motion.button>
                                    </SignInButton>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            </motion.div>

            {/* Result Section */}
            <AnimatePresence>
                {(videoUrl || loading || error) && (
                    <motion.div
                        initial={{ opacity: 0, y: 40 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0 }}
                        className="mt-12"
                    >
                        {error && (
                            <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm text-center">
                                {error}
                            </div>
                        )}

                        {loading && !videoUrl && !error && (
                            <div className="w-full rounded-2xl bg-card border border-border p-8">
                                {/* Progress Steps */}
                                <div className="space-y-4">
                                    {PROGRESS_STEPS.map((step, index) => {
                                        const Icon = step.icon;
                                        const isActive = currentProgress?.step === step.id;
                                        const isComplete = currentProgress ? currentProgress.step > step.id : false;
                                        const isPending = currentProgress ? currentProgress.step < step.id : true;

                                        return (
                                            <motion.div
                                                key={step.id}
                                                initial={{ opacity: 0, x: -20 }}
                                                animate={{ opacity: 1, x: 0 }}
                                                transition={{ delay: index * 0.1 }}
                                                className={cn(
                                                    "flex items-center space-x-4 p-4 rounded-xl transition-all duration-500",
                                                    isActive && "bg-orange-500/10 border border-orange-500/30",
                                                    isComplete && "bg-green-500/10 border border-green-500/20",
                                                    isPending && "opacity-40"
                                                )}
                                            >
                                                {/* Step Icon */}
                                                <div className={cn(
                                                    "w-10 h-10 rounded-full flex items-center justify-center transition-all duration-500",
                                                    isActive && "bg-orange-500 text-white shadow-lg shadow-orange-500/30",
                                                    isComplete && "bg-green-500 text-white",
                                                    isPending && "bg-zinc-800 text-zinc-500"
                                                )}>
                                                    {isActive ? (
                                                        <motion.div
                                                            animate={{ rotate: 360 }}
                                                            transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                                                        >
                                                            <Loader2 className="w-5 h-5" />
                                                        </motion.div>
                                                    ) : isComplete ? (
                                                        <Check className="w-5 h-5" />
                                                    ) : (
                                                        <Icon className="w-5 h-5" />
                                                    )}
                                                </div>

                                                {/* Step Info */}
                                                <div className="flex-1">
                                                    <p className={cn(
                                                        "font-medium transition-colors",
                                                        isActive && "text-orange-500",
                                                        isComplete && "text-green-500",
                                                        isPending && "text-zinc-500"
                                                    )}>
                                                        {step.label}
                                                    </p>
                                                    {isActive && currentProgress && (
                                                        <motion.p
                                                            initial={{ opacity: 0 }}
                                                            animate={{ opacity: 1 }}
                                                            className="text-sm text-muted-foreground mt-0.5"
                                                        >
                                                            {currentProgress.message}
                                                        </motion.p>
                                                    )}
                                                </div>

                                                {/* Step Number */}
                                                <span className={cn(
                                                    "text-xs font-mono",
                                                    isActive && "text-orange-400",
                                                    isComplete && "text-green-400",
                                                    isPending && "text-zinc-600"
                                                )}>
                                                    {String(step.id).padStart(2, '0')}
                                                </span>
                                            </motion.div>
                                        );
                                    })}
                                </div>

                                {/* Animated Gradient Bar */}
                                <div className="mt-6 h-1 bg-zinc-800 rounded-full overflow-hidden">
                                    <motion.div
                                        className="h-full bg-gradient-to-r from-orange-500 via-yellow-500 to-orange-500 rounded-full"
                                        initial={{ width: "0%" }}
                                        animate={{
                                            width: currentProgress ? `${(currentProgress.step / 6) * 100}%` : "5%"
                                        }}
                                        transition={{ duration: 0.5, ease: "easeOut" }}
                                    />
                                </div>

                                {/* Fun Message */}
                                <motion.p
                                    key={currentProgress?.step}
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    className="text-center text-sm text-muted-foreground mt-4"
                                >
                                    {currentProgress?.step === 2 && "✨ The AI is crafting your animation..."}
                                    {currentProgress?.step === 4 && "🎬 Rendering beautiful frames..."}
                                    {currentProgress?.step === 5 && "📦 Almost there! Packaging your video..."}
                                    {(!currentProgress || currentProgress.step <= 1) && "🔮 Preparing the magic..."}
                                </motion.p>
                            </div>
                        )}

                        {videoUrl && (
                            <div className="space-y-4 bg-card border border-border rounded-2xl overflow-hidden shadow-2xl">
                                <div className="relative aspect-video bg-black">
                                    <video
                                        src={videoUrl}
                                        controls
                                        autoPlay
                                        loop
                                        className="w-full h-full object-contain"
                                    />
                                </div>

                                <div className="flex items-center justify-between p-4 bg-card/50 backdrop-blur-sm border-t border-border">
                                    <div className="flex items-center space-x-2">
                                        <button
                                            onClick={() => { }}
                                            className="p-2 rounded-md hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors"
                                            title="View Code"
                                        >
                                            <Code className="w-4 h-4" />
                                        </button>
                                        <button
                                            className="p-2 rounded-md hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors"
                                            title="Share"
                                        >
                                            <Share2 className="w-4 h-4" />
                                        </button>
                                    </div>

                                    <a
                                        href={videoUrl}
                                        download
                                        className="flex items-center space-x-2 px-4 py-2 bg-secondary hover:bg-secondary/80 rounded-md text-secondary-foreground text-sm font-medium transition-colors"
                                    >
                                        <Download className="w-3.5 h-3.5" />
                                        <span>Download</span>
                                    </a>
                                </div>

                                {code && (
                                    <div className="px-4 pb-4">
                                        <details className="group">
                                            <summary className="cursor-pointer list-none flex items-center space-x-2 text-muted-foreground hover:text-foreground transition-colors text-xs font-medium content-none">
                                                <ChevronDown className="w-3 h-3 group-open:rotate-180 transition-transform" />
                                                <span>View Manim Code</span>
                                            </summary>
                                            <div className="mt-2 p-4 rounded-lg bg-zinc-900 dark:bg-zinc-950 border border-zinc-700 dark:border-zinc-800 overflow-x-auto">
                                                <pre className="text-emerald-400 dark:text-emerald-300 font-mono text-xs leading-relaxed whitespace-pre-wrap">
                                                    {code}
                                                </pre>
                                            </div>
                                        </details>
                                    </div>
                                )}
                            </div>
                        )}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
