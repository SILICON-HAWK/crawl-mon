<script>
  import { onMount } from 'svelte';

  let runs = $state([]);
  let pipelines = $state([]);
  let selectedRun = $state(null);
  let results = $state([]);
  let loading = $state(true);
  let busy = $state(false);
  let error = $state('');
  let notice = $state('');
  let seedUrlsText = $state('');
  let profileText = $state(JSON.stringify({
    role_target: 'Software Engineer',
    primary_skills: ['Python'],
    experience_years: 3,
    preferred_locations: ['India'],
    remote_only: false,
    secondary_skills: [],
    min_salary_inr: null
  }, null, 2));
  let selectedPipeline = $state(null);
  let refreshing = $state(false);

  const asList = (value, keys = []) => {
    if (Array.isArray(value)) return value;
    for (const key of keys) if (Array.isArray(value?.[key])) return value[key];
    return [];
  };
  const runId = (run) => run?.id ?? run?.run_id ?? run?.pipeline_id ?? '—';
  const statusOf = (item) => item?.status ?? item?.state ?? 'unknown';
  const titleOf = (item) => item?.name ?? item?.company ?? item?.title ?? item?.label ?? runId(item);
  const shortId = (id) => String(id).length > 18 ? `${String(id).slice(0, 8)}…${String(id).slice(-6)}` : id;
  const dateOf = (item) => item?.created_at ?? item?.started_at ?? item?.updated_at;
  const prettyDate = (value) => value ? new Date(value).toLocaleString() : '—';
  const isObject = (item) => item && typeof item === 'object';
  const pipelineResults = (pipeline) => asList(pipeline?.results ?? pipeline?.ranked_results, ['items', 'jobs', 'evaluations']);
  const matchedSkills = (job) => job?.matched_skills ?? job?.matchedSkills ?? job?.skills_matched ?? [];
  const scoreOf = (job) => job?.composite_score ?? job?.score ?? job?.match_score;

  async function request(path, options = {}) {
    const response = await fetch(path, { ...options, headers: { 'Content-Type': 'application/json', ...options.headers } });
    const raw = await response.text();
    let payload;
    try { payload = raw ? JSON.parse(raw) : null; } catch { payload = raw; }
    if (!response.ok) throw new Error(payload?.detail ?? payload?.message ?? `${response.status} ${response.statusText}`);
    return payload;
  }

  async function refresh(silent = false) {
    if (refreshing) return;
    refreshing = true;
    if (!silent) error = '';
    try {
      const [runData, pipelineData] = await Promise.all([
        request('/api/runs'),
        request('/api/pipeline')
      ]);
      runs = asList(runData, ['runs', 'items', 'results']);
      pipelines = asList(pipelineData, ['pipelines', 'jobs', 'items', 'results']);
      if (selectedRun && !runs.some((item) => runId(item) === runId(selectedRun))) selectedRun = null;
    } catch (e) {
      if (!silent) error = `Could not reach the JevScout API: ${e.message}`;
    } finally {
      loading = false;
      refreshing = false;
    }
  }

  async function showRun(run) {
    selectedRun = run;
    results = [];
    error = '';
    try {
      const data = await request(`/api/runs/${encodeURIComponent(runId(run))}/results`);
      results = asList(data, ['items', 'results', 'jobs']);
    } catch (e) {
      error = `Could not load results: ${e.message}`;
    }
  }

  async function startPipeline() {
    busy = true;
    error = '';
    notice = '';
    try {
      const seed_urls = seedUrlsText.split(/\n|,/).map((url) => url.trim()).filter(Boolean);
      if (!seed_urls.length) throw new Error('Add at least one seed URL to start a pipeline.');
      const profile = profileText.trim() ? JSON.parse(profileText) : {};
      if (!profile || typeof profile !== 'object' || Array.isArray(profile)) throw new Error('Candidate profile must be a JSON object.');
      const body = { seed_urls, profile };
      const created = await request('/api/pipeline', { method: 'POST', body: JSON.stringify(body) });
      const id = runId(created);
      notice = `Pipeline started${id !== '—' ? ` · ${shortId(id)}` : ''}`;
      if (created && typeof created === 'object') pipelines = [created, ...pipelines.filter((p) => runId(p) !== id)];
      await refresh(true);
    } catch (e) {
      error = e instanceof SyntaxError ? 'Candidate profile must be valid JSON.' : e.message.startsWith('Add at least') || e.message.startsWith('Candidate profile') ? e.message : `Could not start pipeline: ${e.message}`;
    } finally {
      busy = false;
    }
  }

  async function inspectPipeline(pipeline) {
    const id = runId(pipeline);
    if (id === '—') return;
    error = '';
    try {
      const detail = await request(`/api/pipeline/${encodeURIComponent(id)}`);
      selectedPipeline = { ...pipeline, ...detail };
      pipelines = pipelines.map((p) => runId(p) === id ? selectedPipeline : p);
    } catch (e) {
      error = `Could not refresh pipeline: ${e.message}`;
    }
  }

  onMount(() => {
    refresh();
    const timer = setInterval(() => refresh(true), 8000);
    return () => clearInterval(timer);
  });
