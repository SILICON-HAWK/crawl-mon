# AI insights toggle

Added a default-on **AI insights** control beside Refresh in the Jobs heading. It hides or shows the current displayed job's already loaded saved decision analysis, including model and dimension output. The control only changes local presentation state; it does not request data or invoke decision analysis. Reels/cards navigation, job actions, and saved decisions remain unchanged.

Affected files:

- `frontend/src/App.svelte`
- `frontend/src/style.css`

Check: `npm run build` (frontend) completed successfully with Vite 6.4.5.

Limitations: visibility resets to on when the app is reloaded; this is intentionally a session-only display preference.
