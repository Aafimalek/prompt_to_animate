import { useState, useEffect, useRef } from 'react';
import { Wand2, ChevronDown, Download, Loader2, Code, Share2, Check, Sparkles, Film, LogIn, Crown, Zap, Lock } from 'lucide-react';
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
    style_pack?: string;
    export_mode?: string;
    interactive_outline?: string;
    voiceover_script?: Record<string, unknown>;
    voiceover_requested_mode?: string;
    voiceover_effective_mode?: string;
    voiceover_fallback_reason?: string;
    interactive_manifest?: Record<string, unknown>;
    quality_report?: Record<string, unknown>;
}

interface UsageInfo {
    tier: string;
    used: number;
    limit: number;
    remaining: number;
    basic_credits: number;
}

interface StyleCatalog {
    default_style: string;
    styles: Record<string, { label?: string; description?: string }>;
}

interface LayoutBox {
    id: string;
    label: string;
    x: number;
    y: number;
    width: number;
    height: number;
}

interface ActiveLayoutPointer {
    id: string;
    mode: 'move' | 'resize';
    startX: number;
    startY: number;
    originX: number;
    originY: number;
    originWidth: number;
    originHeight: number;
}

interface GenerationMeta {
    style_pack?: string;
    export_mode?: string;
    interactive_manifest?: Record<string, unknown> | null;
    interactive_outline?: string;
    voiceover_requested_mode?: string;
    voiceover_effective_mode?: string;
    voiceover_fallback_reason?: string;
}

