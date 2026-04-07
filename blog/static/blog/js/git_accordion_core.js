/**
 * Git Accordion Core — Toggle and copy functionality
 * Depends on: GitAccordionUtils (git_accordion_utils.js)
 */
(function () {
  'use strict';

  const SELECTORS = {
    root: "#git-accordion-root",
    toggle: ".git-accordion__toggle",
    content: ".git-accordion__content",
    copyBtn: ".copy-btn",
    timestamp: "time[data-timestamp]",
  };

  const ARIA = {
    expanded: "aria-expanded",
    hidden: "aria-hidden",
    controls: "aria-controls",
  };

  function toggleAccordion(toggle) {
    const contentId = toggle.getAttribute(ARIA.controls);
    const content = document.getElementById(contentId);
    if (!content) return;

    const isExpanded = toggle.getAttribute(ARIA.expanded) === "true";
    toggle.setAttribute(ARIA.expanded, !isExpanded);
    content.setAttribute(ARIA.hidden, isExpanded);
  }

  function initAccordion() {
    const root = document.querySelector(SELECTORS.root);
    if (!root) return;

    root.addEventListener("click", (event) => {
      const toggle = event.target.closest(SELECTORS.toggle);
      if (toggle) toggleAccordion(toggle);
    });

    root.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        const toggle = event.target.closest(SELECTORS.toggle);
        if (toggle) {
          event.preventDefault();
          toggleAccordion(toggle);
        }
      }
    });
  }

  function initCopyButtons() {
    const root = document.querySelector(SELECTORS.root);
    if (!root) return;

    root.addEventListener("click", async (event) => {
      const btn = event.target.closest(SELECTORS.copyBtn);
      if (!btn) return;

      event.preventDefault();
      const text = btn.getAttribute("data-clipboard");
      if (!text) return;

      try {
        await navigator.clipboard.writeText(text);
        GitAccordionUtils.showToast("✓ Copied!");
      } catch (error) {
        console.error("Copy failed:", error);
        GitAccordionUtils.showToast("✗ Copy failed");
      }
    });
  }

  function initTimestamps() {
    GitAccordionUtils.updateRelativeTimestamps();
    setInterval(GitAccordionUtils.updateRelativeTimestamps, 60000);
  }

  document.addEventListener('DOMContentLoaded', function () {
    initAccordion();
    initCopyButtons();
    initTimestamps();
  });
})();