</script>

<svelte:head>
  <meta name="description" content="Local job search runs, pipeline status, and results." />
</svelte:head>

<div class="shell">
  <header class="topbar">
    <a class="brand" href="/" aria-label="JevScout home"><span class="brand-mark">J</span><span>jevscout</span></a>
    <div class="top-actions"><span class="local"><i></i> Local workspace</span><button class="icon-button" onclick={() => refresh()} aria-label="Refresh" title="Refresh">↻</button></div>
  </header>

  <main>
    <section class="intro">
      <div><p class="eyebrow">JOB SEARCH OPERATIONS</p><h1>Good work starts<br /><em>with a clear view.</em></h1><p class="lede">Track collection runs, follow pipeline progress, and review the jobs they find.</p></div>
      <div class="intro-art" aria-hidden="true"><span class="orbit orbit-one"></span><span class="orbit orbit-two"></span><span class="sun"></span><span class="art-label">YOUR NEXT<br />OPPORTUNITY</span></div>
    </section>

    {#if error}<div class="alert" role="alert"><span>!</span>{error}<button onclick={() => error = ''} aria-label="Dismiss">×</button></div>{/if}
    {#if notice}<div class="notice" role="status">✓ {notice}<button onclick={() => notice = ''} aria-label="Dismiss">×</button></div>{/if}

    <section class="start-card">
      <div class="start-copy"><div class="section-icon">↗</div><div><p class="eyebrow">READY WHEN YOU ARE</p><h2>Start a pipeline</h2><p>Choose sources and a candidate profile. Starting collects from those sources and ranks jobs locally using a simple keyword heuristic.</p></div></div>
      <div class="pipeline-form"><label for="seed-urls">Seed URLs <span>one per line</span></label><textarea id="seed-urls" bind:value={seedUrlsText} placeholder="https://example.com/careers" rows="2"></textarea><label for="profile-json">Candidate profile <span>JSON object</span></label><textarea id="profile-json" bind:value={profileText} placeholder={'{}'} rows="2"></textarea></div>
      <button class="primary" onclick={startPipeline} disabled={busy}>{busy ? 'Starting…' : 'Start pipeline'} <span>↗</span></button>
    </section>

    <div class="section-heading"><div><p class="eyebrow">LIVE ACTIVITY</p><h2>Pipeline status</h2></div><span class="updated">Refreshes every 8 seconds</span></div>
    <section class="pipeline-list" aria-label="Pipeline status">
      {#if loading}<div class="empty"><span class="spinner"></span><p>Connecting to your workspace…</p></div>
      {:else if pipelines.length === 0}<div class="empty"><div class="empty-icon">⌁</div><h3>No pipelines yet</h3><p>Start one above to collect and process job listings.</p></div>
      {:else}<div class="table-wrap"><table><thead><tr><th>PIPELINE</th><th>STATUS</th><th>STARTED</th><th></th></tr></thead><tbody>{#each pipelines as pipeline (runId(pipeline))}<tr><td><strong>{titleOf(pipeline)}</strong><small>{shortId(runId(pipeline))}</small></td><td><span class="badge" class:running={['running','in_progress','processing'].includes(statusOf(pipeline).toLowerCase())}>{statusOf(pipeline)}</span></td><td>{prettyDate(dateOf(pipeline))}</td><td><button class="text-button" onclick={() => inspectPipeline(pipeline)}>View results ↻</button></td></tr>{/each}</tbody></table></div>{/if}
      {#if selectedPipeline}<div class="pipeline-detail"><div class="results-title"><div><p class="eyebrow">RANKED RESULTS</p><h3>{titleOf(selectedPipeline)}</h3></div><span class="count">{pipelineResults(selectedPipeline).length} jobs</span></div>
        {#if pipelineResults(selectedPipeline).length}<div class="ranked-list">{#each pipelineResults(selectedPipeline) as job, i (job.id ?? job.job_id ?? job.url ?? i)}<article class="ranked-job"><span class="rank">{String(i + 1).padStart(2, '0')}</span><div class="ranked-main"><div class="job-top"><span class="job-company">{job.company ?? job.company_name ?? job.employer ?? 'Job listing'}</span><span class="job-location">{job.location ?? ''}</span></div><h4>{job.title ?? job.job_title ?? job.name ?? 'Untitled role'}</h4><div class="ranked-meta"><span class="recommendation">{job.recommendation ?? job.tier ?? 'Ranked match'}</span>{#if matchedSkills(job).length}<span>Skills: {Array.isArray(matchedSkills(job)) ? matchedSkills(job).join(', ') : matchedSkills(job)}</span>{/if}<span>{job.provenance?.source_platform ?? job.source_platform ?? job.provenance?.seed_url ?? job.source ?? ''}</span>{#if scoreOf(job) !== undefined}<strong>{Math.round(Number(scoreOf(job)))}<small> / 100</small></strong>{/if}</div>{#if job.url ?? job.application_url}<a href={job.url ?? job.application_url} target="_blank" rel="noreferrer">View job ↗</a>{/if}</div></article>{/each}</div>
        {:else}<div class="empty compact"><h3>No ranked results yet</h3><p>Results will appear when this pipeline finishes scoring.</p></div>{/if}
      </div>{/if}
    </section>

    <div class="section-heading run-heading"><div><p class="eyebrow">COLLECTED WORK</p><h2>Runs &amp; jobs</h2></div><span class="count">{runs.length} {runs.length === 1 ? 'run' : 'runs'}</span></div>
    <section class="runs-layout">
      <div class="run-list" aria-label="Runs">
        {#if !loading && runs.length === 0}<div class="empty compact"><h3>No runs to show</h3><p>Completed and active collection runs appear here.</p></div>{/if}
        {#each runs as run (runId(run))}<button class="run-row" class:selected={selectedRun && runId(selectedRun) === runId(run)} onclick={() => showRun(run)}><span class="run-dot"></span><span class="run-main"><strong>{titleOf(run)}</strong><small>{prettyDate(dateOf(run))}</small></span><span class="badge">{statusOf(run)}</span><span class="arrow">›</span></button>{/each}
      </div>
      <div class="results-panel">
        {#if selectedRun}<div class="results-title"><div><p class="eyebrow">RUN RESULTS</p><h3>{titleOf(selectedRun)}</h3></div><span class="count">{results.length} jobs</span></div>
          {#if results.length}<div class="job-list">{#each results as job, i (job.id ?? job.url ?? i)}<article class="job"><div class="job-top"><span class="job-company">{job.company ?? job.company_name ?? job.employer ?? 'Company'}</span>{#if job.location}<span class="job-location">{job.location}</span>{/if}</div><h4>{job.title ?? job.name ?? 'Untitled role'}</h4>{#if job.description_summary ?? job.description}<p>{job.description_summary ?? job.description}</p>{/if}{#if job.url ?? job.application_url}<a href={job.url ?? job.application_url} target="_blank" rel="noreferrer">View listing ↗</a>{/if}</article>{/each}</div>
          {:else}<div class="empty compact"><div class="empty-icon">⌕</div><h3>No job results</h3><p>This run has not returned any jobs yet.</p></div>{/if}
        {:else}<div class="empty results-empty"><div class="empty-icon">⌖</div><h3>Select a run</h3><p>Choose a run to inspect its job results.</p></div>{/if}
      </div>
    </section>
  </main>
  <footer><span class="brand-small">jevscout</span><span>Built for a more focused job search.</span><span>Local-first · Private by design</span></footer>
</div>
