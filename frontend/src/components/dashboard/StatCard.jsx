import React from 'react';

export default function StatCard({ title, value, subtitle, icon: Icon, trend, colorScheme = 'indigo' }) {
  const schemeStyles = {
    indigo: {
      bg: 'bg-indigo-50 text-indigo-600',
      border: 'border-indigo-100',
    },
    emerald: {
      bg: 'bg-emerald-50 text-emerald-600',
      border: 'border-emerald-100',
    },
    amber: {
      bg: 'bg-amber-50 text-amber-600',
      border: 'border-amber-100',
    },
    cyan: {
      bg: 'bg-cyan-50 text-cyan-600',
      border: 'border-cyan-100',
    },
  };

  const style = schemeStyles[colorScheme] || schemeStyles.indigo;

  return (
    <div className="p-5 bg-white rounded-2xl border border-slate-200/80 shadow-xs hover:shadow-md transition-all duration-200">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">{title}</span>
        <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${style.bg}`}>
          {Icon && <Icon className="w-5 h-5" />}
        </div>
      </div>
      <div className="flex items-baseline gap-2">
        <span className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">{value}</span>
        {trend && (
          <span className="text-xs font-semibold text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded-md">
            {trend}
          </span>
        )}
      </div>
      {subtitle && <p className="text-xs text-slate-500 mt-1 font-medium">{subtitle}</p>}
    </div>
  );
}
