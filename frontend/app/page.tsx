'use client';

import { useState, useEffect, useCallback } from 'react';
import { Sidebar, HistoryItem } from '@/components/Sidebar';
import { Navbar } from '@/components/Navbar';
import { Footer } from '@/components/Footer';
import { AnimationGenerator } from '@/components/AnimationGenerator';
import { Menu } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useUser } from '@clerk/nextjs';
import { getUserChats, deleteChat, Chat } from '@/lib/api';

export default function Home() {
  const { user, isSignedIn, isLoaded } = useUser();
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [currentChat, setCurrentChat] = useState<HistoryItem | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isDesktopCollapsed, setIsDesktopCollapsed] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);

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
          />
        </div>
      </main>

      <Footer isDesktopCollapsed={isDesktopCollapsed} />
    </div>
  );
}
