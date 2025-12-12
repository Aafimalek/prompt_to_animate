import { Plus, MessageSquare, Trash2, X, PanelLeftClose, PanelLeftOpen, LogIn, UserPlus, Loader2, Crown } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { SignedIn, SignedOut, SignInButton, SignUpButton, UserButton } from '@clerk/nextjs';

export interface HistoryItem {
    id: string;
    prompt: string;
    timestamp: number;
    videoUrl?: string;
    code?: string;
}

interface SidebarProps {
    history: HistoryItem[];
    onSelect: (item: HistoryItem) => void;
    onNew: () => void;
    onDelete: (id: string, e: React.MouseEvent) => void;
    isOpen: boolean; // Mobile open state
    onClose: () => void; // Mobile close
    isDesktopCollapsed: boolean;
    onDesktopToggle: () => void;
    isLoading?: boolean; // Loading state for history
    onUpgradeClick?: () => void; // Open pricing modal
}

export function Sidebar({
    history,
    onSelect,
    onNew,
    onDelete,
    isOpen,
    onClose,
    isDesktopCollapsed,
    onDesktopToggle,
    isLoading = false,
    onUpgradeClick
}: SidebarProps) {
    return (
        <>
            {/* Mobile Overlay */}
            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={onClose}
                        className="fixed inset-0 bg-black/60 z-40 md:hidden backdrop-blur-sm"
                    />
                )}
            </AnimatePresence>

            {/* Sidebar Container */}
            <motion.div
                layout
                className={cn(
                    "fixed top-0 left-0 h-full z-50 flex flex-col transition-all duration-300 backdrop-blur-2xl",
                    // Light mode: frosted glass, Dark mode: deep glass
                    "bg-white/80 dark:bg-zinc-900/80",
                    // Borders
                    "border-r border-white/20 dark:border-zinc-800/50",
                    // Rings for edge definition
                    "ring-1 ring-black/5 dark:ring-white/5",
                    // Shadow
                    "shadow-2xl shadow-zinc-200/50 dark:shadow-black/50",
                    // Mobile styles
                    isOpen ? "translate-x-0 w-72" : "-translate-x-full w-72",
                    // Desktop styles
                    "md:translate-x-0 md:relative",
                    isDesktopCollapsed ? "md:w-20" : "md:w-72"
                )}
            >
                {/* Header */}
                <div className={cn("p-4 flex items-center h-16", isDesktopCollapsed ? "justify-center" : "justify-between")}>
                    <div className="flex items-center space-x-2 overflow-hidden h-8">
                        {!isDesktopCollapsed && (
                            <span className="font-bold text-xl tracking-tight select-none font-logo bg-gradient-to-r from-orange-500 to-orange-600 bg-clip-text text-transparent animate-in fade-in slide-in-from-left-2 duration-500">
                                Manimancer
                            </span>
                        )}
                    </div>

                    {/* Mobile Close */}
                    <button onClick={onClose} className="md:hidden p-2 text-muted-foreground hover:text-foreground transition-colors">
                        <X className="w-5 h-5" />
                    </button>

                    {/* Desktop Toggle (Only visible when NOT collapsed) */}
                    {!isDesktopCollapsed && (
                        <button
                            onClick={onDesktopToggle}
                            className="hidden md:block text-zinc-400 hover:text-orange-500 hover:bg-orange-500/10 p-2 rounded-lg transition-all"
                            title="Collapse Sidebar"
                        >
                            <PanelLeftClose className="w-5 h-5" />
                        </button>
                    )}

                </div>

                {/* Desktop Toggle (Only visible when collapsed) */}
                {isDesktopCollapsed && (
                    <div className="hidden md:flex justify-center py-4">
                        <button
                            onClick={onDesktopToggle}
                            className="text-zinc-400 hover:text-orange-500 hover:bg-orange-500/10 p-2 rounded-lg transition-all"
                            title="Expand Sidebar"
                        >
                            <PanelLeftOpen className="w-5 h-5" />
                        </button>
                    </div>
                )}


                <div className="px-3 py-2">
                    <button
                        onClick={() => {
                            onNew();
                            if (window.innerWidth < 768) onClose();
                        }}
                        className={cn(
                            "w-full flex items-center justify-center space-x-2 transition-all duration-200 rounded-xl font-medium active:scale-95 group",
                            // Standard styling: White in light, Dark in dark
                            "bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100",
                            // Orange Hover Effect
                            "hover:border-orange-500 hover:text-orange-600 dark:hover:text-orange-400 hover:shadow-orange-500/10",
                            "shadow-md border border-zinc-200 dark:border-zinc-700",
                            isDesktopCollapsed ? "p-3" : "py-2.5 px-4"
                        )}
                        title="New Project"
                    >
                        <Plus className="w-5 h-5 group-hover:text-orange-600 dark:group-hover:text-orange-400 transition-colors" />
                        {!isDesktopCollapsed && <span>New Project</span>}
                    </button>
                </div>

                {/* History List */}
                <div className="flex-1 overflow-y-auto px-3 py-2 space-y-1 scrollbar-thin scrollbar-thumb-muted scrollbar-track-transparent">
                    {isLoading && !isDesktopCollapsed && (
                        <div className="flex flex-col items-center justify-center py-10 text-muted-foreground">
                            <Loader2 className="w-6 h-6 animate-spin text-orange-500 mb-2" />
                            <span className="text-sm">Loading history...</span>
                        </div>
                    )}

                    {!isLoading && history.length === 0 && !isDesktopCollapsed && (
                        <div className="text-center text-muted-foreground py-10 px-4 text-sm">
                            Create a new project to get started.
                        </div>
                    )}

                    <div className={cn("text-xs font-semibold text-muted-foreground mb-2 px-2 uppercase tracking-wider", isDesktopCollapsed ? "hidden" : "block")}>
                        Recents
                    </div>

                    {history.map((item) => (
                        <button
                            key={item.id}
                            onClick={() => {
                                onSelect(item);
                                if (window.innerWidth < 768) onClose();
                            }}
                            className={cn(
                                "w-full group flex items-center rounded-lg transition-all text-left relative",
                                // Orange Hover Effect
                                "hover:bg-orange-500/10 hover:text-orange-700 dark:hover:text-orange-300",
                                isDesktopCollapsed ? "justify-center p-3" : "px-3 py-2.5 space-x-3"
                            )}
                            title={isDesktopCollapsed ? item.prompt : undefined}
                        >
                            <MessageSquare className="w-4 h-4 text-zinc-400 group-hover:text-orange-500 transition-colors" />

                            {!isDesktopCollapsed && (
                                <>
                                    <div className="flex-1 overflow-hidden">
                                        <p className="text-sm font-medium truncate pr-6 leading-tight group-hover:text-orange-600 dark:group-hover:text-orange-400 transition-colors">
                                            {item.prompt}
                                        </p>
                                        <p className="text-[10px] text-zinc-500 group-hover:text-orange-500/70 mt-0.5">
                                            {new Date(item.timestamp).toLocaleDateString()}
                                        </p>
                                    </div>
                                    <div
                                        onClick={(e) => onDelete(item.id, e)}
                                        className="absolute right-2 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 p-1.5 hover:bg-orange-500/20 rounded-md text-zinc-400 hover:text-orange-600 dark:hover:text-orange-400 transition-all"
                                    >
                                        <Trash2 className="w-3.5 h-3.5" />
                                    </div>
                                </>
                            )}
                        </button>
                    ))}
                </div>

                {/* Footer - Auth Section */}
                <div className="p-4 border-t border-border">
                    {/* Signed Out State */}
                    <SignedOut>
                        <div className={cn(
                            "flex gap-2",
                            isDesktopCollapsed ? "flex-col items-center" : "flex-col"
                        )}>
                            <SignInButton mode="modal">
                                <button
                                    className={cn(
                                        "flex items-center justify-center gap-2 rounded-xl font-medium transition-all duration-200 active:scale-95",
                                        "bg-gradient-to-r from-orange-500 to-orange-600 text-white",
                                        "hover:from-orange-600 hover:to-orange-700",
                                        "shadow-md shadow-orange-500/20",
                                        isDesktopCollapsed ? "p-3" : "py-2.5 px-4 w-full"
                                    )}
                                    title="Sign In"
                                >
                                    <LogIn className="w-4 h-4" />
                                    {!isDesktopCollapsed && <span>Sign In</span>}
                                </button>
                            </SignInButton>
                            <SignUpButton mode="modal">
                                <button
                                    className={cn(
                                        "flex items-center justify-center gap-2 rounded-xl font-medium transition-all duration-200 active:scale-95",
                                        "bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100",
                                        "hover:border-orange-500 hover:text-orange-600 dark:hover:text-orange-400",
                                        "shadow-md border border-zinc-200 dark:border-zinc-700",
                                        isDesktopCollapsed ? "p-3" : "py-2.5 px-4 w-full"
                                    )}
                                    title="Sign Up"
                                >
                                    <UserPlus className="w-4 h-4" />
                                    {!isDesktopCollapsed && <span>Sign Up</span>}
                                </button>
                            </SignUpButton>
                        </div>
                    </SignedOut>

                    {/* Signed In State */}
                    <SignedIn>
                        <div className={cn(
                            "flex flex-col gap-3",
                            isDesktopCollapsed ? "items-center" : ""
                        )}>
                            {/* Upgrade Button */}
                            <button
                                onClick={onUpgradeClick}
                                className={cn(
                                    "flex items-center justify-center gap-2 rounded-xl font-medium transition-all duration-200 active:scale-95",
                                    "bg-gradient-to-r from-orange-500 to-orange-600 text-white",
                                    "hover:from-orange-600 hover:to-orange-700",
                                    "shadow-md shadow-orange-500/20",
                                    isDesktopCollapsed ? "p-3" : "py-2.5 px-4 w-full"
                                )}
                                title="Upgrade Plan"
                            >
                                <Crown className="w-4 h-4" />
                                {!isDesktopCollapsed && <span>Upgrade</span>}
                            </button>

                            {/* User Account */}
                            <div className={cn(
                                "flex items-center rounded-lg",
                                isDesktopCollapsed ? "justify-center p-2" : "space-x-3 px-2 py-2"
                            )}>
                                <UserButton
                                    appearance={{
                                        elements: {
                                            avatarBox: "w-8 h-8",
                                            userButtonPopoverCard: "bg-zinc-900 border border-zinc-800",
                                            userButtonPopoverActionButton: "hover:bg-zinc-800",
                                            userButtonPopoverActionButtonText: "text-zinc-100",
                                            userButtonPopoverFooter: "hidden"
                                        }
                                    }}
                                />
                                {!isDesktopCollapsed && (
                                    <div className="flex-1 overflow-hidden">
                                        <p className="text-sm font-medium text-foreground truncate">Account</p>
                                        <p className="text-xs text-muted-foreground truncate">Manage profile</p>
                                    </div>
                                )}
                            </div>
                        </div>
                    </SignedIn>
                </div>
            </motion.div>
        </>
    );
}
