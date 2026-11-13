import React, { useState } from 'react';
import { X, Calendar, Clock, AlertTriangle, Sparkles, Check } from 'lucide-react';

export default function RescheduleModal({ session, isOpen, onClose, onConfirm }) {
  if (!isOpen || !session) return null;

  const [selectedDate, setSelectedDate] = useState(session.date || '2026-11-14');
  const [selectedSlot, setSelectedSlot] = useState(session.timeSlot || '04:30 PM - 05:15 PM');
  const [reason, setReason] = useState('Conflict with college laboratory class');
  const [submitting, setSubmitting] = useState(false);

  const slotOptions = [
    '09:00 AM - 10:30 AM (Morning Focus)',
    '11:30 AM - 12:45 PM (Midday)',
    '03:00 PM - 04:30 PM (Afternoon)',
    '05:30 PM - 07:00 PM (Evening Prime)',
    '08:30 PM - 09:30 PM (Consolidation)',
  ];

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    await onConfirm(session.id, selectedDate, selectedSlot.split(' (')[0], reason);
    setSubmitting(false);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs">
      <div className="bg-white rounded-3xl max-w-lg w-full border border-slate-200 shadow-xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="p-5 sm:p-6 border-b border-slate-100 flex items-center justify-between">
          <div>
            <span className="text-xs font-bold uppercase tracking-wider text-indigo-600">Adaptive Re-balancing</span>
            <h3 className="text-lg font-bold text-slate-900 mt-0.5">Reschedule Study Session</h3>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-xl transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Form */}
        <form onSubmit={handleSubmit} className="p-5 sm:p-6 space-y-4">
          {/* Target Topic Details */}
          <div className="p-3.5 bg-slate-50 rounded-2xl border border-slate-200/80">
            <span className="text-xs font-semibold text-slate-500 uppercase">{session.subject}</span>
            <h4 className="text-sm font-bold text-slate-900">{session.topic}</h4>
            <p className="text-xs text-slate-500 mt-1">Duration: {session.durationMinutes} minutes</p>
          </div>

          {/* AI Retention Impact Warning */}
          <div className="p-3 bg-amber-50 rounded-xl border border-amber-200/80 flex items-start gap-2.5 text-xs text-amber-800">
            <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
            <div>
              <p className="font-bold">Agent Retention Advisory:</p>
              <p className="mt-0.5 leading-relaxed">
                Postponing beyond 48 hours will cause predicted retention to drop from {session.retentionScore}% to ~42%. The Critic element suggests maintaining study within the next 2 days.
              </p>
            </div>
          </div>

          {/* Pick New Date */}
          <div>
            <label className="block text-xs font-bold uppercase text-slate-700 mb-1.5">
              New Study Date
            </label>
            <div className="relative">
              <Calendar className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="date"
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                min="2026-11-13"
                max="2026-11-20"
                className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm font-semibold text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
                required
              />
            </div>
          </div>

          {/* Pick New Time Slot */}
          <div>
            <label className="block text-xs font-bold uppercase text-slate-700 mb-1.5">
              Available Time Slot
            </label>
            <div className="relative">
              <Clock className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <select
                value={selectedSlot}
                onChange={(e) => setSelectedSlot(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm font-semibold text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
              >
                {slotOptions.map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Reason for AI Agent to learn from */}
          <div>
            <label className="block text-xs font-bold uppercase text-slate-700 mb-1.5">
              Reason for Reschedule (Informs Critic Agent)
            </label>
            <textarea
              rows={2}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g. Preparing for sudden class test, sickness, or unexpected travel"
              className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs sm:text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
              required
            />
          </div>

          {/* Modal Actions */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-100">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2.5 rounded-xl border border-slate-200 text-xs font-bold text-slate-600 hover:bg-slate-50 transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="flex items-center gap-1.5 px-5 py-2.5 rounded-xl bg-indigo-600 text-white text-xs font-bold hover:bg-indigo-700 transition shadow-sm disabled:opacity-50"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>{submitting ? 'Recalculating...' : 'Confirm & Re-balance Plan'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
