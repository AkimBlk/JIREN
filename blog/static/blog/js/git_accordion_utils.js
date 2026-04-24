/**
 * Git Accordion Utilities — Timestamps and notifications
 */
// eslint-disable-next-line no-unused-vars
const GitAccordionUtils = (function () {
  'use strict';

  const TOAST_DURATION_MS   = 1500;
  const SECS_PER_MINUTE     = 60;
  const SECS_PER_HOUR       = 3_600;
  const SECS_PER_DAY        = 86_400;
  const SECS_PER_WEEK       = 604_800;
  const SECS_PER_MONTH      = 2_592_000;
  const SECS_PER_YEAR       = 31_536_000;

  function getRelativeTime(isoString) {
    if (!isoString) return "";
    const date = new Date(isoString);
    if (isNaN(date.getTime())) return isoString;

    const seconds = Math.floor((Date.now() - date.getTime()) / 1000);

    if (seconds < SECS_PER_MINUTE) return "just now";
    if (seconds < SECS_PER_HOUR)   return `${Math.floor(seconds / SECS_PER_MINUTE)}m ago`;
    if (seconds < SECS_PER_DAY)    return `${Math.floor(seconds / SECS_PER_HOUR)}h ago`;
    if (seconds < SECS_PER_WEEK)   return `${Math.floor(seconds / SECS_PER_DAY)}d ago`;
    if (seconds < SECS_PER_MONTH)  return `${Math.floor(seconds / SECS_PER_WEEK)}w ago`;
    if (seconds < SECS_PER_YEAR)   return `${Math.floor(seconds / SECS_PER_MONTH)}mo ago`;
    return `${Math.floor(seconds / SECS_PER_YEAR)}y ago`;
  }

  function showToast(message) {
    const toast = document.createElement("div");
    toast.className = "git-accordion-toast";
    toast.textContent = message;
    toast.style.cssText = `
      position: fixed;
      bottom: 16px;
      right: 16px;
      padding: 12px 16px;
      background-color: #1f6feb;
      color: white;
      border-radius: 6px;
      font-size: 0.9rem;
      z-index: 10000;
      box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
      animation: slideInUp 0.3s ease;
    `;

    if (!document.querySelector("style[data-git-accordion-toast]")) {
      const style = document.createElement("style");
      style.setAttribute("data-git-accordion-toast", "true");
      style.textContent = `
        @keyframes slideInUp {
          from { transform: translateY(20px); opacity: 0; }
          to { transform: translateY(0); opacity: 1; }
        }
        @keyframes slideOutDown {
          from { transform: translateY(0); opacity: 1; }
          to { transform: translateY(20px); opacity: 0; }
        }
        .git-accordion-toast.fade-out { animation: slideOutDown 0.3s ease; }
      `;
      document.head.appendChild(style);
    }

    document.body.appendChild(toast);
    setTimeout(() => {
      toast.classList.add("fade-out");
      setTimeout(() => toast.remove(), 300);
    }, TOAST_DURATION_MS);
  }

  function updateRelativeTimestamps() {
    const root = document.querySelector("#git-accordion-root");
    if (!root) return;

    root.querySelectorAll("time[data-timestamp]").forEach((el) => {
      const isoString = el.getAttribute("data-timestamp");
      if (isoString) {
        el.textContent = getRelativeTime(isoString);
        el.title = new Date(isoString).toLocaleString();
      }
    });
  }

  return {
    getRelativeTime,
    showToast,
    updateRelativeTimestamps,
  };
})();
