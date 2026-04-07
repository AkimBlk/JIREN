/**
 * Git Accordion Utilities — Timestamps and notifications
 */
const GitAccordionUtils = (function () {
  'use strict';

  const TOAST_DURATION = 1500;

  function getRelativeTime(isoString) {
    if (!isoString) return "";
    const date = new Date(isoString);
    if (isNaN(date.getTime())) return isoString;

    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);

    if (seconds < 60) return "just now";
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;
    if (seconds < 2592000) return `${Math.floor(seconds / 604800)}w ago`;
    if (seconds < 31536000) return `${Math.floor(seconds / 2592000)}mo ago`;
    return `${Math.floor(seconds / 31536000)}y ago`;
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
    }, TOAST_DURATION);
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
