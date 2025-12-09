'use client';

import { useState, useEffect } from 'react';
import { Sidebar, HistoryItem } from '@/components/Sidebar';
import { Navbar } from '@/components/Navbar';
import { Footer } from '@/components/Footer';
import { AnimationGenerator } from '@/components/AnimationGenerator';
import { Menu } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function Home() {
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [currentChat, setCurrentChat] = useState<HistoryItem | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isDesktopCollapsed, setIsDesktopCollapsed] = useState(false);

  // Load history from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem('animation_history');
    if (saved) {
      try {
        setHistory(JSON.parse(saved));
      } catch (e) {
        console.error("Failed to parse history", e);
      }
    }
  }, []);

  // Save history whenever it changes
  useEffect(() => {
    localStorage.setItem('animation_history', JSON.stringify(history));
  }, [history]);

  const handleGenerateComplete = (newItem: HistoryItem) => {
    setHistory(prev => [newItem, ...prev]);
    setCurrentChat(newItem);
  };

  const handleDelete = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
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
