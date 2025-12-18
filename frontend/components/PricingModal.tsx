"use client";

import { X, Crown, Check, Zap, Sparkles, Star } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { useUser } from '@clerk/nextjs';

interface PricingModalProps {
    isOpen: boolean;
    onClose: () => void;
}

interface PricingTier {
    name: string;
    price: string;
    period: string;
    description: string;
    features: string[];
    icon: React.ComponentType<{ className?: string }>;
    popular?: boolean;
    buttonText: string;
    buttonStyle: 'default' | 'gradient' | 'outline';
    productId?: string;
}

const pricingTiers: PricingTier[] = [
    {
        name: "Free",
        price: "$0",
        period: "",
        description: "Perfect for getting started",
        icon: Sparkles,
        features: [
            "5 videos per month",
            "720p @ 30 FPS",
            "Max 30 seconds",
            "Basic support"
        ],
        buttonText: "Current Plan",
        buttonStyle: 'outline'
    },
    {
        name: "Basic",
        price: "$3",
        period: "one-time",
        description: "Great for occasional projects",
        icon: Zap,
        productId: "pdt_9pgk0uVBWpT13GL0Mfqbc",  // LIVE: Manimancer Basic
        features: [
            "5 videos at 1080p 60fps",
            "OR 2 videos at 4K 60fps",
            "Up to 5 min length",
            "Priority rendering"
        ],
        buttonText: "Get Started",
        buttonStyle: 'default'
    },
    {
        name: "Pro",
        price: "$20",
        period: "/month",
        description: "For power users",
        icon: Crown,
        popular: true,
        productId: "pdt_hf3NUNKCCKbDR5HKinOXI",  // LIVE: Manimancer Pro
        features: [
            "50 videos per month",
            "4K @ 60 FPS quality",
            "Up to 5 min length",
            "Priority processing",
            "Premium support"
        ],
        buttonText: "Upgrade to Pro",
        buttonStyle: 'gradient'
    }
];

