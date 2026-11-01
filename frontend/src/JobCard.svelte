<script>
  // Shared job card body: title, company · location, pre-rank, chips, skills and links.
  // Used by the Jobs board (reel/cards) and the read-only All jobs page.
  // Callers wrap it in their own <article>; `top` renders above the title and
  // `children` renders below the links (the Jobs board puts its decision controls there).
  import PreRank from './PreRank.svelte';
  import { availabilityText, availabilityTone, requirementsOf, matchedSkills, sourceUrlOf, applyUrlOf } from './job-utils.js';

  let { job, top, children } = $props();
</script>

{@render top?.()}
<div class="job-head"><h3>{job.title ?? job.job_title ?? job.name ?? 'Untitled role'}</h3><div class="job-top"><span class="job-company">{job.company ?? job.company_name ?? job.employer ?? 'Company'}</span>{#if job.location}<span class="job-location">{job.location}</span>{/if}</div></div>
<PreRank {job} />
<div class="job-chips"><span class="chip"><span class="chip-label">Salary</span> {job.salary ?? 'Not disclosed'}</span>{#if job.source_name}<span class="chip chip-source">{job.source_name}</span>{/if}<span class="chip {availabilityTone(job)}">{availabilityText(job)}</span></div>
{#if requirementsOf(job)}<p class="job-detail"><strong>Requirements / skills</strong> {Array.isArray(requirementsOf(job)) ? requirementsOf(job).join(', ') : requirementsOf(job)}</p>{:else if matchedSkills(job).length}<p class="job-detail"><strong>Skills</strong> {Array.isArray(matchedSkills(job)) ? matchedSkills(job).join(', ') : matchedSkills(job)}</p>{/if}
<div class="job-links">{#if job.source_name && job.source_link}<a href={job.source_link} target="_blank" rel="noreferrer">{job.source_name} ↗</a>{/if}{#if sourceUrlOf(job)}<a href={sourceUrlOf(job)} target="_blank" rel="noreferrer">Source listing ↗</a>{/if}{#if applyUrlOf(job)}<a href={applyUrlOf(job)} target="_blank" rel="noreferrer">Apply ↗</a>{/if}</div>
{@render children?.()}
