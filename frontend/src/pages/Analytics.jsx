import React, { useState, useEffect } from 'react';
import {
  LineChart as ChartIcon,
  Sparkles,
  Calendar,
  Filter,
  Brain,
  AlertCircle,
  RefreshCw,
  Info
} from 'lucide-react';
import AnalyticsStatBanner from '../components/analytics/AnalyticsStatBanner';
import RetentionDecayChart from '../components/analytics/RetentionDecayChart';
import QuizPerformanceChart from '../components/analytics/QuizPerformanceChart';
import SubjectMasteryComparison from '../components/analytics/SubjectMasteryComparison';
import RevisionFrequencyWidget from '../components/analytics/RevisionFrequencyWidget';
import { studyService } from '../services/studyService';

export default function Analytics() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters
  const [timeRange, setTimeRange] = useState('30d'); // '14d' | '30d' | 'semester'
  const [subjectFilter, setSubjectFilter] = useState('all');

  const fetchAnalytics = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await studyService.getAnalyticsData(timeRange);
      setData(res);
    } catch (err) {
      setError(err.message || 'Failed to load analytics metrics');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, [timeRange]);

  if (loading && !data) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] space-y-3">
        <div className="w-10 h-10 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin"></div>
        <p className="text-xs font-semibold text-slate-500">
          Calculating Ebbinghaus retention decay curves and mastery statistics...
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 text-center bg-rose-50 border border-rose-200 rounded-2xl max-w-lg mx-auto my-10">
        <AlertCircle className="w-8 h-8 text-rose-500 mx-auto mb-2" />
        <h3 className="text-base font-bold text-rose-900">Failed to load analytics</h3>
        <p className="text-xs text-rose-700 mt-1 mb-4">{error}</p>
        <button
          onClick={fetchAnalytics}
          className="px-4 py-2 bg-rose-600 text-white rounded-xl text-xs font-semibold"
        >
          Retry
        </button>
      </div>
    );
  }

  const {
    summary,
    retentionDecayCurve,
    quizTrends,
    topicQuizPerformance,
    subjectMasteryComparison,
    revisionFrequency,
    overdueList,
  } = data;

  // Filtered quiz trends & topic performance
  const filteredQuizTrends =
    subjectFilter === 'all'
      ? quizTrends
      : quizTrends.filter((q) => q.subject === subjectFilter);

  const filteredTopics =
    subjectFilter === 'all'
      ? topicQuizPerformance
      : topicQuizPerformance.filter((t) => t.subject === subjectFilter);

  return (
    <div className="space-y-8">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-200/80">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
              Cognitive & Performance Analytics
            </h1>
            <span className="hidden sm:inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-100">
              <Sparkles className="w-3.5 h-3.5" />
              Retention Agent Active
            </span>
          </div>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Real-time memory retention decay estimation, recall checks, and mastery trends.
          </p>
        </div>

        {/* Time range & Refresh */}
        <div className="flex items-center gap-2.5 self-start sm:self-auto flex-wrap">
          <div className="flex items-center p-1 bg-slate-200/70 rounded-xl">
            {['14d', '30d', 'semester'].map((range) => (
              <button
                key={range}
                onClick={() => setTimeRange(range)}
                className={`px-3 py-1.5 text-xs font-bold rounded-lg capitalize transition ${
                  timeRange === range
                    ? 'bg-white text-slate-900 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {range === 'semester' ? 'Semester' : range}
              </button>
            ))}
          </div>

          <button
            onClick={fetchAnalytics}
            title="Refresh analytics data"
            className="p-2 bg-white border border-slate-200 text-slate-600 hover:text-slate-900 hover:bg-slate-50 rounded-xl transition"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* ML Integration Architecture Note */}
      <div className="p-4 rounded-2xl bg-indigo-50/60 border border-indigo-100 flex items-start gap-3 text-xs text-indigo-900">
        <Info className="w-4 h-4 text-indigo-600 shrink-0 mt-0.5" />
        <div>
          <span className="font-bold">ML Model & Spaced Repetition Note:</span>
          <p className="text-indigo-800/90 mt-0.5 leading-relaxed">
            The curves below delineate <strong>Predicted Retention Decay</strong> (generated by the prototype retention model) from <strong>Actual Recall Performance</strong> (recorded during real quiz attempts). Once Member 2 finishes calibrating the neural retention weights, this UI will stream real-time inferences without requiring frontend rebuilds.
          </p>
        </div>
      </div>

      {/* Summary KPI Banner */}
      <AnalyticsStatBanner summary={summary} />

      {/* Memory Retention Curve */}
      <RetentionDecayChart data={retentionDecayCurve} />

      {/* Subject Mastery Comparison & Strengths vs Weaknesses */}
      <SubjectMasteryComparison
        data={subjectMasteryComparison}
        onFilterSubject={setSubjectFilter}
        activeSubject={subjectFilter}
      />

      {/* Quiz Performance & Topic Recall Breakdown */}
      <QuizPerformanceChart
        quizTrends={filteredQuizTrends}
        topicBreakdown={filteredTopics}
      />

      {/* Revision Frequency & Overdue Alerts */}
      <RevisionFrequencyWidget
        frequency={revisionFrequency}
        overdueList={overdueList}
      />
    </div>
  );
}
