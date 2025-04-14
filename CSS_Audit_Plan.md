# CSS & Frontend Code Audit Plan (April 14, 2025)

**Goal:** Identify the root cause(s) of the persistent CSS styling conflicts and inconsistencies observed in the application, focusing initially on the transcript modal issue on the "Themes & Sentiment" page as the primary symptom, and recommend fixes.

**Context:** Recurring styling issues (e.g., accordion scroll, transcript modal styling) suggest a foundational problem rather than isolated bugs. This audit aims to diagnose these issues without breaking existing features, following guidance in `Project_Summary_Updates.md`.

**Potential Areas of Investigation (Hypotheses):**

1.  **CSS Specificity & Conflicts:** Custom styles in `style.css` conflicting with Bootstrap 5 styles due to selector specificity or use of `!important`.
2.  **JavaScript Interaction & Timing:** JS code manipulating the DOM might interfere with Bootstrap's JS or CSS application timing.
3.  **HTML Structure:** Generated HTML might not precisely match CSS selector expectations, especially within Bootstrap components.
4.  **Asset Loading/Caching:** Browser or server caching could contribute to inconsistencies (less likely primary cause).
5.  **CSS Architecture:** Lack of clear methodology could lead to unintentional style leakage or overrides.

**Audit Plan:**

**Phase 1: Static Code Review & Analysis**

*   **Target Files:**
    *   `app/static/css/style.css`: Review custom styles (modals, cards, lists, transcripts, `!important`, complex selectors).
    *   `app/static/js/themes_sentiment_refactored.js`: Analyze `renderTranscriptInModal`, `showTranscriptModal`, RAG response handling, other DOM manipulation. Check event timing.
    *   `app/static/js/main.js` & `app/static/js/utils.js`: Review global scripts for potential conflicts.
    *   `app/templates/themes_sentiment_refactored.html`: Examine page structure, modal definition (`#transcriptModal`), dynamic content containers.
    *   `app/templates/base.html`: Check global asset loading.
*   **Goal:** Identify potential CSS conflicts, JS timing issues, structural problems, or deviations from best practices directly from the code.

**Phase 2: Dynamic Analysis & Browser Debugging**

*   **Environment:** Development server (`python run.py`) via Replit URL.
*   **Target:** "Themes & Sentiment" page (`/themes-sentiment`), triggering the transcript modal.
*   **Tools:** Browser Developer Tools (Inspector, Console, Network).
*   **Actions:**
    *   **Inspect Styles:** Analyze applied/overridden CSS rules for modal/transcript elements. Check computed styles.
    *   **Inspect DOM:** Examine live DOM structure of the open modal vs. expectations/selectors.
    *   **Debug JavaScript:** Set breakpoints in JS (e.g., `renderTranscriptInModal`) to observe DOM state changes.
    *   **Check Console:** Look for errors/warnings.
    *   **Check Network:** Verify asset loading. Force refresh to rule out simple caching.
*   **Goal:** Observe actual browser behavior, confirm/refute Phase 1 hypotheses, pinpoint style breakdown.

**Phase 3: Isolation & Targeted Testing (If Necessary)**

*   **Actions:**
    *   **Isolate CSS:** Temporarily comment out custom or Bootstrap CSS.
    *   **Isolate Components:** Test transcript bubbles in a minimal HTML file.
    *   **Simplify JS:** Temporarily disable interacting JS.
*   **Goal:** Narrow down conflicts by removing potential interfering factors.

**Deliverables:**

1.  Summary of findings identifying likely root cause(s).
2.  Specific, actionable recommendations for fixes.
3.  Assessment of potential impact on other application parts.

**Status:**

*   [ ] Phase 1: Static Code Review & Analysis
*   [ ] Phase 2: Dynamic Analysis & Browser Debugging
*   [ ] Phase 3: Isolation & Targeted Testing (If Necessary)
*   [ ] Findings Summary & Recommendations