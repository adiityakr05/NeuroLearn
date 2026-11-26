import React, { useState, useEffect } from 'react';
import { Sparkles, Brain, AlertCircle, RefreshCw } from 'lucide-react';
import AgentArchitectureHeader from '../components/recommendations/AgentArchitectureHeader';
import PerformanceElementView from '../components/recommendations/PerformanceElementView';
import CriticElementView from '../components/recommendations/CriticElementView';
import LearningElementView from '../components/recommendations/LearningElementView';
import ProblemGeneratorView from '../components/recommendations/ProblemGeneratorView';
import AgentActivityTimeline from '../components/recommendations/AgentActivityTimeline';
import { studyService } from '../services/studyService';
import { useTimer } from '../context/TimerContext';

export default function Recommendations() {
  const { startTimer } = useTimer();
  const [data, setData] = useState(null);
  const [activeTab, setActiveTab] = useState('performance');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchHubData = async () => {
    try {
      setLoading(true);
      setError(null);
      let res = await studyService.getRecommendationsHubData();
      let active = res?.activeRecommendations || res?.performanceRecommendations || [];
      if (active.length === 0) {
        await studyService.generateRecommendations().catch(() => {});
        res = await studyService.getRecommendationsHubData();
        active = res?.activeRecommendations || res?.performanceRecommendations || [];
      }
      const normalized = active.map((r) => ({
        ...r,
        subject: r.subject || r.subject_name || 'Subject',
        topic: r.topic || r.topic_name || r.title,
        reasonType: r.reasonType || r.reason_type || 'retention_decay',
        reasonDetail: r.reasonDetail || r.reason_detail || '',
        durationMinutes: r.durationMinutes || r.estimated_duration_minutes || 30,
        retentionScore: r.retentionScore ?? r.retention_score ?? 70,
        examUrgency: r.examUrgency || r.suggested_slot || 'Scheduled',
      }));
      setData({
        ...res,
        performanceRecommendations: normalized,
      });
    } catch (err) {
      setError(err.message || 'Failed to load recommendations hub');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHubData();
  }, []);

  const handleAcceptRecommendation = async (recId) => {
    try {
      const rec = data?.performanceRecommendations?.find((r) => r.id === recId);
      if (rec && startTimer) {
        await startTimer({
          subjectId: rec.subject_id,
          subjectName: rec.subject,
          topicId: rec.topic_id,
          topicName: rec.topic || rec.title,
          title: rec.title,
          durationMinutes: rec.durationMinutes || 30,
          recommendationId: rec.id,
        });
      } else {
        await studyService.acceptRecommendation(recId);
      }
      setData((prev) => {
        if (!prev) return prev;
        const updated = prev.performanceRecommendations.filter((r) => r.id !== recId);
        return { ...prev, performanceRecommendations: updated };
      });
    } catch (err) {
      alert('Error starting recommendation: ' + err.message);
    }
  };

  const handleDismissRecommendation = async (recId) => {
    try {
      await studyService.dismissRecommendation(recId);
      setData((prev) => {
        if (!prev) return prev;
        const updated = prev.performanceRecommendations.filter((r) => r.id !== recId);
        return { ...prev, performanceRecommendations: updated };
      });
    } catch (err) {
      alert('Error dismissing recommendation: ' + err.message);
    }
  };

  const handleInspectReason = (rec) => {
    alert(
      `AI Explainability Trace for: ${rec.title}\n\n` +
      `Trigger: ${rec.reasonType}\n` +
      `Estimated Retention: ${rec.retentionScore}%\n` +
      `Exam Countdown: ${rec.examUrgency}\n\n` +
      `Reasoning: ${rec.reasonDetail}`
    );
  };

  const handleStartActivity = (probe) => {
    alert(`Starting Diagnostic Probe: "${probe.title}"\nFormat: ${probe.format} (${probe.durationMinutes} mins)`);
  };

  if (loading && !data) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] space-y-3">
        <div className="w-10 h-10 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin"></div>
        <p className="text-xs font-semibold text-slate-500">
          Loading 4-element learning agent state and recommendations...
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 text-center bg-rose-50 border border-rose-200 rounded-2xl max-w-lg mx-auto my-10">
        <AlertCircle className="w-8 h-8 text-rose-500 mx-auto mb-2" />
        <h3 className="text-base font-bold text-rose-900">Failed to load agent hub</h3>
        <p className="text-xs text-rose-700 mt-1 mb-4">{error}</p>
        <button
          onClick={fetchHubData}
          className="px-4 py-2 bg-rose-600 text-white rounded-xl text-xs font-semibold"
        >
          Retry
        </button>
      </div>
    );
  }

  const {
    agentStatus,
    performanceRecommendations,
    criticEvaluations,
    learningInsights,
    problemGeneratorProbes,
    agentActivityTimeline,
  } = data;

  return (
    <div className="space-y-8">
      {/* Header & Tabs */}
      <AgentArchitectureHeader
        agentStatus={agentStatus}
        activeTab={activeTab}
        onTabChange={setActiveTab}
      />

      {/* Tab Panels */}
      {activeTab === 'performance' && (
        <PerformanceElementView
          recommendations={performanceRecommendations}
          onAccept={handleAcceptRecommendation}
          onDismiss={handleDismissRecommendation}
          onInspectReason={handleInspectReason}
        />
      )}

      {activeTab === 'critic' && (
        <CriticElementView evaluations={criticEvaluations} />
      )}

      {activeTab === 'learning' && (
        <LearningElementView insights={learningInsights} />
      )}

      {activeTab === 'generator' && (
        <ProblemGeneratorView
          probes={problemGeneratorProbes}
          onStartActivity={handleStartActivity}
        />
      )}

      {activeTab === 'timeline' && (
        <AgentActivityTimeline timeline={agentActivityTimeline} />
      )}
    </div>
  );
}