const PROGRESS_STEPS = [
    { id: 1, label: 'Analyzing Prompt', icon: Sparkles },
    { id: 2, label: 'Composing Scenes', icon: Sparkles },
    { id: 3, label: 'Generating Code', icon: Code },
    { id: 4, label: 'Validating Code', icon: Check },
    { id: 5, label: 'Rendering & Finalizing', icon: Film },
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
    const [styleCatalog, setStyleCatalog] = useState<StyleCatalog | null>(null);
    const [stylePack, setStylePack] = useState('classic_clean');
    const [voiceoverMode, setVoiceoverMode] = useState('none');
    const [voiceoverText, setVoiceoverText] = useState('');
    const [exportMode, setExportMode] = useState('video');
    const [layoutEditsJson, setLayoutEditsJson] = useState('[]');
    const [applyingLayoutEdits, setApplyingLayoutEdits] = useState(false);
    const [layoutEditError, setLayoutEditError] = useState<string | null>(null);
    const [layoutBoxes, setLayoutBoxes] = useState<LayoutBox[]>([]);
    const [activeLayoutPointer, setActiveLayoutPointer] = useState<ActiveLayoutPointer | null>(null);
    const layoutCanvasRef = useRef<HTMLDivElement | null>(null);
    const [layoutPreset, setLayoutPreset] = useState('none');
    const [generationMeta, setGenerationMeta] = useState<GenerationMeta | null>(null);

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
        const loadStylePacks = async () => {
            try {
                const response = await fetch(`${API_BASE_URL}/style-packs`);
                if (!response.ok) return;
                const data: StyleCatalog = await response.json();
                setStyleCatalog(data);
                if (data.default_style) {
                    setStylePack(data.default_style);
                }
            } catch (error) {
                console.error('Failed to load style packs:', error);
            }
        };
        loadStylePacks();
    }, []);

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
        setLayoutEditError(null);
        setGenerationMeta(null);

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
                    clerk_id: isSignedIn ? user?.id : undefined,
                    style_pack: stylePack,
                    voiceover_mode: voiceoverMode,
                    voiceover_text: voiceoverMode === 'none' ? '' : voiceoverText,
                    export_mode: exportMode,
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
                                setGenerationMeta({
                                    style_pack: data.style_pack,
                                    export_mode: data.export_mode,
                                    interactive_manifest: data.interactive_manifest || null,
                                    interactive_outline: data.interactive_outline || '',
                                    voiceover_requested_mode: data.voiceover_requested_mode,
                                    voiceover_effective_mode: data.voiceover_effective_mode,
                                    voiceover_fallback_reason: data.voiceover_fallback_reason,
                                });
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
                        setGenerationMeta({
                            style_pack: data.style_pack,
                            export_mode: data.export_mode,
                            interactive_manifest: data.interactive_manifest || null,
                            interactive_outline: data.interactive_outline || '',
                            voiceover_requested_mode: data.voiceover_requested_mode,
                            voiceover_effective_mode: data.voiceover_effective_mode,
                            voiceover_fallback_reason: data.voiceover_fallback_reason,
                        });
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

    const handleApplyLayoutEdits = async () => {
        if (!code) return;
        setLayoutEditError(null);

        let parsedEdits: unknown;
        try {
            parsedEdits = JSON.parse(layoutEditsJson);
        } catch {
            setLayoutEditError('Layout edits must be valid JSON.');
            return;
        }
        if (!Array.isArray(parsedEdits)) {
            setLayoutEditError('Layout edits must be a JSON array.');
            return;
        }

        setApplyingLayoutEdits(true);
        try {
            const response = await fetch(`${API_BASE_URL}/scene-editor/apply-layout`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    code,
                    length,
                    edits: parsedEdits,
                    resolution,
                    render_preview: true,
                    preview_sections: 3,
                }),
            });

            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error(data.detail || 'Failed to apply layout edits');
            }

            if (typeof data.code === 'string' && data.code.trim()) {
                setCode(data.code);
            }
            if (typeof data.preview_url === 'string' && data.preview_url.trim()) {
                setVideoUrl(data.preview_url);
            }
            if (data.changed === false) {
                setLayoutEditError(
                    'No code changes were produced. Use real object names from the code (for example: title, equation, graph).'
                );
            }
        } catch (err: unknown) {
            setLayoutEditError((err as Error).message || 'Failed to apply layout edits');
        } finally {
            setApplyingLayoutEdits(false);
        }
    };

    const addLayoutBox = () => {
        const nextIndex = layoutBoxes.length + 1;
        setLayoutBoxes((prev) => [
            ...prev,
            {
                id: crypto.randomUUID(),
                label: nextIndex === 1 ? 'title' : `object_${nextIndex}`,
                x: 0.1,
                y: 0.1,
                width: 0.25,
                height: 0.15,
            },
        ]);
    };

    const updateLayoutBoxLabel = (id: string, label: string) => {
        setLayoutBoxes((prev) => prev.map((box) => (box.id === id ? { ...box, label } : box)));
    };

    const exportCanvasEditsToJson = () => {
        const edits = layoutBoxes.map((box) => ({
            object: box.label || box.id,
            action: "reframe_object",
            normalized_box: {
                x: Number(box.x.toFixed(4)),
                y: Number(box.y.toFixed(4)),
                width: Number(box.width.toFixed(4)),
                height: Number(box.height.toFixed(4)),
            },
            instruction: `Keep '${box.label || box.id}' fully visible inside this normalized box`,
        }));
        setLayoutEditsJson(JSON.stringify(edits, null, 2));
    };

    const applyLayoutPreset = () => {
        if (layoutPreset === 'none') return;
        const presets: Record<string, unknown[]> = {
            safe_title_formula: [
                { object: "title", action: "move_to_edge", edge: "UP", buff: 0.4 },
                { object: "equation", action: "move_to_edge", edge: "DOWN", buff: 0.5 },
                { action: "instruction", instruction: "Keep main visual centered and avoid overlap with title/equation." },
            ],
            spread_labels: [
                { action: "instruction", instruction: "Reduce concurrent labels and spread text groups with larger buff values." },
                { action: "instruction", instruction: "Use VGroup(...).arrange(DOWN, buff=0.35+) for stacked labels." },
            ],
            center_focus: [
                { object: "main_visual", action: "reframe_object", normalized_box: { x: 0.2, y: 0.2, width: 0.6, height: 0.6 } },
                { action: "instruction", instruction: "Move secondary annotations near frame edges with safe margins." },
            ],
        };
        const edits = presets[layoutPreset] || [];
        setLayoutEditsJson(JSON.stringify(edits, null, 2));
    };

    const selectedStyleMeta = styleCatalog?.styles?.[stylePack];
    const voiceoverModeHint =
        voiceoverMode === 'none'
            ? 'No narration instructions are sent.'
            : 'Narration chunks are generated/aligned and injected into codegen.';
    const exportModeHint =
        exportMode === 'video'
            ? 'Standard MP4 output.'
            : exportMode === 'interactive'
                ? 'Adds chapter manifest metadata for scrubbing.'
                : 'Adds chapter manifest + slide outline.';

    const beginLayoutPointer = (
        event: React.MouseEvent,
        box: LayoutBox,
        mode: 'move' | 'resize'
    ) => {
        event.preventDefault();
        event.stopPropagation();
        setActiveLayoutPointer({
            id: box.id,
            mode,
            startX: event.clientX,
            startY: event.clientY,
            originX: box.x,
            originY: box.y,
            originWidth: box.width,
            originHeight: box.height,
        });
    };

    useEffect(() => {
        if (!activeLayoutPointer) return;

        const clamp = (value: number, min: number, max: number) => Math.max(min, Math.min(max, value));

        const onMouseMove = (event: MouseEvent) => {
            const canvas = layoutCanvasRef.current;
            if (!canvas) return;
            const rect = canvas.getBoundingClientRect();
            if (rect.width <= 0 || rect.height <= 0) return;

            const dx = (event.clientX - activeLayoutPointer.startX) / rect.width;
            const dy = (event.clientY - activeLayoutPointer.startY) / rect.height;

            setLayoutBoxes((prev) =>
                prev.map((box) => {
                    if (box.id !== activeLayoutPointer.id) return box;
                    if (activeLayoutPointer.mode === 'move') {
                        const nextX = clamp(activeLayoutPointer.originX + dx, 0, 1 - box.width);
                        const nextY = clamp(activeLayoutPointer.originY + dy, 0, 1 - box.height);
                        return { ...box, x: nextX, y: nextY };
                    }
                    const nextWidth = clamp(activeLayoutPointer.originWidth + dx, 0.08, 1 - box.x);
                    const nextHeight = clamp(activeLayoutPointer.originHeight + dy, 0.06, 1 - box.y);
                    return { ...box, width: nextWidth, height: nextHeight };
                })
            );
        };

        const onMouseUp = () => {
            setActiveLayoutPointer(null);
        };

        window.addEventListener('mousemove', onMouseMove);
        window.addEventListener('mouseup', onMouseUp);
        return () => {
            window.removeEventListener('mousemove', onMouseMove);
            window.removeEventListener('mouseup', onMouseUp);
        };
    }, [activeLayoutPointer]);

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

                        <div className="flex flex-wrap items-center gap-2 border-t border-zinc-100 dark:border-zinc-800 pt-2 md:pt-3">
                            <select
                                value={stylePack}
                                onChange={(e) => setStylePack(e.target.value)}
                                className="px-3 py-2 rounded-lg text-xs bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 text-zinc-800 dark:text-zinc-100"
                            >
                                {Object.entries(styleCatalog?.styles || {}).map(([id, meta]) => (
                                    <option key={id} value={id}>
                                        {meta.label || id}
                                    </option>
                                ))}
                                {!styleCatalog && <option value="classic_clean">Classic Clean</option>}
                            </select>

                            <select
                                value={voiceoverMode}
                                onChange={(e) => setVoiceoverMode(e.target.value)}
                                className="px-3 py-2 rounded-lg text-xs bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 text-zinc-800 dark:text-zinc-100"
                            >
                                <option value="none">Voiceover: Off</option>
                                <option value="scripted">Voiceover: Scripted</option>
                            </select>

                            <select
                                value={exportMode}
                                onChange={(e) => setExportMode(e.target.value)}
                                className="px-3 py-2 rounded-lg text-xs bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 text-zinc-800 dark:text-zinc-100"
                            >
                                <option value="video">Export: Video</option>
                                <option value="interactive">Export: Interactive</option>
                                <option value="slides">Export: Slides</option>
                            </select>
                        </div>

                        {voiceoverMode !== 'none' && (
                            <input
                                value={voiceoverText}
                                onChange={(e) => setVoiceoverText(e.target.value)}
                                placeholder="Optional narration script..."
                                className="w-full px-3 py-2 rounded-lg text-xs bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 text-zinc-800 dark:text-zinc-100"
                            />
                        )}

                        <div className="grid grid-cols-1 md:grid-cols-3 gap-2 text-[11px]">
                            <div className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-zinc-50/80 dark:bg-zinc-900/60 px-2.5 py-2">
                                <p className="font-semibold text-zinc-700 dark:text-zinc-200">Style Mode</p>
                                <p className="text-zinc-500 dark:text-zinc-400 mt-0.5">
                                    {selectedStyleMeta?.description || 'Applies visual tokens (palette, spacing, motion).'}
                                </p>
                            </div>
                            <div className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-zinc-50/80 dark:bg-zinc-900/60 px-2.5 py-2">
                                <p className="font-semibold text-zinc-700 dark:text-zinc-200">Voiceover Mode</p>
                                <p className="text-zinc-500 dark:text-zinc-400 mt-0.5">{voiceoverModeHint}</p>
                            </div>
                            <div className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-zinc-50/80 dark:bg-zinc-900/60 px-2.5 py-2">
                                <p className="font-semibold text-zinc-700 dark:text-zinc-200">Export Mode</p>
                                <p className="text-zinc-500 dark:text-zinc-400 mt-0.5">{exportModeHint}</p>
                            </div>
                        </div>

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
                                    key={`${currentProgress?.step}-${currentProgress?.status}`}
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    className="text-center text-sm text-muted-foreground mt-4"
                                >
                                    {currentProgress?.status === "selecting_style" && "Selecting a style pack..."}
                                    {currentProgress?.status === "voiceover_fallback" && "Voiceover plugin unavailable, falling back safely..."}
                                    {currentProgress?.status === "retrieving_memory" && "Retrieving high-quality memory examples..."}
                                    {currentProgress?.step === 2 && "Composing a scene-by-scene plan..."}
                                    {currentProgress?.status === "candidate_generating" && "Generating multiple code candidates..."}
                                    {currentProgress?.status === "candidate_scoring" && "Scoring candidates with reward model..."}
                                    {currentProgress?.step === 3 && "Generating Manim code from the plan..."}
                                    {currentProgress?.step === 4 && currentProgress?.status === "repairing" && "Repairing code issues automatically..."}
                                    {currentProgress?.step === 4 && currentProgress?.status === "quality_checking" && "Running visual quality gate..."}
                                    {currentProgress?.step === 4 && currentProgress?.status === "quality_repairing" && "Applying visual quality repair..."}
                                    {currentProgress?.step === 4 && currentProgress?.status === "repairing_runtime" && "Repairing runtime failure..."}
                                    {currentProgress?.step === 4 && !["repairing", "quality_checking", "quality_repairing", "repairing_runtime", "candidate_scoring"].includes(currentProgress?.status || "") && "Running strict code validation..."}
                                    {currentProgress?.step === 5 && currentProgress?.status === "rendering" && "Rendering animation frames..."}
                                    {currentProgress?.step === 5 && currentProgress?.status === "finalizing" && "Uploading and finalizing your video..."}
                                    {(!currentProgress || currentProgress.step <= 1) && "Preparing generation pipeline..."}
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

                                {generationMeta && (
                                    <div className="px-4 pt-1 space-y-2">
                                        <div className="flex flex-wrap items-center gap-2 text-[11px]">
                                            <span className="px-2 py-1 rounded-full bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-200">
                                                Style: {generationMeta.style_pack || stylePack}
                                            </span>
                                            <span className="px-2 py-1 rounded-full bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-200">
                                                Export: {generationMeta.export_mode || exportMode}
                                            </span>
                                            <span className="px-2 py-1 rounded-full bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-200">
                                                Voiceover: {generationMeta.voiceover_effective_mode || 'none'}
                                            </span>
                                        </div>
                                        {generationMeta.voiceover_fallback_reason && (
                                            <p className="text-xs text-amber-600 dark:text-amber-400">
                                                {generationMeta.voiceover_fallback_reason}
                                            </p>
                                        )}
                                        {generationMeta.interactive_outline && (
                                            <details className="group">
                                                <summary className="cursor-pointer list-none flex items-center space-x-2 text-muted-foreground hover:text-foreground transition-colors text-xs font-medium content-none">
                                                    <ChevronDown className="w-3 h-3 group-open:rotate-180 transition-transform" />
                                                    <span>View Export Outline</span>
                                                </summary>
                                                <div className="mt-2 p-3 rounded-lg bg-zinc-900 dark:bg-zinc-950 border border-zinc-700 dark:border-zinc-800 overflow-x-auto">
                                                    <pre className="text-zinc-200 font-mono text-[11px] leading-relaxed whitespace-pre-wrap">
                                                        {generationMeta.interactive_outline}
                                                    </pre>
                                                </div>
                                            </details>
                                        )}
                                    </div>
                                )}

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
                                        <details className="group mt-3">
                                            <summary className="cursor-pointer list-none flex items-center space-x-2 text-muted-foreground hover:text-foreground transition-colors text-xs font-medium content-none">
                                                <ChevronDown className="w-3 h-3 group-open:rotate-180 transition-transform" />
                                                <span>Scene Editor (Layout JSON)</span>
                                            </summary>
                                            <div className="mt-2 space-y-2">
                                                <div className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-zinc-50/80 dark:bg-zinc-900/60 px-3 py-2 text-[11px] text-zinc-600 dark:text-zinc-300">
                                                    Drag boxes to define target layout zones, then click <span className="font-semibold">Use Canvas in JSON</span>.
                                                    Use labels that match actual objects in code (`title`, `equation`, `graph`) for better edits.
                                                </div>
                                                <div className="flex flex-wrap items-center gap-2">
                                                    <select
                                                        value={layoutPreset}
                                                        onChange={(e) => setLayoutPreset(e.target.value)}
                                                        className="px-3 py-1.5 rounded-md text-[11px] bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 text-zinc-800 dark:text-zinc-100"
                                                    >
                                                        <option value="none">Preset: None</option>
                                                        <option value="safe_title_formula">Preset: Title + Formula Safe Zones</option>
                                                        <option value="spread_labels">Preset: Spread Dense Labels</option>
                                                        <option value="center_focus">Preset: Center Main Focus</option>
                                                    </select>
                                                    <button
                                                        onClick={applyLayoutPreset}
                                                        disabled={layoutPreset === 'none'}
                                                        className={cn(
                                                            "px-3 py-1.5 rounded-md text-[11px]",
                                                            layoutPreset === 'none'
                                                                ? "bg-zinc-800/50 text-zinc-500 cursor-not-allowed"
                                                                : "bg-zinc-800 text-zinc-200 hover:bg-zinc-700"
                                                        )}
                                                    >
                                                        Insert Preset JSON
                                                    </button>
                                                </div>
                                                <div className="p-3 rounded-lg border border-zinc-700/80 bg-zinc-900/60 space-y-2">
                                                    <div
                                                        ref={layoutCanvasRef}
                                                        className="relative aspect-video rounded-md border border-zinc-700 bg-zinc-950 overflow-hidden"
                                                    >
                                                        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(255,255,255,0.08),transparent_65%)]" />
                                                        {layoutBoxes.map((box) => (
                                                            <div
                                                                key={box.id}
                                                                className="absolute border border-orange-400/90 bg-orange-500/10 cursor-move"
                                                                style={{
                                                                    left: `${box.x * 100}%`,
                                                                    top: `${box.y * 100}%`,
                                                                    width: `${box.width * 100}%`,
                                                                    height: `${box.height * 100}%`,
                                                                }}
                                                                onMouseDown={(event) => beginLayoutPointer(event, box, 'move')}
                                                            >
                                                                <div className="absolute top-0 left-0 right-0 px-1 py-[2px] text-[10px] bg-orange-500/70 text-white truncate">
                                                                    {box.label || box.id}
                                                                </div>
                                                                <div
                                                                    className="absolute right-0 bottom-0 w-3 h-3 bg-orange-400 cursor-se-resize"
                                                                    onMouseDown={(event) => beginLayoutPointer(event, box, 'resize')}
                                                                />
                                                            </div>
                                                        ))}
                                                    </div>
                                                    {layoutBoxes.length > 0 && (
                                                        <div className="space-y-1">
                                                            {layoutBoxes.map((box) => (
                                                                <input
                                                                    key={box.id}
                                                                    value={box.label}
                                                                    onChange={(event) => updateLayoutBoxLabel(box.id, event.target.value)}
                                                                    className="w-full px-2 py-1 rounded bg-zinc-950 border border-zinc-700 text-[11px] text-zinc-200"
                                                                    placeholder="Object label"
                                                                />
                                                            ))}
                                                        </div>
                                                    )}
                                                    <div className="flex flex-wrap gap-2">
                                                        <button
                                                            onClick={addLayoutBox}
                                                            className="px-2 py-1 rounded-md text-[11px] bg-zinc-800 text-zinc-200 hover:bg-zinc-700"
                                                        >
                                                            Add Box
                                                        </button>
                                                        <button
                                                            onClick={exportCanvasEditsToJson}
                                                            disabled={layoutBoxes.length === 0}
                                                            className={cn(
                                                                "px-2 py-1 rounded-md text-[11px]",
                                                                layoutBoxes.length === 0
                                                                    ? "bg-zinc-800/50 text-zinc-500 cursor-not-allowed"
                                                                    : "bg-zinc-800 text-zinc-200 hover:bg-zinc-700"
                                                            )}
                                                        >
                                                            Use Canvas in JSON
                                                        </button>
                                                        <button
                                                            onClick={() => setLayoutBoxes([])}
                                                            disabled={layoutBoxes.length === 0}
                                                            className={cn(
                                                                "px-2 py-1 rounded-md text-[11px]",
                                                                layoutBoxes.length === 0
                                                                    ? "bg-zinc-800/50 text-zinc-500 cursor-not-allowed"
                                                                    : "bg-zinc-800 text-zinc-200 hover:bg-zinc-700"
                                                            )}
                                                        >
                                                            Clear
                                                        </button>
                                                    </div>
                                                </div>
                                                <textarea
                                                    value={layoutEditsJson}
                                                    onChange={(e) => setLayoutEditsJson(e.target.value)}
                                                    className="w-full min-h-[120px] p-3 rounded-lg bg-zinc-900 dark:bg-zinc-950 border border-zinc-700 dark:border-zinc-800 text-emerald-300 font-mono text-xs"
                                                    placeholder='[{"scene":"Scene 1","object":"title","action":"move","to_edge":"UP","buff":0.5}]'
                                                />
                                                {layoutEditError && (
                                                    <p className="text-xs text-red-400">{layoutEditError}</p>
                                                )}
                                                <button
                                                    onClick={handleApplyLayoutEdits}
                                                    disabled={applyingLayoutEdits}
                                                    className={cn(
                                                        "px-3 py-2 rounded-md text-xs font-medium transition-colors",
                                                        applyingLayoutEdits
                                                            ? "bg-zinc-700 text-zinc-300 cursor-not-allowed"
                                                            : "bg-orange-500 text-white hover:bg-orange-600"
                                                    )}
                                                >
                                                    {applyingLayoutEdits ? 'Applying + Previewing...' : 'Apply Layout Edits'}
                                                </button>
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
