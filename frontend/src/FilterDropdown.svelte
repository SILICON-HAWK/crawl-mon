<script>
  // Multi-select checkbox dropdown. Parent owns the `excluded` Set and the `open` flag,
  // so only one dropdown can be open at a time. Options are checked unless excluded.
  import { tick } from 'svelte';

  let { label, options, excluded, open = false, searchable = false, onopen, onset } = $props();

  let query = $state('');
  let wrap = $state();
  let trigger = $state();
  let panel = $state();
  let searchInput = $state();

  let panelId = $derived(`filter-panel-${label.toLowerCase().replace(/\s+/g, '-')}`);
  let selectedCount = $derived(options.filter((option) => !excluded.has(option.value)).length);
  let visible = $derived(
    searchable && query.trim()
      ? options.filter((option) => option.label.toLowerCase().includes(query.trim().toLowerCase()))
      : options
  );
  let visibleValues = $derived(visible.map((option) => option.value));

  async function toggle() {
    if (open) return close(true);
    onopen(true);
    await tick();
    (searchInput ?? panel?.querySelector('input[type="checkbox"]'))?.focus();
  }

  function close(returnFocus = false) {
    query = '';
    onopen(false);
    if (returnFocus) trigger?.focus();
  }

  function handleKeydown(event) {
    if (event.key === 'Escape' && open) {
      event.preventDefault();
      close(true);
    }
  }

  function handleFocusOut(event) {
    if (open && !wrap.contains(event.relatedTarget)) close(false);
  }
</script>

<svelte:window
  onpointerdown={(event) => { if (open && wrap && !wrap.contains(event.target)) close(false); }}
  onkeydown={handleKeydown}
/>

<div class="filter-dd" bind:this={wrap} onfocusout={handleFocusOut}>
  <button
    bind:this={trigger}
    type="button"
    class="filter-trigger"
    class:open
    aria-expanded={open}
    aria-controls={panelId}
    onclick={toggle}
  >
    <span>{label}</span>
    <span class="filter-count" aria-label={`${selectedCount} of ${options.length} selected`}>{selectedCount}</span>
    <span class="filter-caret" aria-hidden="true">▾</span>
  </button>
  {#if open}
    <div class="filter-panel" id={panelId} role="group" aria-label={`${label} options`} bind:this={panel}>
      <div class="filter-tools">
        <button type="button" class="filter-tool" onclick={() => onset(visibleValues, true)} disabled={!visibleValues.length}>Select all</button>
        <button type="button" class="filter-tool" onclick={() => onset(visibleValues, false)} disabled={!visibleValues.length}>Clear</button>
        <span class="filter-tally">{selectedCount}/{options.length}</span>
      </div>
      {#if searchable}
        <input
          bind:this={searchInput}
          bind:value={query}
          type="search"
          class="filter-search"
          placeholder={`Search ${label.toLowerCase()}…`}
          aria-label={`Search ${label.toLowerCase()}`}
          autocomplete="off"
        />
      {/if}
      <div class="filter-options">
        {#each visible as option (option.value)}
          <label class="filter-option">
            <input type="checkbox" checked={!excluded.has(option.value)} onchange={(event) => onset([option.value], event.currentTarget.checked)} />
            <span class="filter-option-label">{option.label}</span>
            <span class="filter-option-count">{option.count}</span>
          </label>
        {:else}
          <p class="filter-none">No matching options.</p>
        {/each}
      </div>
    </div>
  {/if}
</div>
