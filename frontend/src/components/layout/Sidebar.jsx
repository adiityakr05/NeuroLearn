import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  CalendarCheck,
  BookOpen,
  LineChart,
  Sparkles,
  Settings,
  BrainCircuit,
  LogOut,
  ChevronRight,
  GraduationCap
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

const navItems = [
  { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
  { name: 'Adaptive Planner', path: '/planner', icon: CalendarCheck },
  { name: 'Subjects & Topics', path: '/subjects', icon: BookOpen },
  { name: 'Performance Analytics', path: '/analytics', icon: LineChart },
  { name: 'AI Recommendations', path: '/recommendations', icon: Sparkles, badge: '4 New' },
];

export default function Sidebar({ isOpen, onClose }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  const displayName = user?.name || 'Aditya Kumar';
  const displayProgram = user?.program || 'B.Tech AI • Sem 6';

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs z-40 lg:hidden transition-opacity"
          onClick={onClose}
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={`fixed top-0 bottom-0 left-0 z-50 w-72 bg-white border-r border-slate-200/80 flex flex-col transition-transform duration-300 ease-in-out lg:translate-x-0 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Brand Header */}
        <div className="h-18 px-6 flex items-center gap-3 border-b border-slate-100">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center text-white shadow-md shadow-indigo-100">
            <BrainCircuit className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="font-bold text-lg text-slate-900 tracking-tight">NeuroLearn</span>
              <span className="text-[10px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded-full bg-indigo-50 text-indigo-600 border border-indigo-100/80">AI</span>
            </div>
            <p className="text-xs text-slate-500 font-medium">Adaptive Study Agent</p>
          </div>
        </div>

        {/* Navigation Links */}
        <nav className="flex-1 px-4 py-6 space-y-1.5 overflow-y-auto">
          <div className="px-3 pb-2 text-[11px] font-bold tracking-wider uppercase text-slate-400">
            Core Learning
          </div>
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                onClick={onClose}
                className={({ isActive }) =>
                  `flex items-center justify-between px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all ${
                    isActive
                      ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-200'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    <div className="flex items-center gap-3">
                      <Icon className={`w-5 h-5 ${isActive ? 'text-white' : 'text-slate-400'}`} />
                      <span>{item.name}</span>
                    </div>
                    {item.badge && (
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full font-semibold ${
                          isActive
                            ? 'bg-white/20 text-white'
                            : 'bg-indigo-50 text-indigo-600 border border-indigo-100'
                        }`}
                      >
                        {item.badge}
                      </span>
                    )}
                  </>
                )}
              </NavLink>
            );
          })}
        </nav>

        {/* Learning Agent Status Card */}
        <div className="p-4 mx-4 mb-4 rounded-2xl bg-gradient-to-br from-indigo-50/80 via-slate-50 to-violet-50/60 border border-indigo-100/60">
          <div className="flex items-center gap-2 mb-2">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span className="text-xs font-semibold text-slate-800">Retention Agent Active</span>
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">
            Estimating memory decay based on 4 completed sessions today.
          </p>
        </div>

        {/* User Mini Profile & Logout */}
        <div className="p-4 border-t border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-3 min-w-0">
            <img
              src={user?.avatar || "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80"}
              alt={displayName}
              className="w-9 h-9 rounded-full object-cover ring-2 ring-slate-100 shrink-0"
            />
            <div className="text-left min-w-0">
              <p className="text-sm font-semibold text-slate-900 leading-tight truncate">{displayName}</p>
              <p className="text-xs text-slate-500 flex items-center gap-1 truncate">
                <GraduationCap className="w-3.5 h-3.5 text-indigo-500 shrink-0" />
                <span className="truncate">{displayProgram}</span>
              </p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            title="Sign out of student account"
            className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors shrink-0"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </aside>
    </>
  );
}
