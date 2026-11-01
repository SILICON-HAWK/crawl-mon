// Content for the Architecture page. Describes the pipeline as the app implements it today.
// Columns run left to right; rows stack boxes within a column.

export const LAYOUT = {
  colW: 190,
  rowH: 104,
  nodeW: 160,
  nodeH: 60,
  padX: 24,
  padY: 40,
  viewW: 1728,
  viewH: 470
};

export const GROUPS = {
  source: { label: 'Source', fill: '#eef3dc', stroke: '#8aa45a' },
  collect: { label: 'Collection', fill: '#e2efe9', stroke: '#3f7a6a' },
  store: { label: 'Run store', fill: '#f5eedb', stroke: '#9b7d3d' },
  process: { label: 'Processing', fill: '#ebe8f3', stroke: '#6d62a3' },
  rank: { label: 'Ranking', fill: '#e6f0f5', stroke: '#3d74a0' },
  model: { label: 'Decision model', fill: '#f7e7dc', stroke: '#b56a3c' },
  ui: { label: 'Interface', fill: '#eef7d2', stroke: '#5b8a3c' }
};

export const NODES = [
  {
    id: 'remote-ok',
    label: 'Remote OK feed',
    group: 'source',
    col: 0,
    row: 0,
    summary: 'Public developer job feed used as a seed source.',
    details: [
      'Added as a seed from the Start pipeline form on the Runs page.',
      'Pulled by the feed-refresh worker rather than the crawler.',
      'Listings go through the same normalization as other sources.'
    ]
  },
  {
    id: 'ats',
    label: 'Employer ATS feeds',
    group: 'source',
    col: 0,
    row: 1,
    summary: 'Company job boards on common applicant-tracking systems.',
    details: [
      'Supported systems: Greenhouse, Ashby, Lever, Recruitee, Breezy and Teamtailor.',
      'Feed candidates come from employers of jobs already saved.',
      'Each feed is added as a seed only after you review it.'
    ]
  },
  {
    id: 'wellfound',
    label: 'Wellfound page',
    group: 'source',
    col: 0,
    row: 2,
    summary: 'A page saved by hand and supplied to the pipeline.',
    details: [
      'Saved manually in the browser, then provided as input.',
      'No automated access to the site is assumed.',
      'Enters at extraction, not at the crawler.'
    ]
  },
  {
    id: 'feed-worker',
    label: 'Feed refresh CLI',
    group: 'collect',
    col: 1,
    row: 0,
    summary: 'Command-line worker that refreshes feed sources into runs.',
    details: [
      'Started from the command line, not from the web page.',
      'Reads the configured feed URL and writes the results as a run.',
      'Runs are then read by the rest of the pipeline from the run store.'
    ]
  },
  {
    id: 'crawler',
    label: 'Crawlee adapter',
    group: 'collect',
    col: 1,
    row: 1,
    summary: 'Bounded crawler adapter built on Crawlee.',
    details: [
      'Crawl scope and page budget are bounded for each run.',
      'robots.txt and rate limits are applied before fetching.',
      'Crawlee sits behind a JevScout adapter, so it can be swapped out.'
    ],
    subflow: [
      'Start from the seed URLs of the run.',
      'Follow in-scope links within the budget.',
      'Save each page outcome and its raw page.'
    ]
  },
  {
    id: 'fs-store',
    label: 'Filesystem store',
    group: 'store',
    col: 2,
    row: 1,
    summary: 'Runs, saved pages and results kept as files under data/live-trial.',
    details: [
      'The default backend for the current build.',
      'Run records and saved pages are written as files behind a storage adapter.',
      'Read by the API layer and by extraction.'
    ]
  },
  {
    id: 'pg',
    label: 'PostgreSQL',
    group: 'store',
    col: 2,
    row: 0,
    summary: 'Optional database backend. Not required for local use.',
    details: [
      'Intended as a later backend behind the same storage adapter.',
      'The filesystem store is used first.',
      'Shown dashed because it is optional.'
    ]
  },
  {
    id: 'normalize',
    label: 'Normalize & extract',
    group: 'process',
    col: 3,
    row: 1,
    summary: 'Turns raw listings into one consistent job shape.',
    details: [
      'Resolves company identity from the source data.',
      'Prepares salary text for display.',
      'Checks India location eligibility.'
    ]
  },
  {
    id: 'tech-filter',
    label: 'Tech-job filter',
    group: 'process',
    col: 4,
    row: 1,
    summary: 'Narrows the normalized set to technical roles.',
    details: [
      'Runs after normalization and before pre-rank.',
      'Only jobs that pass this filter are scored.'
    ]
  },
  {
    id: 'prerank',
    label: 'Structured pre-rank',
    group: 'rank',
    col: 5,
    row: 1,
    tag: 'new',
    summary: 'Loose title, location and salary match, scored 0-100. No model.',
    details: [
      'Compares title, location and salary with the candidate profile.',
      'Produces a 0-100 score with title, salary and location parts.',
      'Shows short reasons next to the score.',
      'Makes no model call.'
    ],
    subflow: [
      'Read the title, location and salary fields of the job.',
      'Compare them with the profile target role, preferred locations and minimum salary.',
      'Combine the parts into a 0-100 score and reasons.'
    ]
  },
  {
    id: 'availability',
    label: 'Availability checks',
    group: 'process',
    col: 6,
    row: 1,
    summary: 'Checks whether listing pages still respond. Only when you start it.',
    details: [
      'Started explicitly from the Jobs page with Check listings.',
      'Requests each application URL.',
      'HTTP 200 means the page is reachable, not necessarily that the job is open.'
    ]
  },
  {
    id: 'decision',
    label: 'Decision model',
    group: 'model',
    col: 7,
    row: 1,
    summary: 'OpenRouter analysis of one job, only when you click Analyze.',
    details: [
      'Runs one job at a time, on an explicit click.',
      'Sends the saved profile context and the selected job to OpenRouter.',
      'Results are cached by profile and job.',
      'Dimension scores are shown beside the job.'
    ],
    subflow: [
      'You click Analyze on one job.',
      'Saved profile context and that job are sent to OpenRouter.',
      'Dimension scores come back and are cached by profile and job.',
      'Scores appear beside the job in the review UI.'
    ]
  },
  {
    id: 'profile',
    label: 'Candidate profile',
    group: 'store',
    col: 5,
    row: 3,
    summary: 'Structured fields and freeform context, saved per username.',
    details: [
      'Stored as user-assets/<user>/profile.json.',
      'Structured fields feed the pre-rank.',
      'Freeform context reaches the decision model only when you click Analyze.'
    ]
  },
  {
    id: 'api',
    label: 'FastAPI layer',
    group: 'ui',
    col: 2,
    row: 3,
    summary: 'Local HTTP API between the stores and the Svelte app.',
    details: [
      'GET /api/jobs lists jobs with pre-rank and availability.',
      'POST /api/pipeline starts a collection run.',
      'POST /api/classify runs the decision model for one job.',
      'POST /api/availability/check starts listing checks.',
      '/api/profile reads and saves the profile and job decisions.'
    ]
  },
  {
    id: 'decisions',
    label: 'Job decisions',
    group: 'ui',
    col: 8,
    row: 2,
    summary: 'Interested and not-interested choices, saved per job.',
    details: [
      'Stored in user-assets/<user>/job-actions.json.',
      'Every decision can be reset.',
      'Loaded again on each visit to the Jobs page.'
    ]
  },
  {
    id: 'review',
    label: 'Job review UI',
    group: 'ui',
    col: 8,
    row: 1,
    summary: 'Svelte Jobs page with Reels and Cards review.',
    details: [
      'Reels shows one job at a time; swipe or use the buttons.',
      'Cards shows the same decisions as a grid.',
      'Filter by decision and listing check; sort by best match or newest.'
    ]
  }
];

