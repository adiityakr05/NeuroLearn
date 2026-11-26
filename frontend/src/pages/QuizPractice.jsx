import React, { useState, useEffect } from 'react';
import { HelpCircle, CheckCircle2, XCircle, Sparkles, RotateCcw, History, Play } from 'lucide-react';
import { studyService } from '../services/studyService';

export default function QuizPractice() {
  const [subjects, setSubjects] = useState([]);
  const [selectedSubjectId, setSelectedSubjectId] = useState('');
  const [selectedTopicId, setSelectedTopicId] = useState('');
  const [difficulty, setDifficulty] = useState('Medium');
  const [numQuestions, setNumQuestions] = useState(5);

  const [quizData, setQuizData] = useState(null);
  const [answers, setAnswers] = useState({});
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);

  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const init = async () => {
      try {
        setLoading(true);
        const [subs, attempts] = await Promise.all([
          studyService.getSubjects(),
          studyService.getQuizAttempts().catch(() => []),
        ]);
        setSubjects(subs || []);
        setHistory(Array.isArray(attempts) ? attempts : []);
        if (subs && subs.length > 0) {
          setSelectedSubjectId(subs[0].id);
          if (subs[0].topics && subs[0].topics.length > 0) {
            setSelectedTopicId(subs[0].topics[0].id);
          }
        }
      } catch (err) {
        setError(err.message || 'Failed to load subjects');
      } finally {
        setLoading(false);
      }
    };
    init();
  }, []);

  const currentSubject = subjects.find((s) => s.id === selectedSubjectId);
  const availableTopics = currentSubject?.topics || [];

  const handleSubjectChange = (subjId) => {
    setSelectedSubjectId(subjId);
    const subj = subjects.find((s) => s.id === subjId);
    setSelectedTopicId(subj?.topics?.[0]?.id || '');
    setQuizData(null);
    setResult(null);
  };

  const handleStartQuiz = async () => {
    if (!selectedTopicId) {
      setError('Please select a topic first.');
      return;
    }
    try {
      setGenerating(true);
      setError(null);
      setResult(null);
      setAnswers({});
      const data = await studyService.generateQuiz(selectedTopicId, difficulty, Number(numQuestions));
      setQuizData(data);
    } catch (err) {
      setError(err.message || 'Failed to generate quiz');
    } finally {
      setGenerating(false);
    }
  };

  const handleSubmitQuiz = async () => {
    if (!quizData) return;
    const total = quizData.questions.length;
    if (Object.keys(answers).length < total) {
      setError(`Please answer all ${total} questions before submitting.`);
      return;
    }
    try {
      setSubmitting(true);
      setError(null);
      let correct = 0;
      quizData.questions.forEach((q, idx) => {
        if (answers[idx] === q.correctIndex) correct += 1;
      });
      const scorePct = Math.round((correct / total) * 1000) / 10;
      const saved = await studyService.submitQuizAttempt({
        topic_id: selectedTopicId,
        title: `${quizData.topic_name} (${difficulty}) Practice Quiz`,
        total_questions: total,
        correct_answers: correct,
        score: scorePct,
        score_percentage: scorePct,
      });
      setResult({
        score: scorePct,
        correct,
        total,
        criticEvaluated: saved.critic_evaluated,
        criticNotes: saved.critic_notes,
      });
      const updatedHistory = await studyService.getQuizAttempts().catch(() => history);
      if (Array.isArray(updatedHistory)) setHistory(updatedHistory);
    } catch (err) {
      setError(err.message || 'Failed to submit quiz');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <HelpCircle className="w-6 h-6 text-indigo-600" />
            Practice &amp; Diagnostic Quiz
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Test your recall, update topic mastery, and calibrate your Ebbinghaus retention schedule.
          </p>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-700 text-sm font-medium">
          {error}
        </div>
      )}

      {/* Quiz Configuration Card */}
      <div className="bg-white rounded-3xl border border-slate-200/80 p-6 shadow-xs space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1.5">Subject</label>
            <select
              value={selectedSubjectId}
              onChange={(e) => handleSubjectChange(e.target.value)}
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm bg-white"
            >
              {subjects.length === 0 && <option value="">No subjects available</option>}
              {subjects.map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1.5">Topic</label>
            <select
              value={selectedTopicId}
              onChange={(e) => { setSelectedTopicId(e.target.value); setQuizData(null); setResult(null); }}
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm bg-white"
            >
              {availableTopics.length === 0 && <option value="">No topics in subject</option>}
              {availableTopics.map((t) => (
                <option key={t.id} value={t.id}>{t.name} ({t.difficulty})</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1.5">Difficulty</label>
            <select
              value={difficulty}
              onChange={(e) => setDifficulty(e.target.value)}
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm bg-white"
            >
              <option value="Easy">Easy</option>
              <option value="Medium">Medium</option>
              <option value="Hard">Hard</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1.5">Questions</label>
            <select
              value={numQuestions}
              onChange={(e) => setNumQuestions(Number(e.target.value))}
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm bg-white"
            >
              <option value={5}>5 Questions</option>
              <option value={10}>10 Questions</option>
              <option value={15}>15 Questions</option>
              <option value={20}>20 Questions</option>
            </select>
          </div>
        </div>

        <div className="flex justify-end">
          <button
            onClick={handleStartQuiz}
            disabled={generating || !selectedTopicId}
            className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            <Play className="w-4 h-4" />
            {generating ? 'AI is generating your questions...' : quizData ? 'Regenerate Quiz' : 'Start Quiz'}
          </button>
        </div>
      </div>

      {/* Active Quiz Questions */}
      {quizData && (
        <div className="bg-white rounded-3xl border border-slate-200/80 p-6 shadow-xs space-y-6">
          <div className="flex items-center justify-between border-b border-slate-100 pb-4">
            <div>
              <h2 className="text-lg font-bold text-slate-900">{quizData.topic_name} — {quizData.difficulty}</h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Source: <span className="font-semibold text-indigo-600">{quizData.source}</span>
              </p>
            </div>
            <span className="text-xs font-semibold text-slate-500">
              {Object.keys(answers).length} / {quizData.questions.length} answered
            </span>
          </div>

          <div className="space-y-6">
            {quizData.questions.map((q, qIdx) => (
              <div key={q.id || qIdx} className="space-y-3">
                <p className="text-sm font-semibold text-slate-800">
                  {qIdx + 1}. {q.question}
                </p>
                <div className="grid grid-cols-1 gap-2">
                  {q.options.map((opt, oIdx) => {
                    const isSelected = answers[qIdx] === oIdx;
                    const isCorrect = result && q.correctIndex === oIdx;
                    const isWrongSelected = result && isSelected && q.correctIndex !== oIdx;
                    let cls = 'border-slate-200 hover:border-indigo-300 bg-white text-slate-700';
                    if (result) {
                      if (isCorrect) cls = 'border-emerald-500 bg-emerald-50 text-emerald-900 font-medium';
                      else if (isWrongSelected) cls = 'border-rose-500 bg-rose-50 text-rose-900';
                    } else if (isSelected) {
                      cls = 'border-indigo-600 bg-indigo-50 text-indigo-900 font-medium';
                    }
                    return (
                      <button
                        key={oIdx}
                        type="button"
                        disabled={Boolean(result)}
                        onClick={() => setAnswers((prev) => ({ ...prev, [qIdx]: oIdx }))}
                        className={`text-left px-4 py-3 rounded-xl border text-sm transition-colors flex items-center justify-between ${cls}`}
                      >
                        <span>{opt}</span>
                        {result && isCorrect && <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />}
                        {result && isWrongSelected && <XCircle className="w-4 h-4 text-rose-600 shrink-0" />}
                      </button>
                    );
                  })}
                </div>
                {result && q.explanation && (
                  <p className="text-xs text-slate-600 bg-slate-50 px-3 py-2 rounded-lg">
                    <span className="font-semibold">Explanation:</span> {q.explanation}
                  </p>
                )}
              </div>
            ))}
          </div>

          {!result ? (
            <div className="flex justify-end pt-2">
              <button
                onClick={handleSubmitQuiz}
                disabled={submitting}
                className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-6 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                {submitting ? 'Submitting...' : 'Submit Answers'}
              </button>
            </div>
          ) : (
            <div className="rounded-2xl bg-indigo-50 border border-indigo-200 p-5 space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="text-base font-bold text-indigo-950 flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-indigo-600" />
                  Score: {result.score}% ({result.correct}/{result.total} correct)
                </h3>
                <button
                  onClick={handleStartQuiz}
                  className="inline-flex items-center gap-1.5 text-xs font-semibold text-indigo-700 hover:underline"
                >
                  <RotateCcw className="w-3.5 h-3.5" /> Retry Quiz
                </button>
              </div>
              {result.criticNotes && (
                <p className="text-xs text-indigo-900">
                  <span className="font-semibold">Critic Agent Feedback:</span> {result.criticNotes}
                </p>
              )}
            </div>
          )}
        </div>
      )}

      {/* Previous Quiz Attempts */}
      <div className="bg-white rounded-3xl border border-slate-200/80 p-6 shadow-xs space-y-4">
        <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
          <History className="w-5 h-5 text-slate-500" />
          Previous Quiz Attempts
        </h2>
        {history.length === 0 ? (
          <p className="text-sm text-slate-500">No quiz attempts recorded yet. Complete a quiz above to see your history.</p>
        ) : (
          <div className="divide-y divide-slate-100">
            {history.slice(0, 10).map((item) => (
              <div key={item.id} className="py-3 flex items-center justify-between text-sm">
                <div>
                  <p className="font-semibold text-slate-800">{item.title || 'Diagnostic Quiz'}</p>
                  <p className="text-xs text-slate-500">
                    {item.correct_answers}/{item.total_questions} correct • {item.attempted_at ? new Date(item.attempted_at).toLocaleDateString() : 'Recent'}
                  </p>
                </div>
                <span className="font-bold text-indigo-600">{item.score ?? item.accuracy}%</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
