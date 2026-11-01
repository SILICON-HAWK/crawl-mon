<script>
  import { preRankOf, preRankTier } from './job-utils.js';

  let { job } = $props();
  let pr = $derived(preRankOf(job));
</script>

{#if pr}
  <div class="pre-rank">
    <div class="score-ring" data-tier={preRankTier(pr.score)} style="--p: {pr.score}" role="img" aria-label={`Match score ${pr.score} out of 100`}><span>{pr.score}</span></div>
    <div class="pre-rank-bars">
      {#each [['Title', pr.title], ['Salary', pr.salary], ['Location', pr.location]] as [label, value]}
        <div class="bar-row"><span>{label}</span><div class="bar" role="img" aria-label={`${label} match ${value} out of 100`}><i style="width: {value}%"></i></div><b>{value}</b></div>
      {/each}
    </div>
  </div>
  {#if pr.reasons.length}<p class="pre-rank-reasons">{pr.reasons.join(' · ')}</p>{/if}
{/if}
