"use client"

import { useState, useEffect } from "react"
import { useTheme } from "next-themes"
import { Moon, Sun, Menu } from "lucide-react"
import { motion } from "framer-motion"
import { cn } from "@/lib/utils"

interface NavbarProps {
    onMenuClick?: () => void
    isDesktopCollapsed?: boolean
}

export function Navbar({ onMenuClick, isDesktopCollapsed = true }: NavbarProps) {
    const { theme, setTheme } = useTheme()
    const [mounted, setMounted] = useState(false)

    useEffect(() => {
        setMounted(true)
    }, [])

    return (
        <motion.nav
            initial={{ y: -20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.5 }}
            className={cn(
                "fixed top-4 z-50 pointer-events-auto transition-all duration-300",
                isDesktopCollapsed
                    ? "left-4 right-4 md:left-24 md:right-4"
                    : "left-4 right-4 md:left-[304px] md:right-4"
            )}
        >
            <div className="max-w-fit mx-auto flex items-center space-x-3 bg-white/70 dark:bg-zinc-900/70 backdrop-blur-2xl border border-white/20 dark:border-zinc-800/50 rounded-full shadow-2xl shadow-zinc-200/50 dark:shadow-black/40 px-4 py-2.5 ring-1 ring-black/5 dark:ring-white/10">

                {/* Mobile Menu */}
                <button
                    onClick={onMenuClick}
                    className="md:hidden p-2 text-zinc-600 dark:text-zinc-400 hover:text-orange-500 hover:bg-orange-500/10 rounded-full transition-all"
                >
                    <Menu className="w-4 h-4" />
                </button>

                {/* Brand - Text with Orange Gradient */}
                <span className="font-bold text-sm tracking-tight bg-gradient-to-r from-orange-500 to-orange-600 bg-clip-text text-transparent px-1">Manimancer</span>

                {/* Divider */}
                <div className="w-px h-5 bg-zinc-300 dark:bg-zinc-700" />

                {/* Theme Toggle */}
                {mounted && (
                    <motion.button
                        whileHover={{ scale: 1.1 }}
                        whileTap={{ scale: 0.9 }}
                        onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
                        className="p-2 rounded-full bg-orange-500/10 hover:bg-orange-500/20 text-orange-600 dark:text-orange-400 transition-all duration-300 border border-orange-500/30"
                        title="Toggle Theme"
                    >
                        {theme === "dark" ? (
                            <Moon className="w-4 h-4" />
                        ) : (
                            <Sun className="w-4 h-4" />
                        )}
                    </motion.button>
                )}
            </div>
        </motion.nav>
    )
}
