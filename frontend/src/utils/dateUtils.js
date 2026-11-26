/**
 * Date and Time Utilities for NeuroLearn
 * Provides reliable local-date formatting without UTC timezone drift.
 */

/**
 * Returns a local calendar date string formatted as "YYYY-MM-DD"
 * based on the user's local timezone (avoiding toISOString UTC drift).
 * 
 * @param {Date} [d=new Date()] 
 * @returns {string} e.g. "2026-11-13"
 */
export function getLocalDateString(d = new Date()) {
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

/**
 * Formats a "YYYY-MM-DD" string into an accessible display title.
 * e.g. "Friday, Nov 13, 2026"
 */
export function formatLocalDateTitle(dateStr) {
  if (!dateStr) return '';
  try {
    const [year, month, day] = dateStr.split('-').map(Number);
    if (!year || !month || !day) return dateStr;
    const d = new Date(year, month - 1, day);
    return d.toLocaleDateString('en-US', {
      weekday: 'long',
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  } catch {
    return dateStr;
  }
}

/**
 * Adds or subtracts days from a "YYYY-MM-DD" string reliably.
 */
export function addDaysToDateString(dateStr, days) {
  try {
    const [year, month, day] = dateStr.split('-').map(Number);
    const d = new Date(year, month - 1, day);
    d.setDate(d.getDate() + days);
    return getLocalDateString(d);
  } catch {
    return dateStr;
  }
}