export function PricingModal({ isOpen, onClose }: PricingModalProps) {
    const { user } = useUser();

    return (
        <AnimatePresence>
            {isOpen && (
                <>
                    {/* Backdrop */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={onClose}
                        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[100]"
                    />

                    {/* Modal */}
                    <motion.div
                        initial={{ opacity: 0, scale: 0.95, y: 10 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.95, y: 10 }}
                        transition={{ type: "spring", duration: 0.4 }}
                        className="fixed inset-0 z-[101] flex items-center justify-center p-3 sm:p-4 md:p-8 overflow-y-auto"
                    >
                        <div className={cn(
                            "w-full max-w-4xl relative my-auto",
                            "bg-white/95 dark:bg-zinc-900/95 backdrop-blur-2xl",
                            "border border-white/20 dark:border-zinc-800/50",
                            "rounded-xl sm:rounded-2xl shadow-2xl shadow-zinc-200/50 dark:shadow-black/50",
                            "ring-1 ring-black/5 dark:ring-white/5",
                            "p-4 sm:p-5 md:p-8 max-h-[95vh] overflow-y-auto"
                        )}>
                            {/* Close Button */}
                            <button
                                onClick={onClose}
                                className="absolute top-3 right-3 p-2 rounded-full hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-500 hover:text-orange-500 transition-all z-10"
                            >
                                <X className="w-5 h-5" />
                            </button>

                            {/* Header - Compact */}
                            <div className="text-center mb-4 sm:mb-6">
                                <div className="flex items-center justify-center gap-2 sm:gap-3 mb-2">
                                    <div className="w-8 sm:w-10 h-8 sm:h-10 rounded-lg sm:rounded-xl bg-gradient-to-br from-orange-500 to-orange-600 shadow-lg shadow-orange-500/30 flex items-center justify-center">
                                        <Crown className="w-4 sm:w-5 h-4 sm:h-5 text-white" />
                                    </div>
                                    <h2 className="text-xl sm:text-2xl md:text-3xl font-bold tracking-tight bg-gradient-to-r from-orange-500 via-orange-600 to-orange-500 bg-clip-text text-transparent">
                                        Choose Your Plan
                                    </h2>
                                </div>
                                <p className="text-xs sm:text-sm text-muted-foreground">
                                    Unlock the full power of Manimancer
                                </p>
                            </div>

                            {/* Pricing Cards - Compact Grid */}
                            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 sm:gap-4">
                                {pricingTiers.map((tier, index) => (
                                    <motion.div
                                        key={tier.name}
                                        initial={{ opacity: 0, y: 15 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        transition={{ delay: 0.05 * index + 0.1 }}
                                        className={cn(
                                            "relative flex flex-col rounded-xl p-4 transition-all duration-300",
                                            "border-2",
                                            tier.popular
                                                ? "border-orange-500 bg-gradient-to-b from-orange-500/10 to-transparent"
                                                : "border-zinc-200 dark:border-zinc-700 hover:border-orange-500/50",
                                            "group hover:shadow-lg hover:shadow-orange-500/10"
                                        )}
                                    >
                                        {/* Popular Badge */}
                                        {tier.popular && (
                                            <div className="absolute -top-2.5 left-1/2 -translate-x-1/2">
                                                <span className="px-3 py-0.5 rounded-full text-[10px] font-bold bg-gradient-to-r from-orange-500 to-orange-600 text-white shadow-md shadow-orange-500/30">
                                                    POPULAR
                                                </span>
                                            </div>
                                        )}

                                        {/* Tier Icon & Name */}
                                        <div className="flex items-center gap-3 mb-3">
                                            <div className={cn(
                                                "w-9 h-9 rounded-lg flex items-center justify-center shrink-0",
                                                tier.popular
                                                    ? "bg-gradient-to-br from-orange-500 to-orange-600 text-white"
                                                    : "bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 group-hover:text-orange-500"
                                            )}>
                                                <tier.icon className="w-4 h-4" />
                                            </div>
                                            <div>
                                                <h3 className="text-lg font-bold text-foreground leading-none">{tier.name}</h3>
                                                <p className="text-xs text-muted-foreground mt-0.5">{tier.description}</p>
                                            </div>
                                        </div>

                                        {/* Price */}
                                        <div className="flex items-baseline gap-1 mb-3">
                                            <span className="text-3xl font-bold text-foreground">{tier.price}</span>
                                            {tier.period && (
                                                <span className="text-muted-foreground text-xs">{tier.period}</span>
                                            )}
                                        </div>

                                        {/* Features - Compact */}
                                        <ul className="space-y-1.5 mb-4 flex-1">
                                            {tier.features.map((feature, i) => (
                                                <li key={i} className="flex items-center gap-2">
                                                    <Check className={cn(
                                                        "w-3.5 h-3.5 shrink-0",
                                                        tier.popular ? "text-orange-500" : "text-green-500"
                                                    )} />
                                                    <span className="text-xs text-foreground">{feature}</span>
                                                </li>
                                            ))}
                                        </ul>

                                        {/* CTA Button */}
                                        <button
                                            onClick={async () => {
                                                if (tier.productId && user?.id) {
                                                    try {
                                                        // Save product info for post-payment detection
                                                        sessionStorage.setItem('last_selected_product', tier.name.toLowerCase());

                                                        const response = await fetch(
                                                            `/api/checkout?productId=${tier.productId}&metadata[clerk_id]=${user.id}`
                                                        );
                                                        const data = await response.json();
                                                        if (data.checkout_url) {
                                                            window.location.href = data.checkout_url;
                                                        }
                                                    } catch (error) {
                                                        console.error('Checkout error:', error);
                                                    }
                                                }
                                            }}
                                            className={cn(
                                                "w-full py-2 px-3 rounded-lg text-sm font-medium transition-all duration-200 flex items-center justify-center gap-2",
                                                tier.buttonStyle === 'gradient' && [
                                                    "bg-gradient-to-r from-orange-500 to-orange-600 text-white",
                                                    "hover:from-orange-600 hover:to-orange-700",
                                                    "shadow-md shadow-orange-500/30",
                                                    "active:scale-95"
                                                ],
                                                tier.buttonStyle === 'default' && [
                                                    "bg-zinc-900 dark:bg-white text-white dark:text-zinc-900",
                                                    "hover:bg-zinc-800 dark:hover:bg-zinc-100",
                                                    "shadow-sm",
                                                    "active:scale-95"
                                                ],
                                                tier.buttonStyle === 'outline' && [
                                                    "border-2 border-zinc-200 dark:border-zinc-700 text-zinc-500",
                                                    "cursor-default"
                                                ]
                                            )}
                                            disabled={tier.buttonStyle === 'outline'}
                                        >
                                            {tier.buttonStyle === 'gradient' && <Star className="w-3.5 h-3.5" />}
                                            {tier.buttonText}
                                        </button>
                                    </motion.div>
                                ))}
                            </div>

                            {/* Footer Note */}
                            <p className="text-center text-[10px] text-muted-foreground mt-4">
                                All plans include access to basic features. Prices exclude applicable taxes.
                            </p>
                        </div>
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );
}

