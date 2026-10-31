# Jobs page, saved scores, and mobile readability

The default Jobs view now contains the job list as its page content. Runs and Profile remain available from the main navigation and show their own page content; the shared intro is limited to Jobs. Job descriptions are not rendered until a user opens them with the per-job Show more/Show less control. Persisted evaluations for the current username are loaded from each job's current and original run references and shown in the job row when available. Evaluation lookup remains read-only and does not trigger model calls. Mobile text sizes and navigation controls are larger for readability.

Affected files: `frontend/src/App.svelte`, `frontend/src/style.css`.

Check: `npm run build` from `frontend/` completed successfully (Vite 6.4.5, 109 modules transformed).

Limitations: Navigation uses `/jobs`, `/runs`, and `/profile` URLs through the History API; `/` also opens Jobs. Browser back and forward restore the matching view. The production server must serve the app shell for these paths. Saved evaluations without timestamps use the API job source order to break ties.
