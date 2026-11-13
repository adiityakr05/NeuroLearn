import React from 'react';
import { Menu, Bell, Sparkles, Search } from 'lucide-react';

export default function Navbar({ onMenuToggle, todayStreak = 12 }) {
  return (
    <header className="sticky top-0 z-30 h-18 bg-white/90 backdrop-blur-md border-b border-slate-200/80 px-4 sm:px-8 flex items-center justify-between">
      {/* Mobile Toggle & Search */}
      <div className="flex items-center gap-4 flex-1 max-w-lg">
        <button
          onClick={onMenuToggle}
          className="lg:hidden p-2 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-xl transition-colors"
          aria-label="Open navigation menu"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div className="relative w-full hidden sm:block">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search subjects, topics, or AI recommendations..."
            className="w-full pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
          />
        </div>
      </div>

      {/* Right Actions */}
      <div className="flex items-center gap-3 sm:gap-4">
        {/* Streak Pill */}
        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-amber-50 border border-amber-200/60 text-amber-700 text-xs font-semibold shadow-xs">
          <span className="text-sm">🔥</span>
          <span>{todayStreak} Day Streak</span>
        </div>

        {/* AI Optimization Mode Indicator */}
        <div className="hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-indigo-50 border border-indigo-100 text-indigo-700 text-xs font-semibold">
          <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
          <span>Adaptive Mode</span>
        </div>

        {/* Notification Bell */}
        <button
          className="relative p-2 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-xl transition-colors"
          aria-label="View notifications"
        >
          <Bell className="w-5 h-5" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-indigo-600 ring-2 ring-white"></span>
        </button>
      </div>
    </header>
  );
}
