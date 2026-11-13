import React, { useState, useEffect } from 'react';
import { X, BookOpen, Sparkles } from 'lucide-react';

export default function TopicModal({
  isOpen,
  onClose,
  onSave,
  editingTopic,
  subjectName = '',
}) {
  if (!isOpen) return null;

  const [name, setName] = useState('');
  const [difficulty, setDifficulty] = useState('Medium');
  const [mastery, setMastery] = useState(50);
  const [nextRevision, setNextRevision] = useState('2026-11-20');
  const [completed, setCompleted] = useState(false);

  useEffect(() => {
    if (editingTopic) {
      setName(editingTopic.name || '');
      setDifficulty(editingTopic.difficulty || 'Medium');
      setMastery(editingTopic.mastery ?? 50);
      setNextRevision(editingTopic.nextRevision || '2026-11-20');
      setCompleted(Boolean(editingTopic.completed));
    } else {
      setName('');
      setDifficulty('Medium');
      setMastery(50);
      setNextRevision('2026-11-20');
      setCompleted(false);
    }
  }, [editingTopic, isOpen]);

  const handleSubmit = (e) => {
    e.preventDefault();
    onSave({
      name,
      difficulty,
      mastery: Number(mastery),
      nextRevision,
      completed,
    });
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs">
      <div className="bg-white rounded-3xl max-w-md w-full border border-slate-200 shadow-xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        <div className="p-5 sm:p-6 border-b border-slate-100 flex items-center justify-between">
          <div>
            <span className="text-xs font-bold uppercase tracking-wider text-indigo-600">
              {subjectName}
            </span>
            <h3 className="text-base font-bold text-slate-900 mt-0.5">
              {editingTopic ? 'Edit Topic' : 'Add New Topic'}
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-xl transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 sm:p-6 space-y-4">
          <div>
            <label className="block text-xs font-bold uppercase text-slate-700 mb-1.5">
              Topic Name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Raft Consensus Algorithm"
              className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm font-semibold text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-bold uppercase text-slate-700 mb-1.5">
              Difficulty Rating
            </label>
            <div className="grid grid-cols-3 gap-2">
              {['Easy', 'Medium', 'Hard'].map((diff) => (
                <button
                  type="button"
                  key={diff}
                  onClick={() => setDifficulty(diff)}
                  className={`py-2 text-xs font-bold rounded-xl border transition ${
                    difficulty === diff
                      ? 'bg-slate-900 text-white border-slate-900 shadow-xs'
                      : 'bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100'
                  }`}
                >
                  {diff}
                </button>
              ))}
            </div>
          </div>

          <div>
            <div className="flex justify-between items-center mb-1.5">
              <label className="text-xs font-bold uppercase text-slate-700">
                Initial Mastery Score
              </label>
              <span className="text-xs font-bold text-indigo-600">{mastery}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              value={mastery}
              onChange={(e) => setMastery(e.target.value)}
              className="w-full accent-indigo-600"
            />
            <p className="text-[11px] text-slate-400 mt-1">
              Note: The AI Learning Element continuously calibrates this value based on quiz results and retention intervals.
            </p>
          </div>

          <div>
            <label className="block text-xs font-bold uppercase text-slate-700 mb-1.5">
              Target Revision Date
            </label>
            <input
              type="date"
              value={nextRevision}
              onChange={(e) => setNextRevision(e.target.value)}
              className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm font-semibold text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
              required
            />
          </div>

          <div className="flex items-center gap-2 pt-1">
            <input
              type="checkbox"
              id="completedCheck"
              checked={completed}
              onChange={(e) => setCompleted(e.target.checked)}
              className="w-4 h-4 rounded text-indigo-600 focus:ring-indigo-500 border-slate-300"
            />
            <label htmlFor="completedCheck" className="text-xs font-semibold text-slate-700">
              Mark as already completed initially
            </label>
          </div>

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
              className="px-5 py-2.5 rounded-xl bg-indigo-600 text-white text-xs font-bold hover:bg-indigo-700 transition shadow-xs"
            >
              {editingTopic ? 'Save Changes' : 'Add Topic'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
