# Jobs, Runs, and Profile views

The frontend now opens on Jobs and provides simple in-page navigation to Runs and Profile. Jobs loads the array returned by `GET /api/jobs`, offers list and card layouts, displays salary (or “Not disclosed”), available requirements/skills and description, and exposes source/apply links and decision-model analysis. Runs retains pipeline creation, pipeline status, ranked pipeline results, and collected run results. Profile contains the saved candidate context and structured profile editor.

The Jobs view expects each job to include `run_id` and `job_index` for analysis. It posts those values through the existing `POST /api/classify` request, with the current profile username. Saved evaluations are loaded from `GET /api/runs/{run_id}/evaluations` for the current username. Salary is read from the nullable `salary` field supplied by the API; missing values display as “Not disclosed.”
