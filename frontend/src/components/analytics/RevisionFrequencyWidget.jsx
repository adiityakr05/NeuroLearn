import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { RefreshCw, AlertCircle, Clock, CalendarClock } from 'lucide-react';

export default function RevisionFrequencyWidget({ frequency = [], overdueList = [] }) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Left: Revision Frequency Bar */}
      <div className="lg:col-span-2 bg-white rounded-3xl border border-slate-200/80 shadow-xs p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
                <RefreshCw className="w-4 h-4" />
              </div>
              <h3 className="text-base font-bold text-slate-900">Weekly Revision Adherence</h3>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Completed spaced repetitions vs. missed target sessions
            </p>
          </div>
        </div>

        <div className="h-56 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={frequency} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#F1F5F9" />
              <XAxis dataKey="week" stroke="#94A3B8" fontSize={11} tickLine={false} />
              <YAxis stroke="#94A3B8" fontSize={11} tickLine={false} axisLine={false} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#FFFFFF',
                  borderRadius: '14px',
                  border: '1px solid #E2E8F0',
                  fontSize: '11px',
                }}
              />
              <Bar dataKey="completed" name="Completed Revisions" fill="#6366F1" radius={[4, 4, 0, 0]} />
              <Bar dataKey="missed" name="Missed Intervals" fill="#FDA4AF" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Right: Overdue Revisions Alert List */}
      <div className="bg-white rounded-3xl border border-slate-200/80 shadow-xs p-6 space-y-4">
        <div>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center">
              <AlertCircle className="w-4 h-4" />
            </div>
            <h3 className="text-base font-bold text-slate-900">Overdue Memory Reviews</h3>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Prioritized by Critic element to halt rapid decay
          </p>
        </div>

        <div className="space-y-3">
          {overdueList.map((item) => (
            <div
              key={item.id}
              className="p-3.5 rounded-2xl bg-rose-50/50 border border-rose-200/80 text-xs space-y-1.5"
            >
              <div className="flex items-center justify-between">
                <span className="font-semibold text-rose-700 bg-rose-100 px-2 py-0.2 rounded-md">
                  {item.subject}
                </span>
                <span className="font-bold text-rose-600 flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  <span>{item.daysOverdue}d Overdue</span>
                </span>
              </div>

              <h4 className="font-bold text-slate-900 leading-snug">{item.topic}</h4>

              <div className="pt-1 flex items-center justify-between text-slate-600 border-t border-rose-200/50">
                <span>Predicted Retention:</span>
                <strong className="text-rose-700">{item.currentRetention}%</strong>
              </div>
              <p className="text-[10px] text-rose-600 italic font-medium">{item.predictedDecay}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
