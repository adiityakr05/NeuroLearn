import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { Layers, ShieldCheck, AlertTriangle } from 'lucide-react';

export default function SubjectMasteryComparison({ data = [], onFilterSubject, activeSubject }) {
  return (
    <div className="bg-white rounded-3xl border border-slate-200/80 shadow-xs p-6 space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-xl bg-cyan-50 text-cyan-600 flex items-center justify-center">
              <Layers className="w-4 h-4" />
            </div>
            <h3 className="text-base font-bold text-slate-900">Subject Mastery vs Target Mastery</h3>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Topic mastery estimated through active study frequency and quiz precision
          </p>
        </div>

        {/* Quick subject pill filter */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs">
          <button
            onClick={() => onFilterSubject('all')}
            className={`px-3 py-1 rounded-xl font-bold transition shrink-0 ${
              activeSubject === 'all'
                ? 'bg-slate-900 text-white'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            All Subjects
          </button>
          {data.map((s) => (
            <button
              key={s.code}
              onClick={() => onFilterSubject(s.subject)}
              className={`px-2.5 py-1 rounded-xl font-bold transition shrink-0 ${
                activeSubject === s.subject
                  ? 'bg-indigo-600 text-white'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {s.code}
            </button>
          ))}
        </div>
      </div>

      {/* Recharts Bar Comparison */}
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#F1F5F9" />
            <XAxis dataKey="code" stroke="#94A3B8" fontSize={11} tickLine={false} />
            <YAxis stroke="#94A3B8" fontSize={11} tickLine={false} axisLine={false} domain={[0, 100]} unit="%" />
            <Tooltip
              contentStyle={{
                backgroundColor: '#FFFFFF',
                borderRadius: '16px',
                border: '1px solid #E2E8F0',
                fontSize: '11px',
              }}
            />
            <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} iconType="circle" />
            <Bar dataKey="mastery" name="Current Estimated Mastery" fill="#06B6D4" radius={[4, 4, 0, 0]} />
            <Bar dataKey="targetMastery" name="Target Target Mastery" fill="#E2E8F0" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Strong vs Weak Breakdown Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 pt-2">
        {data.map((subj) => {
          const isCritical = subj.status === 'critical_attention';
          const isStrong = subj.status === 'strong';

          return (
            <div
              key={subj.code}
              className={`p-3.5 rounded-2xl border text-xs space-y-1.5 ${
                isCritical
                  ? 'bg-rose-50/50 border-rose-200'
                  : isStrong
                  ? 'bg-emerald-50/50 border-emerald-200'
                  : 'bg-slate-50/70 border-slate-200/80'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-bold text-slate-900">{subj.subject}</span>
                <span
                  className={`text-[10px] font-extrabold uppercase px-1.5 py-0.2 rounded-full ${
                    isCritical
                      ? 'bg-rose-100 text-rose-700'
                      : isStrong
                      ? 'bg-emerald-100 text-emerald-700'
                      : 'bg-slate-200 text-slate-700'
                  }`}
                >
                  {subj.status.replace('_', ' ')}
                </span>
              </div>

              <div className="pt-1 space-y-1 text-slate-600">
                <div className="flex items-center gap-1 text-emerald-700 font-semibold">
                  <ShieldCheck className="w-3.5 h-3.5 shrink-0" />
                  <span className="truncate">Strong: {subj.strongestTopic}</span>
                </div>
                <div className="flex items-center gap-1 text-rose-700 font-semibold">
                  <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                  <span className="truncate">Bottleneck: {subj.weakestTopic}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
