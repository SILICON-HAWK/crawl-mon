<script>
  import { onMount } from 'svelte';

  let runs = $state([]);
  let jobs = $state([]);
  let activePage = $state('Home');
  let jobsLoading = $state(true);
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
  let profileUsername = $state('abhi');
  let profileContext = $state('');
  let profileFields = $state({ role_target: '', primary_skills: [], experience_years: '', preferred_locations: [], remote_only: false, secondary_skills: [], min_salary_inr: '' });
  let profileBusy = $state(false);
  let profileNotice = $state('');
  let profileError = $state('');
  let primarySkillsText = $state('');
  let secondarySkillsText = $state('');
  let preferredLocationsText = $state('');
  let resultsView = $state('list');
  let classifications = $state({});
  let expandedDescriptions = $state({});
  let classifying = $state({});
  let selectedPipeline = $state(null);
  let refreshing = $state(false);
  let jobActions = $state({});
  let jobMode = $state('reels');
  let jobBucket = $state('all');
  let activeJobIndex = $state(0);
  let pointerStart = null;

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
  const requirementsOf = (job) => {
    const supplied = job?.requirements ?? job?.required_skills ?? job?.skills ?? job?.qualifications;
    if (supplied) return supplied;
    const text = String(job?.description ?? '');
    const match = /(?:requirements|qualifications|what you(?:’|'| a)ll bring|what we(?:’|'| a)re looking for)/i.exec(text);
    return match ? text.slice(match.index, match.index + 500) : null;
  };
  const summaryOf = (job) => job?.description_summary ?? job?.description ?? job?.summary ?? '';
  const scoreOf = (job) => job?.composite_score ?? job?.score ?? job?.match_score;
  const scoringStats = (job) => job?.scoring_stats ?? job?.scoring_breakdown ?? job?.score_components ?? job?.decision_stats ?? null;
  const sourceUrlOf = (job) => job?.source_url ?? job?.provenance?.source_url ?? job?.provenance?.seed_url ?? job?.seed_url ?? null;
  const applyUrlOf = (job) => job?.application_url ?? job?.apply_url ?? job?.url ?? null;
  const jobUrlOf = (job) => job?.url ?? job?.application_url ?? job?.apply_url ?? job?.source_url ?? null;
  const listText = (value) => String(value ?? '').split(/\n|,/).map((part) => part.trim()).filter(Boolean);
  const niceKey = (key) => String(key).replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
  const pageFromPath = (path) => ({ '/': 'Home', '/jobs': 'Jobs', '/runs': 'Runs', '/profile': 'Profile' })[path] ?? 'Jobs';

  function navigate(page, event) {
    event?.preventDefault();
    const path = { Home: '/', Jobs: '/jobs', Runs: '/runs', Profile: '/profile' }[page];
    if (location.pathname !== path) history.pushState({}, '', path);
    activePage = page;
  }

  function syncPageFromLocation() {
    activePage = pageFromPath(location.pathname);
  }

  async function loadProfile() {
    profileError = '';
    jobActions = {};
    activeJobIndex = 0;
    try {
      const data = await request(`/api/profile/${encodeURIComponent(profileUsername.trim())}`);
      profileContext = data?.freeform_context ?? '';
      profileFields = { ...profileFields, ...(data?.structured_fields ?? {}) };
      primarySkillsText = (profileFields.primary_skills ?? []).join(', ');
      secondarySkillsText = (profileFields.secondary_skills ?? []).join(', ');
      preferredLocationsText = (profileFields.preferred_locations ?? []).join(', ');
      profileText = JSON.stringify({ role_target: profileFields.role_target, primary_skills: profileFields.primary_skills, experience_years: profileFields.experience_years, preferred_locations: profileFields.preferred_locations, remote_only: profileFields.remote_only, secondary_skills: profileFields.secondary_skills, min_salary_inr: profileFields.min_salary_inr }, null, 2);
    } catch (e) {
      profileError = `Could not load profile: ${e.message}`;
    }
    if (jobs.length) await loadJobActions();
  }

  async function saveProfile() {
    profileBusy = true;
    profileNotice = '';
    profileError = '';
    try {
      if (!profileUsername.trim()) throw new Error('Enter a profile username.');
      const structured_fields = {
        ...profileFields,
        primary_skills: listText(primarySkillsText),
        secondary_skills: listText(secondarySkillsText),
        preferred_locations: listText(preferredLocationsText),
        experience_years: profileFields.experience_years === '' ? null : Number(profileFields.experience_years),
        min_salary_inr: profileFields.min_salary_inr === '' ? null : Number(profileFields.min_salary_inr)
      };
      if (structured_fields.experience_years !== null && !Number.isFinite(structured_fields.experience_years)) throw new Error('Experience must be a number.');
      if (structured_fields.min_salary_inr !== null && !Number.isFinite(structured_fields.min_salary_inr)) throw new Error('Minimum salary must be a number.');
      const saved = await request(`/api/profile/${encodeURIComponent(profileUsername.trim())}`, { method: 'PUT', body: JSON.stringify({ freeform_context: profileContext, structured_fields }) });
      profileFields = { ...structured_fields, ...(saved?.structured_fields ?? {}) };
      profileContext = saved?.freeform_context ?? profileContext;
      profileNotice = `Profile “${profileUsername.trim()}” saved.`;
      profileText = JSON.stringify({ role_target: profileFields.role_target, primary_skills: profileFields.primary_skills, experience_years: profileFields.experience_years, preferred_locations: profileFields.preferred_locations, remote_only: profileFields.remote_only, secondary_skills: profileFields.secondary_skills, min_salary_inr: profileFields.min_salary_inr }, null, 2);
    } catch (e) {
      profileError = `Could not save profile: ${e.message}`;
    } finally { profileBusy = false; }
  }

  async function classifyJob(job, run, index) {
    const id = runId(run);
    const jobIdIndex = job?.job_id == null ? NaN : Number(String(job.job_id).split(':').at(-1));
    const job_index = Number(job?.job_index ?? (Number.isInteger(jobIdIndex) ? jobIdIndex : index));
    if (!Number.isInteger(job_index) || job_index < 0) {
      classifications = { ...classifications, [`${id}:${index}`]: { error: 'This result has no usable job index.' } };
      return;
    }
    const key = `${id}:${index}`;
    classifying = { ...classifying, [key]: true };
    classifications = { ...classifications, [key]: null };
    try {
      const data = await request('/api/classify', { method: 'POST', body: JSON.stringify({ username: profileUsername.trim() || 'default', run_id: job?.run_id ?? id, job_index }) });
      classifications = { ...classifications, [key]: data };
    } catch (e) {
      classifications = { ...classifications, [key]: { error: e.message } };
    } finally {
      classifying = { ...classifying, [key]: false };
    }
  }

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

  async function loadJobs() {
    jobsLoading = true;
    try {
      const data = await request('/api/jobs');
      jobs = asList(data, ['jobs', 'items', 'results']);
      await loadJobActions();
      const runIds = [...new Set(jobs.flatMap((job) => [job?.run_id, ...asList(job?.originals).map((original) => original?.run_id)]).filter(Boolean))];
      const evaluations = await Promise.allSettled(runIds.map((id) => request(`/api/runs/${encodeURIComponent(id)}/evaluations`)));
      const entriesBySource = new Map();
      for (let i = 0; i < evaluations.length; i += 1) if (evaluations[i].status === 'fulfilled') {
        for (const entry of asList(evaluations[i].value)) if (entry.username === profileUsername.trim() && Number.isInteger(entry.job_index)) {
          entriesBySource.set(`${entry.run_id ?? runIds[i]}:${entry.job_index}`, entry);
        }
      }
      const saved = { ...classifications };
      for (const job of jobs) {
        const key = `${job.run_id}:${Number(job.job_index)}`;
        const sources = [{ run_id: job.run_id, job_index: job.job_index }, ...asList(job.originals)];
        const matches = sources.map((source) => entriesBySource.get(`${source.run_id}:${source.job_index}`)).filter(Boolean);
        if (matches.length) saved[key] = matches.reduce((latest, entry) => {
          const currentTime = Date.parse(entry.updated_at ?? entry.created_at ?? '') || 0;
          const latestTime = Date.parse(latest.updated_at ?? latest.created_at ?? '') || 0;
          return currentTime > latestTime ? entry : latest;
        });
      }
      classifications = saved;
    } catch (e) {
      error = `Could not load jobs: ${e.message}`;
    } finally { jobsLoading = false; }
  }

  async function loadJobActions() {
    try {
      const data = await request(`/api/profile/${encodeURIComponent(profileUsername.trim() || 'default')}/job-actions`);
      const records = Array.isArray(data) ? data : asList(data, ['actions', 'items', 'results']);
      const mapped = { ...jobActions };
      for (const [url, status] of Object.entries(data?.actions ?? data ?? {})) mapped[url] = typeof status === 'string' ? status : status?.status;
      for (const action of records) if (action?.job_url) mapped[action.job_url] = action.status;
      jobActions = mapped;
    } catch (e) { error = `Could not load saved job decisions: ${e.message}`; }
  }

  async function setJobAction(job, status) {
    const url = jobUrlOf(job);
    if (!url) return;
    const previous = jobActions[url];
    if (status === 'unset') { const next = { ...jobActions }; delete next[url]; jobActions = next; }
    else jobActions = { ...jobActions, [url]: status };
    try {
      await request(`/api/profile/${encodeURIComponent(profileUsername.trim() || 'default')}/job-actions`, { method: 'PUT', body: JSON.stringify({ job_url: url, status }) });
      if (status === 'unset') { const next = { ...jobActions }; delete next[url]; jobActions = next; }
      if (jobBucket === 'all' && status !== 'unset' && activeJobIndex < filteredJobs.length - 1) activeJobIndex += 1;
      else activeJobIndex = Math.min(activeJobIndex, Math.max(0, filteredJobs.length - 1));
    } catch (e) {
      jobActions = { ...jobActions, [url]: previous };
      error = `Could not save job decision: ${e.message}`;
    }
  }

  let filteredJobs = $derived(jobs.filter((job) => jobBucket === 'all' || jobActions[jobUrlOf(job)] === (jobBucket === 'interested' ? 'interested' : 'not_interested')));
  function swipeStart(event) { if (event.target.closest('button, a, details')) { pointerStart = null; return; } pointerStart = { x: event.clientX, y: event.clientY }; }
  function swipeEnd(event, job) {
    if (!pointerStart) return;
    const dx = event.clientX - pointerStart.x;
    const dy = event.clientY - pointerStart.y;
    pointerStart = null;
    if (jobMode === 'reels' && Math.abs(dy) > 65 && Math.abs(dy) > Math.abs(dx)) activeJobIndex = Math.max(0, Math.min(filteredJobs.length - 1, activeJobIndex + (dy < 0 ? 1 : -1)));
    else if (jobMode === 'cards' && Math.abs(dx) > 65 && Math.abs(dx) > Math.abs(dy) && jobUrlOf(job)) setJobAction(job, dx > 0 ? 'interested' : 'not_interested');
  }

  async function showRun(run) {
    selectedRun = run;
    results = [];
    error = '';
    try {
      const data = await request(`/api/runs/${encodeURIComponent(runId(run))}/results`);
      results = asList(data, ['items', 'results', 'jobs']);
      const saved = await request(`/api/runs/${encodeURIComponent(runId(run))}/evaluations`);
      for (const entry of asList(saved)) { if (entry.username === profileUsername.trim() && Number.isInteger(entry.job_index)) classifications = { ...classifications, [`${runId(run)}:${entry.job_index}`]: entry }; }
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
      const profile = {
        role_target: profileFields.role_target,
        primary_skills: listText(primarySkillsText),
        experience_years: profileFields.experience_years === '' ? null : Number(profileFields.experience_years),
        preferred_locations: listText(preferredLocationsText),
        remote_only: profileFields.remote_only,
        secondary_skills: listText(secondarySkillsText),
        min_salary_inr: profileFields.min_salary_inr === '' ? null : Number(profileFields.min_salary_inr)
      };
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
    syncPageFromLocation();
    window.addEventListener('popstate', syncPageFromLocation);
    refresh();
    loadJobs();
    loadProfile();
    const timer = setInterval(() => refresh(true), 8000);
    return () => {
      clearInterval(timer);
      window.removeEventListener('popstate', syncPageFromLocation);
    };
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
    {#if error}<div class="alert" role="alert"><span>!</span>{error}<button onclick={() => error = ''} aria-label="Dismiss">×</button></div>{/if}
    {#if notice}<div class="notice" role="status">✓ {notice}<button onclick={() => notice = ''} aria-label="Dismiss">×</button></div>{/if}
    <nav class="page-nav" aria-label="Main navigation">{#each ['Home', 'Jobs', 'Runs', 'Profile'] as page}<a class:active={activePage === page} href={{ Home: '/', Jobs: '/jobs', Runs: '/runs', Profile: '/profile' }[page]} aria-current={activePage === page ? 'page' : undefined} onclick={(event) => navigate(page, event)}>{page}</a>{/each}</nav>
    {#if activePage === 'Home'}
    <section class="intro">
      <div><p class="eyebrow">YOUR OPPORTUNITIES</p><h1>Good work starts<br /><em>with a clear view.</em></h1><p class="lede">Review the roles collected for your search and see their saved decision scores.</p><a class="primary intro-cta" href="/jobs" onclick={(event) => navigate('Jobs', event)}>Explore jobs ↗</a></div>
      <div class="intro-art" aria-hidden="true"><span class="orbit orbit-one"></span><span class="orbit orbit-two"></span><span class="sun"></span><span class="art-label">YOUR NEXT<br />OPPORTUNITY</span></div>
    </section>
    {:else if activePage === 'Jobs'}
    <div class="section-heading jobs-heading"><div><p class="eyebrow">YOUR OPPORTUNITIES</p><h2>Jobs</h2></div><div class="results-tools"><span class="count">{filteredJobs.length} of {jobs.length} jobs</span><div class="view-toggle" aria-label="Jobs view"><button class:active={jobMode === 'reels'} onclick={() => jobMode = 'reels'} aria-pressed={jobMode === 'reels'}>Reels</button><button class:active={jobMode === 'cards'} onclick={() => jobMode = 'cards'} aria-pressed={jobMode === 'cards'}>Cards</button></div><button class="text-button" onclick={loadJobs}>Refresh ↻</button></div></div>
    <div class="job-filters" aria-label="Filter jobs">{#each [['all','All'],['interested','Interested'],['not_interested','Not interested']] as [key,label]}<button class:active={jobBucket === key} aria-pressed={jobBucket === key} onclick={() => { jobBucket = key; activeJobIndex = 0; }}>{label}{#if key === 'interested'} <span>{jobs.filter(j => jobActions[jobUrlOf(j)] === 'interested').length}</span>{:else if key === 'not_interested'} <span>{jobs.filter(j => jobActions[jobUrlOf(j)] === 'not_interested').length}</span>{/if}</button>{/each}</div>
    {#if jobsLoading}<div class="empty"><span class="spinner"></span><p>Loading jobs…</p></div>
    {:else if filteredJobs.length}{@const job = filteredJobs[Math.min(activeJobIndex, filteredJobs.length - 1)]}{@const url = jobUrlOf(job)}<section class="reel-stage" aria-label="Job review"><div class="reel-progress" aria-label={`Job ${activeJobIndex + 1} of ${filteredJobs.length}`}><span class:done={activeJobIndex > 0} class:current={true}></span></div><article class="reel-job" class:card-mode={jobMode === 'cards'} onpointerdown={swipeStart} onpointerup={(event) => swipeEnd(event, job)}><div class="job-top"><span class="job-company">{job.company ?? job.company_name ?? job.employer ?? 'Company'}</span>{#if job.location}<span class="job-location">{job.location}</span>{/if}</div><h3>{job.title ?? job.job_title ?? job.name ?? 'Untitled role'}</h3><p class="job-detail"><strong>Salary</strong> {job.salary ?? 'Not disclosed'}</p>{#if requirementsOf(job)}<p class="job-detail"><strong>Requirements / skills</strong> {Array.isArray(requirementsOf(job)) ? requirementsOf(job).join(', ') : requirementsOf(job)}</p>{:else if matchedSkills(job).length}<p class="job-detail"><strong>Skills</strong> {Array.isArray(matchedSkills(job)) ? matchedSkills(job).join(', ') : matchedSkills(job)}</p>{/if}<div class="job-links">{#if sourceUrlOf(job)}<a href={sourceUrlOf(job)} target="_blank" rel="noreferrer">Source listing ↗</a>{/if}{#if applyUrlOf(job)}<a href={applyUrlOf(job)} target="_blank" rel="noreferrer">Apply ↗</a>{/if}</div><button class="analyze-button" onclick={() => classifyJob(job, {id: job.run_id ?? runId(job)}, Number(job.job_index ?? 0))} disabled={classifying[`${job.run_id ?? runId(job)}:${Number(job.job_index ?? 0)}`]}>Analyze with decision model</button>{#if classifications[`${job.run_id ?? runId(job)}:${Number(job.job_index ?? 0)}`]}<div class="decision-result">{#if classifications[`${job.run_id ?? runId(job)}:${Number(job.job_index ?? 0)}`]?.error}<span class="decision-error">Analysis failed: {classifications[`${job.run_id ?? runId(job)}:${Number(job.job_index ?? 0)}`].error}</span>{:else}<span class="model-label">Decision model: {classifications[`${job.run_id ?? runId(job)}:${Number(job.job_index ?? 0)}`]?.model ?? 'unknown'}</span>{#if classifications[`${job.run_id ?? runId(job)}:${Number(job.job_index ?? 0)}`]?.dimensions}<div class="score-stats">{#each Object.entries(classifications[`${job.run_id ?? runId(job)}:${Number(job.job_index ?? 0)}`].dimensions) as [key, value]}<span>{niceKey(key)}: {typeof value === 'number' ? `${Math.round(value * (value <= 1 ? 100 : 1))}%` : String(value)}</span>{/each}</div>{/if}{/if}</div>{/if}{#if summaryOf(job)}<details class="job-description"><summary>Show description</summary><p>{summaryOf(job)}</p></details>{/if}<div class="reel-actions"><button class="action-no" onclick={() => setJobAction(job, 'not_interested')} disabled={!url} aria-label="Not interested">× <span>Not interested</span></button><button class="action-yes" onclick={() => setJobAction(job, 'interested')} disabled={!url} aria-label="Interested">♥ <span>Interested</span></button></div>{#if url && jobActions[url]}<button class="reset-decision" onclick={() => setJobAction(job, 'unset')}>Reset decision ({jobActions[url] === 'interested' ? 'Interested' : 'Not interested'})</button>{/if}{#if !url}<p class="no-job-url">Decision buttons unavailable: this job has no URL.</p>{/if}</article><div class="reel-nav"><button class="text-button" onclick={() => activeJobIndex = Math.max(0, activeJobIndex - 1)} disabled={activeJobIndex === 0}>← Previous</button><span>{activeJobIndex + 1} / {filteredJobs.length}{jobMode === 'reels' ? ' · swipe vertically' : ' · swipe to decide'}</span><button class="text-button" onclick={() => activeJobIndex = Math.min(filteredJobs.length - 1, activeJobIndex + 1)} disabled={activeJobIndex >= filteredJobs.length - 1}>Next →</button></div></section>
    {:else}<div class="empty"><h3>{jobs.length ? 'No jobs in this bucket' : 'No jobs found'}</h3><p>{jobs.length ? 'Try another decision filter or mark a job in a different bucket.' : 'Jobs collected by your runs will appear here.'}</p></div>{/if}
    {:else if activePage === 'Profile'}
    <div class="section-heading"><div><p class="eyebrow">YOUR SEARCH SETTINGS</p><h2>Candidate profile</h2></div><span class="updated">Saved per username</span></div>
    {#if profileError}<div class="alert" role="alert"><span>!</span>{profileError}<button onclick={() => profileError = ''} aria-label="Dismiss">×</button></div>{/if}
    {#if profileNotice}<div class="notice" role="status">✓ {profileNotice}<button onclick={() => profileNotice = ''} aria-label="Dismiss">×</button></div>{/if}
    <section class="profile-card">
      <div class="profile-top"><div><p class="eyebrow">PROFILE</p><h3>Tell JevScout what you’re looking for</h3></div><label class="profile-user">Username<input bind:value={profileUsername} onchange={loadProfile} autocomplete="username" /></label></div>
      <label class="field-label" for="freeform-context">Freeform context</label><textarea id="freeform-context" class="context-input" bind:value={profileContext} placeholder="Describe your experience, strengths, goals, constraints, and the kinds of roles you want…" rows="4"></textarea>
      <div class="profile-fields">
        <label>Target role<input bind:value={profileFields.role_target} placeholder="e.g. Product Designer" /></label>
        <label>Experience (years)<input type="number" min="0" step="0.5" bind:value={profileFields.experience_years} /></label>
        <label>Primary skills <span>comma separated</span><input bind:value={primarySkillsText} placeholder="Python, SQL, ..." /></label>
        <label>Secondary skills <span>comma separated</span><input bind:value={secondarySkillsText} placeholder="Figma, AWS, ..." /></label>
        <label>Preferred locations <span>comma separated</span><input bind:value={preferredLocationsText} placeholder="India, Remote, ..." /></label>
        <label>Minimum salary (INR)<input type="number" min="0" step="1000" bind:value={profileFields.min_salary_inr} placeholder="Optional" /></label>
      </div>
      <label class="check-field"><input type="checkbox" bind:checked={profileFields.remote_only} /> Remote roles only</label>
      <div class="profile-actions"><span>Used when ranking jobs. Analysis sends your saved context and the selected job to OpenRouter only after you choose Analyze.</span><button class="primary" onclick={saveProfile} disabled={profileBusy}>{profileBusy ? 'Saving…' : 'Save profile'} <span>✓</span></button></div>
    </section>
    {:else}
    <section class="start-card">
      <div class="start-copy"><div class="section-icon">↗</div><div><p class="eyebrow">READY WHEN YOU ARE</p><h2>Start a pipeline</h2><p>Choose sources and a candidate profile. Starting collects from those sources and ranks jobs locally using a simple keyword heuristic.</p></div></div>
      <div class="pipeline-form"><label for="seed-urls">Seed URLs <span>one per line</span></label><textarea id="seed-urls" bind:value={seedUrlsText} placeholder="https://example.com/careers" rows="2"></textarea><p class="profile-hint">The initial local ranking uses your structured profile. Decision analysis uses your saved context.</p></div>
      <button class="primary" onclick={startPipeline} disabled={busy}>{busy ? 'Starting…' : 'Start pipeline'} <span>↗</span></button>
    </section>



    <div class="section-heading"><div><p class="eyebrow">LIVE ACTIVITY</p><h2>Pipeline status</h2></div><span class="updated">Refreshes every 8 seconds</span></div>
    <section class="pipeline-list" aria-label="Pipeline status">
      {#if loading}<div class="empty"><span class="spinner"></span><p>Connecting to your workspace…</p></div>
      {:else if pipelines.length === 0}<div class="empty"><div class="empty-icon">⌁</div><h3>No pipelines yet</h3><p>Start one above to collect and process job listings.</p></div>
      {:else}<div class="table-wrap"><table><thead><tr><th>PIPELINE</th><th>STATUS</th><th>STARTED</th><th></th></tr></thead><tbody>{#each pipelines as pipeline (runId(pipeline))}<tr><td><strong>{titleOf(pipeline)}</strong><small>{shortId(runId(pipeline))}</small></td><td><span class="badge" class:running={['running','in_progress','processing'].includes(statusOf(pipeline).toLowerCase())}>{statusOf(pipeline)}</span></td><td>{prettyDate(dateOf(pipeline))}</td><td><button class="text-button" onclick={() => inspectPipeline(pipeline)}>View results ↻</button></td></tr>{/each}</tbody></table></div>{/if}
      {#if selectedPipeline}<div class="pipeline-detail"><div class="results-title"><div><p class="eyebrow">RANKED RESULTS</p><h3>{titleOf(selectedPipeline)}</h3></div><div class="results-tools"><span class="count">{pipelineResults(selectedPipeline).length} jobs</span><div class="view-toggle" aria-label="Results view"><button class:active={resultsView === 'list'} onclick={() => resultsView = 'list'} aria-pressed={resultsView === 'list'}>List</button><button class:active={resultsView === 'cards'} onclick={() => resultsView = 'cards'} aria-pressed={resultsView === 'cards'}>Cards</button></div></div></div>
        {#if pipelineResults(selectedPipeline).length}<div class="ranked-list" class:card-view={resultsView === 'cards'}>{#each pipelineResults(selectedPipeline) as job, i (job.id ?? job.job_id ?? job.url ?? i)}<article class="ranked-job"><span class="rank">{String(i + 1).padStart(2, '0')}</span><div class="ranked-main"><div class="job-top"><span class="job-company">{job.company ?? job.company_name ?? job.employer ?? 'Job listing'}</span><span class="job-location">{job.location ?? ''}</span></div><h4>{job.title ?? job.job_title ?? job.name ?? 'Untitled role'}</h4><div class="ranked-meta"><span class="recommendation">{job.recommendation ?? job.tier ?? 'Ranked match'}</span>{#if matchedSkills(job).length}<span>Skills: {Array.isArray(matchedSkills(job)) ? matchedSkills(job).join(', ') : matchedSkills(job)}</span>{/if}<span>{job.provenance?.source_platform ?? job.source_platform ?? job.source ?? ''}</span>{#if scoreOf(job) !== undefined}<strong>{Math.round(Number(scoreOf(job)))}<small> / 100</small></strong>{/if}</div>
        {#if scoringStats(job)}<div class="score-stats">{#each Object.entries(scoringStats(job)) as [key, value]}<span>{niceKey(key)}: {typeof value === 'number' ? `${Math.round(value * (value <= 1 ? 100 : 1))}%` : String(value)}</span>{/each}</div>{/if}
        <div class="job-links">{#if sourceUrlOf(job)}<a href={sourceUrlOf(job)} target="_blank" rel="noreferrer">Source listing ↗</a>{/if}{#if applyUrlOf(job)}<a href={applyUrlOf(job)} target="_blank" rel="noreferrer">Apply ↗</a>{/if}</div>
        <button class="analyze-button" onclick={() => classifyJob(job, selectedPipeline, i)} disabled={classifying[`${runId(selectedPipeline)}:${i}`]}>{classifying[`${runId(selectedPipeline)}:${i}`] ? 'Analyzing…' : 'Analyze with decision model'}</button>
        {#if classifications[`${runId(selectedPipeline)}:${i}`]}{@const decision = classifications[`${runId(selectedPipeline)}:${i}`]}<div class="decision-result">{#if decision.error}<span class="decision-error">Analysis failed: {decision.error}</span>{:else}<span class="model-label">Decision model: {decision.model ?? 'unknown'}</span>{#if decision.dimensions}<div class="score-stats">{#each Object.entries(decision.dimensions) as [key, value]}<span>{niceKey(key)}: {typeof value === 'number' ? `${Math.round(value * (value <= 1 ? 100 : 1))}%` : String(value)}</span>{/each}</div>{/if}{/if}</div>{/if}
        </div></article>{/each}</div>
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
        {#if selectedRun}<div class="results-title"><div><p class="eyebrow">RUN RESULTS</p><h3>{titleOf(selectedRun)}</h3></div><div class="results-tools"><span class="count">{results.length} jobs</span><div class="view-toggle" aria-label="Results view"><button class:active={resultsView === 'list'} onclick={() => resultsView = 'list'} aria-pressed={resultsView === 'list'}>List</button><button class:active={resultsView === 'cards'} onclick={() => resultsView = 'cards'} aria-pressed={resultsView === 'cards'}>Cards</button></div></div></div>
          {#if results.length}<div class="job-list" class:card-view={resultsView === 'cards'}>{#each results as job, i (job.id ?? job.url ?? i)}<article class="job"><div class="job-top"><span class="job-company">{job.company ?? job.company_name ?? job.employer ?? 'Company'}</span>{#if job.location}<span class="job-location">{job.location}</span>{/if}</div><h4>{job.title ?? job.name ?? 'Untitled role'}</h4>{#if job.description_summary ?? job.description}<p>{job.description_summary ?? job.description}</p>{/if}<div class="job-links">{#if sourceUrlOf(job)}<a href={sourceUrlOf(job)} target="_blank" rel="noreferrer">Source listing ↗</a>{/if}{#if applyUrlOf(job)}<a href={applyUrlOf(job)} target="_blank" rel="noreferrer">Apply ↗</a>{/if}</div><button class="analyze-button" onclick={() => classifyJob(job, selectedRun, i)} disabled={classifying[`${runId(selectedRun)}:${i}`]}>{classifying[`${runId(selectedRun)}:${i}`] ? 'Analyzing…' : 'Analyze with decision model'}</button>{#if classifications[`${runId(selectedRun)}:${i}`]}{@const decision = classifications[`${runId(selectedRun)}:${i}`]}<div class="decision-result">{#if decision.error}<span class="decision-error">Analysis failed: {decision.error}</span>{:else}<span class="model-label">Decision model: {decision.model ?? 'unknown'}</span>{#if decision.dimensions}<div class="score-stats">{#each Object.entries(decision.dimensions) as [key, value]}<span>{niceKey(key)}: {typeof value === 'number' ? `${Math.round(value * (value <= 1 ? 100 : 1))}%` : String(value)}</span>{/each}</div>{/if}{/if}</div>{/if}</article>{/each}</div>
          {:else}<div class="empty compact"><div class="empty-icon">⌕</div><h3>No job results</h3><p>This run has not returned any jobs yet.</p></div>{/if}
        {:else}<div class="empty results-empty"><div class="empty-icon">⌖</div><h3>Select a run</h3><p>Choose a run to inspect its job results.</p></div>{/if}
      </div>
    </section>
    {/if}
  </main>
  <footer><span class="brand-small">jevscout</span><span>Built for a more focused job search.</span><span>Local-first · Private by design</span></footer>
</div>