// from/to are node ids. dashed = optional, or started by the user.
export const EDGES = [
  { from: 'remote-ok', to: 'feed-worker', label: 'feed pull' },
  { from: 'ats', to: 'crawler', label: 'bounded crawl' },
  { from: 'wellfound', to: 'normalize', label: 'manual save', dashed: true },
  { from: 'feed-worker', to: 'fs-store', label: 'writes runs' },
  { from: 'crawler', to: 'fs-store', label: 'writes runs' },
  { from: 'fs-store', to: 'pg', label: 'optional', dashed: true },
  { from: 'fs-store', to: 'normalize', label: 'reads runs' },
  { from: 'normalize', to: 'tech-filter' },
  { from: 'tech-filter', to: 'prerank' },
  { from: 'profile', to: 'prerank', label: 'profile fields' },
  { from: 'prerank', to: 'availability', label: 'you start it', dashed: true },
  { from: 'availability', to: 'decision' },
  { from: 'profile', to: 'decision', label: 'saved context' },
  { from: 'decision', to: 'review', label: 'scores' },
  { from: 'review', to: 'decisions', label: 'yes / no' },
  { from: 'fs-store', to: 'api', label: 'reads' },
  { from: 'api', to: 'review', label: '/api/jobs' },
  { from: 'api', to: 'decision', label: '/api/classify' },
  { from: 'api', to: 'availability', label: '/api/availability' },
  { from: 'api', to: 'profile', label: '/api/profile' }
];
