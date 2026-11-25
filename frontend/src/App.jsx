import React, { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './components/common/ProtectedRoute';
import AppLayout from './components/layout/AppLayout';

// Eagerly load core landing/auth pages for instant first-load
import Landing from './pages/Landing';
import Login from './pages/Login';
import Register from './pages/Register';

// Route-level code splitting for heavy sub-pages (e.g. Analytics with Recharts)
const Dashboard = lazy(() => import('./pages/Dashboard'));
const StudyPlanner = lazy(() => import('./pages/StudyPlanner'));
const Subjects = lazy(() => import('./pages/Subjects'));
const Analytics = lazy(() => import('./pages/Analytics'));
const Recommendations = lazy(() => import('./pages/Recommendations'));

function PageFallback() {
  return (
    <div className="flex h-screen w-full items-center justify-center bg-slate-950 text-slate-400">
      <div className="flex flex-col items-center gap-3">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
        <p className="text-sm">Loading view...</p>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Suspense fallback={<PageFallback />}>
          <Routes>
            {/* Public Routes */}
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />

            {/* Protected Student Dashboard Layout */}
            <Route
              element={
                <ProtectedRoute>
                  <AppLayout />
                </ProtectedRoute>
              }
            >
              <Route path="dashboard" element={<Dashboard />} />
              <Route path="planner" element={<StudyPlanner />} />
              <Route path="subjects" element={<Subjects />} />
              <Route path="analytics" element={<Analytics />} />
              <Route path="recommendations" element={<Recommendations />} />
            </Route>

            {/* Fallback route */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </AuthProvider>
  );
}
