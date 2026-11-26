import React, { useState, useEffect, useRef } from 'react';
import { Menu, Bell, Sparkles, Search, Check, CheckCheck, Trash2 } from 'lucide-react';
import { studyService } from '../../services/studyService';
import { useTimer } from '../../context/TimerContext';
import StreakCalendarModal from '../common/StreakCalendarModal';

export default function Navbar({ onMenuToggle }) {
  const { dailyGoalMinutes } = useTimer() || { dailyGoalMinutes: 120 };
  const [streak, setStreak] = useState(0);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [notifOpen, setNotifOpen] = useState(false);
  const [calendarOpen, setCalendarOpen] = useState(false);
  const notifRef = useRef(null);

  const loadNavbarData = async () => {
    try {
      const [notifRes, dashRes] = await Promise.all([
        studyService.getNotifications().catch(() => ({ notifications: [], unreadCount: 0 })),
        studyService.getDashboardData().catch(() => null),
      ]);
      setNotifications(notifRes?.notifications || []);
      setUnreadCount(notifRes?.unreadCount || 0);
      if (dashRes?.stats?.activeStreak !== undefined) {
        setStreak(dashRes.stats.activeStreak);
      }
    } catch {
      // Non-blocking
    }
  };

  useEffect(() => {
    loadNavbarData();
  }, []);

  useEffect(() => {
    if (!notifOpen) return;
    const handleClickOutside = (e) => {
      if (notifRef.current && !notifRef.current.contains(e.target)) {
        setNotifOpen(false);
      }
    };
    const handleEsc = (e) => {
      if (e.key === 'Escape') setNotifOpen(false);
    };
    document.addEventListener('mousedown', handleClickOutside);
    window.addEventListener('keydown', handleEsc);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      window.removeEventListener('keydown', handleEsc);
    };
  }, [notifOpen]);

  const handleMarkRead = async (id) => {
    await studyService.markNotificationRead(id).catch(() => {});
    setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n)));
    setUnreadCount((c) => Math.max(0, c - 1));
  };

  const handleMarkAllRead = async () => {
    await studyService.markAllNotificationsRead().catch(() => {});
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
    setUnreadCount(0);
  };

  const handleDismiss = async (id) => {
    const target = notifications.find((n) => n.id === id);
    await studyService.dismissNotification(id).catch(() => {});
    setNotifications((prev) => prev.filter((n) => n.id !== id));
    if (target && !target.read) {
      setUnreadCount((c) => Math.max(0, c - 1));
    }
  };

  return (
    <>
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
          {/* Clickable Streak Pill -> LeetCode-style Calendar */}
          <button
            type="button"
            onClick={() => setCalendarOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-amber-50 hover:bg-amber-100 border border-amber-200/60 text-amber-700 text-xs font-semibold shadow-xs transition-colors"
            title="View yearly study activity & streak calendar"
          >
            <span className="text-sm">🔥</span>
            <span>{streak} Day Streak</span>
          </button>

          {/* AI Optimization Mode Indicator */}
          <div className="hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-indigo-50 border border-indigo-100 text-indigo-700 text-xs font-semibold">
            <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
            <span>Adaptive Mode</span>
          </div>

          {/* Interactive Notification Bell */}
          <div className="relative" ref={notifRef}>
            <button
              type="button"
              onClick={() => {
                const next = !notifOpen;
                setNotifOpen(next);
                if (next) loadNavbarData();
              }}
              className="relative p-2 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-xl transition-colors"
              aria-label="View notifications"
            >
              <Bell className="w-5 h-5" />
              {unreadCount > 0 && (
                <span className="absolute -top-0.5 -right-0.5 min-w-4 h-4 px-1 rounded-full bg-indigo-600 text-white text-[10px] font-bold flex items-center justify-center ring-2 ring-white">
                  {unreadCount}
                </span>
              )}
            </button>

            {notifOpen && (
              <div className="absolute right-0 mt-2 w-80 sm:w-96 rounded-2xl bg-white shadow-xl border border-slate-200 overflow-hidden z-50">
                <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
                  <span className="text-sm font-bold text-slate-900">Notifications</span>
                  {unreadCount > 0 && (
                    <button
                      onClick={handleMarkAllRead}
                      className="inline-flex items-center gap-1 text-xs font-semibold text-indigo-600 hover:text-indigo-800"
                    >
                      <CheckCheck className="w-3.5 h-3.5" /> Mark all read
                    </button>
                  )}
                </div>

                <div className="max-h-80 overflow-y-auto divide-y divide-slate-100">
                  {notifications.length === 0 ? (
                    <div className="p-6 text-center text-xs text-slate-500">
                      No notifications yet. Complete a quiz, add an exam, or finish a study session to see updates.
                    </div>
                  ) : (
                    notifications.map((n) => (
                      <div key={n.id} className={`p-3.5 flex items-start justify-between gap-2 ${n.read ? 'bg-white' : 'bg-indigo-50/40'}`}>
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-1.5">
                            {!n.read && <span className="w-2 h-2 rounded-full bg-indigo-600 shrink-0" />}
                            <p className="text-xs font-bold text-slate-900 truncate">{n.title}</p>
                          </div>
                          <p className="text-xs text-slate-600 mt-0.5">{n.description}</p>
                          <p className="text-[10px] text-slate-400 mt-1">
                            {n.category} • {n.timestamp ? new Date(n.timestamp).toLocaleString() : ''}
                          </p>
                        </div>
                        <div className="flex items-center gap-1 shrink-0">
                          {!n.read && (
                            <button
                              onClick={() => handleMarkRead(n.id)}
                              className="p-1 text-slate-400 hover:text-indigo-600 rounded"
                              title="Mark as read"
                            >
                              <Check className="w-3.5 h-3.5" />
                            </button>
                          )}
                          <button
                            onClick={() => handleDismiss(n.id)}
                            className="p-1 text-slate-400 hover:text-rose-600 rounded"
                            title="Dismiss"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </header>

      <StreakCalendarModal
        isOpen={calendarOpen}
        onClose={() => setCalendarOpen(false)}
        dailyGoalMinutes={dailyGoalMinutes}
      />
    </>
  );
}
