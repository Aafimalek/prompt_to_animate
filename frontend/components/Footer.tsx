"use client"

import { motion } from "framer-motion"
import { Github, Twitter, Heart } from "lucide-react"
import { cn } from "@/lib/utils"

interface FooterProps {
    isDesktopCollapsed?: boolean
}

export function Footer({ isDesktopCollapsed = true }: FooterProps) {
    return (
        <motion.footer
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className={cn(
                "fixed bottom-4 z-50 pointer-events-none transition-all duration-300",
                isDesktopCollapsed
                    ? "left-4 right-4 md:left-24 md:right-4"
                    : "left-4 right-4 md:left-[304px] md:right-4"
            )}
        >
            <div className="max-w-fit mx-auto flex items-center justify-center space-x-4 bg-white/70 dark:bg-zinc-900/70 backdrop-blur-2xl border border-white/20 dark:border-zinc-800/50 rounded-full shadow-2xl shadow-zinc-200/50 dark:shadow-black/40 px-6 py-2.5 pointer-events-auto ring-1 ring-black/5 dark:ring-white/10">

                {/* Copyright */}
                <span className="text-sm text-zinc-600 dark:text-zinc-400">© {new Date().getFullYear()} <span className="text-orange-500 font-medium">Manimancer</span></span>

                <span className="text-zinc-300 dark:text-zinc-700">•</span>

                {/* Made with love */}
                <div className="flex items-center space-x-1.5 text-sm text-zinc-600 dark:text-zinc-400">
                    <span>Made with</span>
                    <Heart className="w-3.5 h-3.5 text-orange-500 fill-orange-500" />
                </div>

                <span className="text-zinc-300 dark:text-zinc-700">•</span>

                {/* Social Icons */}
                <div className="flex items-center space-x-1">
                    <a href="https://github.com/Aafimalek" target="_blank" rel="noopener noreferrer" className="p-1.5 text-zinc-500 hover:text-orange-500 hover:bg-orange-500/10 rounded-lg transition-all">
                        <Github className="w-4 h-4" />
                    </a>
                    <a href="https://x.com/aafimalek2032" target="_blank" rel="noopener noreferrer" className="p-1.5 text-zinc-500 hover:text-orange-500 hover:bg-orange-500/10 rounded-lg transition-all">
                        <Twitter className="w-4 h-4" />
                    </a>
                </div>
            </div>
        </motion.footer>
    )
}
