import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import {
  BrainCircuit,
  Mail,
  Lock,
  Eye,
  EyeOff,
  ArrowRight,
  Sparkles,
  AlertCircle,
  CheckCircle2,
  Info
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);

  const [submitting, setSubmitting] = useState(false);
  const [errors, setErrors] = useState({});
  const [forgotModalOpen, setForgotModalOpen] = useState(false);

  // Read the original destination if redirected from a protected route
  const from = location.state?.from?.pathname || '/dashboard';

  const validate = () => {
    const errs = {};
    if (!email.trim()) {
      errs.email = 'Email address is required.';
    } else if (!/\S+@\S+\.\S+/.test(email)) {
      errs.email = 'Please provide a valid email format (e.g. aditya@college.edu).';
    }

    if (!password) {
      errs.password = 'Password is required.';
    } else if (password.length < 6) {
      errs.password = 'Password must be at least 6 characters.';
    }

    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;

    try {
      setSubmitting(true);
      await login({ email, password, rememberMe });
      navigate(from, { replace: true });
    } catch (err) {
      setErrors({ form: err.message || 'Login failed. Please verify your credentials.' });
    } finally {
      setSubmitting(false);
    }
  };

  const handleFillDemo = () => {
    setEmail('aditya.kumar@college.edu');
    setPassword('NeuroLearn2026!');
    setErrors({});
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      {/* Brand Header */}
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <Link to="/" className="inline-flex items-center gap-2.5 mb-3">
          <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center text-white shadow-md shadow-indigo-100">
            <BrainCircuit className="w-6 h-6" />
          </div>
          <span className="text-2xl font-black text-slate-900 tracking-tight">NeuroLearn</span>
        </Link>
        <h2 className="text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight">
          Welcome back to NeuroLearn
        </h2>
        <p className="text-xs sm:text-sm text-slate-500 mt-1">
          Learn Smarter. Remember Longer.
        </p>
      </div>

      {/* Main Login Card */}
      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md px-4 sm:px-0">
        <div className="bg-white py-8 px-6 sm:px-10 rounded-3xl border border-slate-200/90 shadow-xl space-y-6">
          {/* Demo Hint Banner */}
          <div className="p-3.5 rounded-2xl bg-indigo-50/70 border border-indigo-100 text-xs text-indigo-900 flex items-start justify-between gap-3">
            <div className="flex items-start gap-2">
              <Sparkles className="w-4 h-4 text-indigo-600 shrink-0 mt-0.5" />
              <div>
                <p className="font-bold">Prototype Demonstration Mode</p>
                <p className="text-indigo-800/90 text-[11px] mt-0.5">
                  Enter any valid email or click below to autofill demo student credentials.
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={handleFillDemo}
              className="text-[11px] font-extrabold text-indigo-700 bg-white px-2.5 py-1 rounded-lg border border-indigo-200 hover:bg-indigo-50 transition shrink-0"
            >
              Autofill
            </button>
          </div>

          {/* Form-level error */}
          {errors.form && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-700 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-500" />
              <span>{errors.form}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Email Address */}
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
                College Email
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    if (errors.email) setErrors({ ...errors, email: null });
                  }}
                  placeholder="e.g. aditya.kumar@college.edu"
                  className={`w-full pl-10 pr-4 py-2.5 bg-slate-50 border rounded-xl text-sm font-semibold text-slate-900 focus:outline-none focus:ring-2 transition ${
                    errors.email
                      ? 'border-rose-400 focus:ring-rose-200'
                      : 'border-slate-200 focus:ring-indigo-500/20 focus:border-indigo-600'
                  }`}
                />
              </div>
              {errors.email && (
                <p className="text-xs text-rose-600 mt-1 font-medium">{errors.email}</p>
              )}
            </div>

            {/* Password */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs font-bold uppercase tracking-wider text-slate-700">
                  Password
                </label>
                <button
                  type="button"
                  onClick={() => setForgotModalOpen(true)}
                  className="text-xs font-bold text-indigo-600 hover:text-indigo-700 hover:underline"
                >
                  Forgot password?
                </button>
              </div>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value);
                    if (errors.password) setErrors({ ...errors, password: null });
                  }}
                  placeholder="••••••••"
                  className={`w-full pl-10 pr-10 py-2.5 bg-slate-50 border rounded-xl text-sm font-semibold text-slate-900 focus:outline-none focus:ring-2 transition ${
                    errors.password
                      ? 'border-rose-400 focus:ring-rose-200'
                      : 'border-slate-200 focus:ring-indigo-500/20 focus:border-indigo-600'
                  }`}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {errors.password && (
                <p className="text-xs text-rose-600 mt-1 font-medium">{errors.password}</p>
              )}
            </div>

            {/* Remember Me */}
            <div className="flex items-center gap-2 pt-1">
              <input
                type="checkbox"
                id="rememberMe"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                className="w-4 h-4 rounded text-indigo-600 focus:ring-indigo-500 border-slate-300"
              />
              <label htmlFor="rememberMe" className="text-xs font-semibold text-slate-700 select-none">
                Remember this session
              </label>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={submitting}
              className="w-full flex items-center justify-center gap-2 py-3 px-4 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-sm font-bold transition shadow-md shadow-indigo-100 disabled:opacity-50 mt-2"
            >
              {submitting ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                  <span>Authenticating...</span>
                </>
              ) : (
                <>
                  <span>Sign In to Dashboard</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          {/* Registration Redirect Footer */}
          <div className="pt-4 border-t border-slate-100 text-center text-xs text-slate-500">
            <span>Don't have an account yet? </span>
            <Link to="/register" className="font-bold text-indigo-600 hover:text-indigo-700 hover:underline">
              Create student account
            </Link>
          </div>
        </div>
      </div>

      {/* Forgot Password Demo Modal */}
      {forgotModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs">
          <div className="bg-white rounded-3xl max-w-sm w-full p-6 text-center space-y-4 border border-slate-200 shadow-xl">
            <div className="w-12 h-12 rounded-2xl bg-indigo-50 text-indigo-600 flex items-center justify-center mx-auto">
              <Info className="w-6 h-6" />
            </div>
            <h3 className="text-base font-bold text-slate-900">Password Recovery Notice</h3>
            <p className="text-xs text-slate-600 leading-relaxed">
              In this prototype demonstration, automated email recovery is disabled until Member 3 integrates the FastAPI SMTP mailer. You can log in using any email and 6-character password!
            </p>
            <button
              onClick={() => setForgotModalOpen(false)}
              className="w-full py-2.5 bg-indigo-600 text-white rounded-xl text-xs font-bold hover:bg-indigo-700 transition"
            >
              Got it, continue
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
