<script>
  // Debug page: lists EVERY saved job (technical, non-technical, undetermined) for checking the API.
  // Read-only cards, with four multi-select filters. Within a filter checked values are OR-ed;
  // across filters they are AND-ed. Options are stored as excluded values so new values start checked.
  import { onMount } from 'svelte';
  import JobCard from './JobCard.svelte';
  import FilterDropdown from './FilterDropdown.svelte';

  let { username = 'default' } = $props();

  const CATEGORY_ORDER = ['technical', 'non_technical', 'undetermined'];
  const CATEGORY_LABELS = { technical: 'Technical', non_technical: 'Non-technical', undetermined: 'Undetermined' };
  const UNKNOWN = 'Unknown';
  const FILTERS = [
    { key: 'department', label: 'Department', searchable: false },
    { key: 'location', label: 'Location', searchable: false },
    { key: 'source', label: 'Source', searchable: false },
    { key: 'company', label: 'Company', searchable: true }
  ];

  const textOf = (value) => String(value ?? '').trim() || UNKNOWN;
  const categoryOf = (job) => CATEGORY_ORDER.includes(job?.job_category) ? job.job_category : 'undetermined';
  const sourceOf = (job) => textOf(job?.source_name?.trim() ? job.source_name : job?.source_platform);
  const valueFor = {
    department: categoryOf,
    location: (job) => textOf(job?.location),
    source: sourceOf,
    company: (job) => textOf(job?.company)
  };
  const withSource = (job) => ({ ...job, source_name: sourceOf(job) });
  const emptyExcluded = () => ({ department: new Set(), location: new Set(), source: new Set(), company: new Set() });

  let jobs = $state([]);
  let status = $state('loading');
  let errorMessage = $state('');
  let excluded = $state(emptyExcluded());
  let openFilter = $state(null);

  let optionsByFilter = $derived.by(() => {
    const result = {};
    for (const { key } of FILTERS) {
      const counts = new Map();
      if (key === 'department') for (const value of CATEGORY_ORDER) counts.set(value, 0);
      for (const job of jobs) {
        const value = valueFor[key](job);
        counts.set(value, (counts.get(value) ?? 0) + 1);
      }
      result[key] = [...counts.entries()]
        .sort(([a], [b]) => key === 'department' ? CATEGORY_ORDER.indexOf(a) - CATEGORY_ORDER.indexOf(b) : a.localeCompare(b, undefined, { sensitivity: 'base' }))
        .map(([value, count]) => ({ value, label: key === 'department' ? CATEGORY_LABELS[value] : value, count }));
    }
    return result;
  });

  let filtered = $derived(jobs.filter((job) => FILTERS.every(({ key }) => !excluded[key].has(valueFor[key](job)))));
  let emptyFilter = $derived(FILTERS.find(({ key }) => optionsByFilter[key].length && optionsByFilter[key].every((option) => excluded[key].has(option.value))));

  function setOptions(key, values, include) {
    const next = new Set(excluded[key]);
    for (const value of values) if (include) next.delete(value); else next.add(value);
    excluded = { ...excluded, [key]: next };
  }

  function resetFilters() {
    excluded = emptyExcluded();
  }

  async function load() {
    status = 'loading';
    errorMessage = '';
    try {
      const response = await fetch(`/api/jobs?technical_only=false&username=${encodeURIComponent(username.trim() || 'default')}`);
      const raw = await response.text();
      let payload = null;
      try { payload = raw ? JSON.parse(raw) : null; } catch { payload = null; }
      if (!response.ok) throw new Error(payload?.detail ?? payload?.message ?? `${response.status} ${response.statusText}`);
      jobs = [payload, payload?.jobs, payload?.items, payload?.results].find(Array.isArray) ?? [];
      resetFilters();
      status = 'ready';
    } catch (e) {
      errorMessage = `Could not load jobs: ${e.message}`;
      status = 'error';
    }
  }

  onMount(load);
</script>

<div class="section-heading jobs-heading">
  <div><p class="eyebrow">DEBUG · API CHECK</p><h2>All jobs</h2></div>
  <div class="results-tools">
    {#if status === 'ready'}<span class="count" aria-live="polite">{filtered.length} of {jobs.length} jobs</span>{/if}
    <button class="text-button" onclick={load} disabled={status === 'loading'}>Refresh ↻</button>
  </div>
</div>
<p class="all-jobs-note">Every saved job for <code>{username.trim() || 'default'}</code>, including non-technical and undetermined roles the Jobs board hides. Read-only.</p>

{#if status === 'loading'}
  <div class="all-jobs-skeleton" aria-busy="true" aria-live="polite">
    <span class="sr-only">Loading all jobs…</span>
    {#each [1, 2, 3, 4] as n (n)}
      <div class="skeleton-card" aria-hidden="true">
        <span class="skel skel-title"></span>
        <span class="skel skel-line"></span>
        <div class="skel-row"><span class="skel skel-chip"></span><span class="skel skel-chip"></span></div>
        <span class="skel skel-block"></span>
        <span class="skel skel-line short"></span>
      </div>
    {/each}
  </div>
{:else if status === 'error'}
  <div class="alert" role="alert"><span>!</span>{errorMessage}</div>
  <div class="empty"><div class="empty-icon" aria-hidden="true">!</div><h3>Could not load jobs</h3><p>Check that the JevScout API is running, then try again.</p><button class="text-button empty-action" onclick={load}>Retry</button></div>
{:else}
  <div class="filter-bar" role="group" aria-label="Filter jobs">
    {#each FILTERS as filter (filter.key)}
      <FilterDropdown
        label={filter.label}
        options={optionsByFilter[filter.key]}
        excluded={excluded[filter.key]}
        searchable={filter.searchable}
        open={openFilter === filter.key}
        onopen={(next) => openFilter = next ? filter.key : (openFilter === filter.key ? null : openFilter)}
        onset={(values, include) => setOptions(filter.key, values, include)}
      />
    {/each}
    {#if jobs.length}<button class="text-button filter-reset" onclick={resetFilters}>Reset filters</button>{/if}
  </div>

  {#if !jobs.length}
    <div class="empty"><div class="empty-icon" aria-hidden="true">⌁</div><h3>No saved jobs</h3><p>There are no saved jobs for this username yet. Run a pipeline to collect some.</p></div>
  {:else if emptyFilter}
    <div class="empty"><div class="empty-icon" aria-hidden="true">◌</div><h3>Nothing selected for {emptyFilter.label}</h3><p>Check at least one {emptyFilter.label.toLowerCase()} option to see jobs.</p></div>
  {:else if !filtered.length}
    <div class="empty"><div class="empty-icon" aria-hidden="true">◌</div><h3>No jobs match these filters</h3><p>Try selecting more options.</p><button class="text-button empty-action" onclick={resetFilters}>Clear filters</button></div>
  {:else}
    <div class="job-list card-view all-jobs-grid">
      {#each filtered.map(withSource) as job}
        {#snippet categoryTag()}
          <div class="job-categories"><span class="chip chip-category" data-category={categoryOf(job)}>{CATEGORY_LABELS[categoryOf(job)]}</span></div>
        {/snippet}
        <article class="job all-job">
          <JobCard {job} top={categoryTag} />
        </article>
      {/each}
    </div>
  {/if}
{/if}
