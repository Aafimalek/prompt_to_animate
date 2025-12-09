import { useState, useEffect } from 'react';
import { Wand2, ChevronDown, Download, Loader2, Code, Share2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { HistoryItem } from './Sidebar';

interface AnimationGeneratorProps {
    initialData?: HistoryItem | null;
    onGenerateComplete: (data: HistoryItem) => void;
}

export function AnimationGenerator({ initialData, onGenerateComplete }: AnimationGeneratorProps) {
    const [prompt, setPrompt] = useState('');
    const [length, setLength] = useState('Short (5s)');
    const [loading, setLoading] = useState(false);
    const [videoUrl, setVideoUrl] = useState<string | null>(null);
    const [code, setCode] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [isDropdownOpen, setIsDropdownOpen] = useState(false);

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            const target = event.target as HTMLElement;
            if (!target.closest('.custom-dropdown-container')) {
                setIsDropdownOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const lengths = ['Short (5s)', 'Medium (15s)', 'Long (1m)', 'Deep Dive (2m)'];

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

        try {
            const response = await fetch('http://localhost:8000/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ prompt, length }),
            });

            if (!response.ok) {
                throw new Error('Failed to generate animation');
            }

            const data = await response.json();
            setVideoUrl(data.video_url);
            setCode(data.code);

            // Notify parent to save history
            onGenerateComplete({
                id: crypto.randomUUID(),
                prompt: prompt,
                timestamp: Date.now(),
                videoUrl: data.video_url,
                code: data.code
            });

        } catch (err: any) {
            setError(err.message || 'Something went wrong');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="w-full max-w-3xl mx-auto px-6 min-h-full flex flex-col justify-center py-8">
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6 }}
                className="text-center mb-10 flex flex-col items-center"
            >

                <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-4 bg-gradient-to-r from-orange-500 via-orange-600 to-orange-500 bg-clip-text text-transparent font-display">
                    Manimancer
                </h1>
                <p className="text-lg text-muted-foreground max-w-lg mx-auto">
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
                <div className="relative group rounded-3xl transition-all duration-300 shadow-2xl shadow-zinc-200/50 dark:shadow-black/50 border border-white/20 dark:border-zinc-800/50 active:scale-[0.99] duration-200">
                    <div className="bg-white/60 dark:bg-zinc-900/60 backdrop-blur-2xl rounded-3xl p-5 flex flex-col gap-4 ring-1 ring-black/5 dark:ring-white/5">
                        <textarea
                            value={prompt}
                            onChange={(e) => setPrompt(e.target.value)}
                            placeholder="Describe your animation... e.g. 'Visualize a sorting algorithm'"
                            className="w-full bg-transparent text-lg placeholder:text-zinc-400 dark:placeholder:text-zinc-500 text-zinc-900 dark:text-zinc-100 p-2 focus:outline-none resize-none min-h-[100px] font-sans"
                            onKeyDown={(e) => {
                                if (e.key === 'Enter' && !e.shiftKey) {
                                    e.preventDefault();
                                    handleGenerate();
                                }
                            }}
                        />

                        <div className="flex items-center justify-between gap-3 border-t border-zinc-100 dark:border-zinc-800 pt-3 relative z-20">
                            {/* Custom Dropdown */}
                            <div className="relative custom-dropdown-container">
                                <button
                                    onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                                    className={cn(
                                        "flex items-center space-x-2 px-4 py-2.5 rounded-full text-xs font-medium transition-all duration-200 border-2 select-none",
                                        // Standard Colors
                                        "bg-zinc-50 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100",
                                        "border-zinc-200 dark:border-zinc-700",
                                        // Hover & Open States
                                        "hover:border-orange-500 hover:text-orange-600 dark:hover:text-orange-400",
                                        isDropdownOpen && "border-orange-500 ring-2 ring-orange-500/20 text-orange-600 dark:text-orange-400"
                                    )}
                                >
                                    <span>{length}</span>
                                    <ChevronDown className={cn("w-3.5 h-3.5 transition-transform duration-200", isDropdownOpen && "rotate-180")} />
                                </button>

                                <AnimatePresence>
                                    {isDropdownOpen && (
                                        <motion.div
                                            initial={{ opacity: 0, y: 10, scale: 0.95 }}
                                            animate={{ opacity: 1, y: 0, scale: 1 }}
                                            exit={{ opacity: 0, y: 10, scale: 0.95 }}
                                            transition={{ duration: 0.15, ease: "easeOut" }}
                                            className="absolute top-full left-0 mt-2 w-40 p-1.5 rounded-xl border border-zinc-200 dark:border-zinc-700 bg-white/95 dark:bg-zinc-900/95 backdrop-blur-xl shadow-xl overflow-hidden z-50 origin-top-left"
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

                            <motion.button
                                onClick={handleGenerate}
                                disabled={loading || !prompt}
                                whileHover={{ scale: 1.05 }}
                                whileTap={{ scale: 0.95 }}
                                className={cn(
                                    "px-5 py-2.5 rounded-xl font-medium transition-all flex items-center space-x-2 border-2",
                                    loading
                                        ? "bg-zinc-100 dark:bg-zinc-800 text-zinc-400 border-zinc-200 dark:border-zinc-700 cursor-not-allowed"
                                        : [
                                            "bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 border-zinc-900 dark:border-white shadow-lg",
                                            // Orange Hover Effect: Invert colors to Orange Border + Text
                                            "hover:bg-white dark:hover:bg-zinc-900",
                                            "hover:text-orange-600 dark:hover:text-orange-400",
                                            "hover:border-orange-500 dark:hover:border-orange-500",
                                            "hover:shadow-orange-500/20"
                                        ].join(" ")
                                )}
                            /** ... */
                            >
                                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Wand2 className="w-4 h-4" />}
                                <span>{loading ? 'Conjuring...' : 'Generate'}</span>
                            </motion.button>
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
                            <div className="w-full aspect-video rounded-2xl bg-card border border-border flex flex-col items-center justify-center space-y-6">
                                <div className="relative">
                                    <div className="w-16 h-16 border-2 border-zinc-800 rounded-full" />
                                    <div className="absolute inset-0 w-16 h-16 border-2 border-t-foreground rounded-full animate-spin" />
                                </div>
                                <div className="text-center space-y-2">
                                    <p className="text-foreground font-medium">Weaving magic...</p>
                                    <p className="text-muted-foreground text-sm">Generating code & rendering frames</p>
                                </div>
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
                                            <div className="mt-2 p-3 rounded-lg bg-black/50 border border-border/50 overflow-x-auto text-[10px]">
                                                <pre className="text-zinc-400 font-mono">
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
