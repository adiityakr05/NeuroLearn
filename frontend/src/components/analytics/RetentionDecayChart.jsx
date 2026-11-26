import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceDot,
} from 'recharts';
import { Sparkles, Brain, Info, Repeat } from 'lucide-react';

export default function RetentionDecayChart({ data = [] }) {
  // Custom tooltip explaining the curves
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const point = payload[0].payload;
      return (
        <div className="bg-white p-3.5 rounded-2xl border border-slate-200 shadow-lg text-xs space-y-1.5 max-w-xs">
          <p className="font-bold text-slate-900 border-b border-slate-100 pb-1">
            Day {label} {point.revisionEvent ? `• ${point.revisionEvent}` : ''}
          </p>
          <div className="space-y-1">
            <div className="flex items-center justify-between gap-4">
              <span className="text-indigo-600 font-semibold flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-indigo-600"></span>
                Predicted Retention (Spaced):
              </span>
              <strong className="text-indigo-950 font-bold">{point.predicted}%</strong>
            </div>

            {point.actual !== null && (
              <div className="flex items-center justify-between gap-4">
                <span className="text-emerald-600 font-semibold flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-emerald-600"></span>
                  Actual Recall Test:
                </span>
                <strong className="text-emerald-950 font-bold">{point.actual}%</strong>
              </div>
            )}

            <div className="flex items-center justify-between gap-4">
              <span className="text-slate-400 flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-slate-300"></span>
                Baseline (No Repetition):
              </span>
              <span className="text-slate-500 font-semibold">{point.baselineWithoutRepetition}%</span>
            </div>
          </div>
          {point.note && <p className="text-[10px] text-slate-500 italic pt-1">{point.note}</p>}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="bg-white rounded-3xl border border-slate-200/80 shadow-xs p-6 space-y-4">
      {/* Chart Title & Explanation Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
              <Brain className="w-4 h-4" />
            </div>
            <h3 className="text-base font-bold text-slate-900">
              Ebbinghaus Retention Decay & Spaced Repetition Curve
            </h3>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Predicted memory retention decay over 30 days vs. baseline forgetting without repetition
          </p>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto">
          <span className="px-2.5 py-1 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-100 flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
            Actual Recall Dots
          </span>
        </div>
      </div>

      {/* Main Line Chart */}
      <div className="h-72 w-full pt-2">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 15, right: 15, left: -20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#F1F5F9" />
            <XAxis
              dataKey="day"
              stroke="#94A3B8"
              fontSize={11}
              tickLine={false}
              unit="d"
            />
            <YAxis
              stroke="#94A3B8"
              fontSize={11}
              tickLine={false}
              axisLine={false}
              domain={[0, 100]}
              unit="%"
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }}
              iconType="circle"
            />

            {/* Baseline without repetition: Steep exponential decay */}
            <Line
              type="monotone"
              dataKey="baselineWithoutRepetition"
              name="Baseline Forgetting (No Repetition)"
              stroke="#CBD5E1"
              strokeDasharray="4 4"
              strokeWidth={2}
              dot={false}
            />

            {/* NeuroLearn Spaced Repetition Curve: Flattens decay with each review */}
            <Line
              type="monotone"
              dataKey="predicted"
              name="Predicted Retention (NeuroLearn Spaced)"
              stroke="#6366F1"
              strokeWidth={3}
              dot={{ r: 3, fill: '#6366F1', strokeWidth: 0 }}
              activeDot={{ r: 6 }}
            />

            {/* Actual Recall Tests */}
            <Line
              type="monotone"
              dataKey="actual"
              name="Actual Recall Test Results"
              stroke="#10B981"
              strokeWidth={0}
              dot={{ r: 5, fill: '#10B981', stroke: '#FFFFFF', strokeWidth: 2 }}
              connectNulls={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Scientific Context Box */}
      <div className="p-4 bg-slate-50/80 rounded-2xl border border-slate-200/60 text-xs text-slate-600 space-y-1.5">
        <div className="flex items-center gap-1.5 font-bold text-slate-800">
          <Repeat className="w-3.5 h-3.5 text-indigo-600" />
          <span>How NeuroLearn Modifies Your Forgetting Curve:</span>
        </div>
        <p className="leading-relaxed">
          Without scheduled reviews, human memory drops to ~20% retention within 14 days (the grey dashed curve).
          Each spaced recall session scheduled by the Learning Element resets retention to ~95% while flattening the decay trajectory, meaning longer gaps are needed before the next review.
        </p>
      </div>
    </div>
  );
}
