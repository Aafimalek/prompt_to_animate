'use client';

import { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'next/navigation';
import { Sidebar, HistoryItem } from '@/components/Sidebar';
import { Navbar } from '@/components/Navbar';
import { Footer } from '@/components/Footer';
import { AnimationGenerator } from '@/components/AnimationGenerator';
import { PricingModal } from '@/components/PricingModal';
import { cn } from '@/lib/utils';
import { useUser } from '@clerk/nextjs';
import { getUserChats, deleteChat, Chat, API_BASE_URL } from '@/lib/api';

export default function Home() {
  const { user, isSignedIn, isLoaded } = useUser();
  const searchParams = useSearchParams();
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [currentChat, setCurrentChat] = useState<HistoryItem | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isDesktopCollapsed, setIsDesktopCollapsed] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [isPricingOpen, setIsPricingOpen] = useState(false);
  const [paymentSuccess, setPaymentSuccess] = useState(false);

  // Handle payment success from URL params
  useEffect(() => {
    const status = searchParams.get('status');
    const paymentId = searchParams.get('payment_id');

    if (status === 'succeeded' && paymentId && user?.id) {
      // Payment was successful - trigger webhook manually for local testing
      setPaymentSuccess(true);

      // Call backend to add credits (simulates webhook for local testing)
      fetch(`${API_BASE_URL}/webhook/payment`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event_type: 'payment_succeeded',
          clerk_id: user.id,
          product_id: 'basic'  // Assume basic for now
        })
      }).then(() => {
        console.log('Credits added via manual webhook');
      }).catch(err => {
        console.error('Failed to add credits:', err);
      });

      // Clear URL params after 3 seconds
      setTimeout(() => {
        window.history.replaceState({}, '', '/');
        setPaymentSuccess(false);
      }, 5000);
    }
  }, [searchParams, user?.id]);

  // Convert Chat from API to HistoryItem
  const chatToHistoryItem = (chat: Chat): HistoryItem => ({
    id: chat.id,
    prompt: chat.prompt,
    timestamp: new Date(chat.created_at).getTime(),
    videoUrl: chat.video_url,
    code: chat.code,
  });

  // Fetch history from MongoDB for authenticated users
  const fetchHistory = useCallback(async () => {
    if (!isSignedIn || !user?.id) {
      // For non-authenticated users, use localStorage
      const saved = localStorage.getItem('animation_history');
      if (saved) {
        try {
          setHistory(JSON.parse(saved));
        } catch (e) {
          console.error("Failed to parse history", e);
        }
      }
      return;
    }

    setIsLoadingHistory(true);
    try {
      const chats = await getUserChats(user.id);
      setHistory(chats.map(chatToHistoryItem));
    } catch (error) {
      console.error('Failed to fetch history:', error);
      // Fallback to localStorage on error
      const saved = localStorage.getItem('animation_history');
      if (saved) {
        try {
          setHistory(JSON.parse(saved));
        } catch (e) {
          console.error("Failed to parse history", e);
        }
      }
    } finally {
      setIsLoadingHistory(false);
    }
  }, [isSignedIn, user?.id]);

  // Load history on mount and when auth state changes
  useEffect(() => {
    if (isLoaded) {
      fetchHistory();
    }
  }, [isLoaded, fetchHistory]);

  // Save to localStorage for non-authenticated users
  useEffect(() => {
    if (isLoaded && !isSignedIn) {
      localStorage.setItem('animation_history', JSON.stringify(history));
    }
  }, [history, isLoaded, isSignedIn]);

  const handleGenerateComplete = (newItem: HistoryItem) => {
    // For authenticated users, history is already saved to MongoDB by backend
    // Just update the local state
    setHistory(prev => {
      // Check if item already exists (update) or is new
      const existingIndex = prev.findIndex(item => item.id === newItem.id);
      if (existingIndex >= 0) {
        const updated = [...prev];
        updated[existingIndex] = newItem;
        return updated;
      }
      return [newItem, ...prev];
    });
    setCurrentChat(newItem);
  };

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();

    // Delete from MongoDB if authenticated
    if (isSignedIn && user?.id) {
      try {
        await deleteChat(user.id, id);
      } catch (error) {
        console.error('Failed to delete chat:', error);
        // Continue with local deletion even if API fails
      }
    }

    setHistory(prev => prev.filter(item => item.id !== id));
    if (currentChat?.id === id) {
      setCurrentChat(null);
    }
  };

  return (
    <div className="flex h-screen overflow-hidden bg-background text-foreground font-sans">
      {/* Background Effects */}
      <div className="fixed inset-0 z-0 pointer-events-none">
        <div className="absolute top-0 inset-x-0 h-64 bg-gradient-to-b from-zinc-900/10 to-transparent" />
      </div>

      {/* Gradual Blur Header */}
      <div className="fixed top-0 left-0 right-0 h-32 z-40 pointer-events-none backdrop-blur-[2px] [mask-image:linear-gradient(to_bottom,black,transparent)]" />

      {/* Gradual Blur Footer */}
      <div className="fixed bottom-0 left-0 right-0 h-32 z-40 pointer-events-none backdrop-blur-[2px] [mask-image:linear-gradient(to_top,black,transparent)]" />

      <Navbar onMenuClick={() => setIsSidebarOpen(true)} isDesktopCollapsed={isDesktopCollapsed} />

      <Sidebar
        history={history}
        onSelect={setCurrentChat}
        onNew={() => setCurrentChat(null)}
        onDelete={handleDelete}
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
        isDesktopCollapsed={isDesktopCollapsed}
        onDesktopToggle={() => setIsDesktopCollapsed(!isDesktopCollapsed)}
        isLoading={isLoadingHistory}
        onUpgradeClick={() => setIsPricingOpen(true)}
      />

      {/* Main Content */}
      <main className={cn(
        "flex-1 relative z-10 overflow-y-auto overflow-x-hidden transition-all duration-300",
        // Desktop margin based on sidebar state
        isDesktopCollapsed ? "md:ml-0" : "md:ml-0"
      )}>
        {/* Wrapper for vertical centering */}
        <div className="min-h-full flex flex-col pt-20 pb-24">
          <AnimationGenerator
            initialData={currentChat}
            onGenerateComplete={handleGenerateComplete}
            onUpgradeClick={() => setIsPricingOpen(true)}
          />
        </div>
      </main>

      <Footer isDesktopCollapsed={isDesktopCollapsed} />

      {/* Pricing Modal */}
      <PricingModal isOpen={isPricingOpen} onClose={() => setIsPricingOpen(false)} />

      {/* Payment Success Toast */}
      {paymentSuccess && (
        <div className="fixed bottom-8 left-1/2 -translate-x-1/2 z-50 animate-in slide-in-from-bottom-4">
          <div className="flex items-center gap-3 px-6 py-4 rounded-2xl bg-gradient-to-r from-green-500 to-emerald-500 text-white shadow-2xl shadow-green-500/30">
            <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <div>
              <p className="font-semibold">Payment Successful! 🎉</p>
              <p className="text-sm text-white/80">Credits added to your account</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
