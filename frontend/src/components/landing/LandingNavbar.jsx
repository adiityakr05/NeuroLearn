import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { BrainCircuit, ArrowRight, Menu, X, Sparkles } from 'lucide-react';

export default function LandingNavbar() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-slate-200/80">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between">
        {/* Brand Logo */}
        <Link to="/" className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center text-white shadow-md shadow-indigo-100">
            <BrainCircuit className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="font-bold text-lg text-slate-900 tracking-tight">NeuroLearn</span>
              <span className="text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded-full bg-indigo-50 text-indigo-600 border border-indigo-100">
                AI Agent
              </span>
            </div>
            <p className="text-[11px] text-slate-500 font-medium">Adaptive Study Planner</p>
          </div>
        </Link>

        {/* Desktop Navigation */}
        <nav className="hidden md:flex items-center gap-8 text-sm font-semibold text-slate-600">
          <a href="#problem-solution" className="hover:text-indigo-600 transition">
            Why Adaptive?
          </a>
          <a href="#agent-architecture" className="hover:text-indigo-600 transition">
            Agent Architecture
          </a>
          <a href="#how-it-works" className="hover:text-indigo-600 transition">
            How It Works
          </a>
          <a href="#features" className="hover:text-indigo-600 transition">
            Features
          </a>
          <a href="#preview" className="hover:text-indigo-600 transition">
            Platform Preview
          </a>
        </nav>

        {/* Right CTA */}
        <div className="hidden sm:flex items-center gap-3">
          <Link
            to="/dashboard"
            className="flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold transition shadow-sm"
          >
            <span>Open Student App</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {/* Mobile Hamburger */}
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="md:hidden p-2 text-slate-600 hover:text-slate-900 rounded-xl"
          aria-label="Toggle Navigation"
        >
          {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
        </button>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden bg-white border-b border-slate-200 px-6 py-4 space-y-3 text-sm font-semibold text-slate-700">
          <a
            href="#problem-solution"
            onClick={() => setMobileMenuOpen(false)}
            className="block py-1 hover:text-indigo-600"
          >
            Why Adaptive?
          </a>
          <a
            href="#agent-architecture"
            onClick={() => setMobileMenuOpen(false)}
            className="block py-1 hover:text-indigo-600"
          >
            Agent Architecture
          </a>
          <a
            href="#how-it-works"
            onClick={() => setMobileMenuOpen(false)}
            className="block py-1 hover:text-indigo-600"
          >
            How It Works
          </a>
          <a
            href="#features"
            onClick={() => setMobileMenuOpen(false)}
            className="block py-1 hover:text-indigo-600"
          >
            Features
          </a>
          <a
            href="#preview"
            onClick={() => setMobileMenuOpen(false)}
            className="block py-1 hover:text-indigo-600"
          >
            Platform Preview
          </a>
          <div className="pt-2 border-t border-slate-100">
            <Link
              to="/dashboard"
              className="w-full flex items-center justify-center gap-2 py-2.5 bg-indigo-600 text-white rounded-xl text-xs font-bold"
            >
              <span>Open Student App</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      )}
    </header>
  );
}
