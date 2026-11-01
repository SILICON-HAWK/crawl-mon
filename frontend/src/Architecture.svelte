<script>
  import { tick } from 'svelte';
  import { NODES, EDGES, GROUPS, LAYOUT } from './architecture-data.js';

  const { colW, rowH, nodeW, nodeH, padX, padY, viewW, viewH } = LAYOUT;
  const byId = Object.fromEntries(NODES.map((n) => [n.id, n]));
  const at = (n) => ({ x: padX + n.col * colW, y: padY + n.row * rowH });
  const anchor = (n, side) => {
    const { x, y } = at(n);
    if (side === 'left') return { x, y: y + nodeH / 2 };
    if (side === 'right') return { x: x + nodeW, y: y + nodeH / 2 };
    if (side === 'top') return { x: x + nodeW / 2, y };
    return { x: x + nodeW / 2, y: y + nodeH };
  };
  const geometry = (edge) => {
    const a = byId[edge.from];
    const b = byId[edge.to];
    let p1;
    let p2;
    let d;
    if (a.col === b.col) {
      const down = b.row > a.row;
      p1 = anchor(a, down ? 'bottom' : 'top');
      p2 = anchor(b, down ? 'top' : 'bottom');
      const my = (p1.y + p2.y) / 2;
      d = `M${p1.x} ${p1.y} C${p1.x} ${my} ${p2.x} ${my} ${p2.x} ${p2.y}`;
    } else {
      const forward = b.col > a.col;
      p1 = anchor(a, forward ? 'right' : 'left');
      p2 = anchor(b, forward ? 'left' : 'right');
      const dx = Math.abs(p2.x - p1.x) / 2;
      const s = forward ? 1 : -1;
      d = `M${p1.x} ${p1.y} C${p1.x + s * dx} ${p1.y} ${p2.x - s * dx} ${p2.y} ${p2.x} ${p2.y}`;
    }
    return { d, mid: { x: (p1.x + p2.x) / 2, y: (p1.y + p2.y) / 2 } };
  };

  const nodes = NODES.map((n) => ({ ...n, ...at(n) }));
  const edges = EDGES.map((e) => ({ ...e, ...geometry(e) }));
  const searchText = (n) => `${n.label} ${n.summary} ${GROUPS[n.group].label} ${n.details.join(' ')}`.toLowerCase();

  let selectedId = $state(null);
  let query = $state('');
  let zoomOverride = $state(null);
  let stageWidth = $state(1000);
  let subflowOpen = $state(false);
  let drawerTitle = $state(null);

  let selected = $derived(selectedId ? byId[selectedId] : null);
  let zoom = $derived(zoomOverride ?? Math.min(1, Math.max(0.7, stageWidth / viewW)));
  let neighbourIds = $derived(new Set(selectedId ? EDGES.filter((e) => e.from === selectedId || e.to === selectedId).flatMap((e) => [e.from, e.to]) : []));
  let upstream = $derived(selectedId ? EDGES.filter((e) => e.to === selectedId).map((e) => byId[e.from].label) : []);
  let downstream = $derived(selectedId ? EDGES.filter((e) => e.from === selectedId).map((e) => byId[e.to].label) : []);
  let matchList = $derived(query.trim() ? NODES.filter((n) => searchText(n).includes(query.trim().toLowerCase())) : []);
  let matchIds = $derived(query.trim() ? new Set(matchList.map((n) => n.id)) : null);

  const nodeDimmed = (id) => (selectedId ? !neighbourIds.has(id) : matchIds ? !matchIds.has(id) : false);
  const edgeHot = (e) => selectedId !== null && (e.from === selectedId || e.to === selectedId);
  const edgeDimmed = (e) => selectedId !== null && !edgeHot(e);

  function toggle(id, keyboard = false) {
    if (selectedId === id) {
      close(keyboard);
      return;
    }
    selectedId = id;
    subflowOpen = false;
    if (keyboard) tick().then(() => drawerTitle?.focus());
  }

  function close(restoreFocus = false) {
    const id = selectedId;
    selectedId = null;
    subflowOpen = false;
    if (restoreFocus && id) tick().then(() => document.getElementById(`arch-node-${id}`)?.focus());
  }

  function zoomBy(delta) {
    zoomOverride = Math.round(Math.min(1.6, Math.max(0.6, zoom + delta)) * 100) / 100;
  }

  function onWindowKey(event) {
    if (event.key === 'Escape' && selectedId) close(true);
  }
</script>

<svelte:window onkeydown={onWindowKey} />

<section class="arch-page" aria-labelledby="arch-title">
  <div class="section-heading">
    <div>
      <p class="eyebrow">HOW JEVSCOUT WORKS</p>
      <h2 id="arch-title">Architecture</h2>
    </div>
    <span class="updated">Data flows left to right</span>
  </div>
  <p class="arch-intro">Each box is one stage of the local pipeline. Select a box to see what it does and what it connects to. Solid lines are the main path; dashed lines are optional or started by you.</p>

  <div class="arch-toolbar">
    <label class="arch-search">
      <span class="sr-only">Search components</span>
      <input type="search" placeholder="Search components…" bind:value={query} onkeydown={(event) => { if (event.key === 'Enter' && matchList[0]) toggle(matchList[0].id, true); }} />
    </label>
    <div class="arch-zoom" role="group" aria-label="Zoom diagram">
      <button type="button" onclick={() => zoomBy(-0.1)} disabled={zoom <= 0.6} aria-label="Zoom out">−</button>
      <button type="button" onclick={() => (zoomOverride = null)} aria-label="Fit diagram to width">Fit</button>
      <button type="button" onclick={() => zoomBy(0.1)} disabled={zoom >= 1.6} aria-label="Zoom in">+</button>
    </div>
    {#if matchList.length}
      <div class="arch-results">
        {#each matchList.slice(0, 8) as match (match.id)}
          <button type="button" class="arch-result" aria-pressed={selectedId === match.id} onclick={() => toggle(match.id, true)}>{match.label}</button>
        {/each}
      </div>
    {/if}
  </div>

  <div class="arch-layout">
    <div class="arch-stage" bind:clientWidth={stageWidth}>
      <svg width={Math.round(viewW * zoom)} height={Math.round(viewH * zoom)} viewBox={`0 0 ${viewW} ${viewH}`} role="group" aria-label="Pipeline diagram">
        <defs>
          <marker id="arch-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
            <path d="M0 1L8 5L0 9z" fill="#9aa193" />
          </marker>
          <marker id="arch-arrow-hot" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
            <path d="M0 1L8 5L0 9z" fill="#244d3a" />
          </marker>
        </defs>

        {#each edges as edge, i (i)}
          <path class="arch-edge" class:dashed={edge.dashed} class:hot={edgeHot(edge)} class:dim={edgeDimmed(edge)} d={edge.d} marker-end={edgeHot(edge) ? 'url(#arch-arrow-hot)' : 'url(#arch-arrow)'} />
        {/each}
        {#each edges as edge, i (i)}
          {#if edge.label}
            <text class="arch-edge-label" class:dim={edgeDimmed(edge)} x={edge.mid.x} y={edge.mid.y - 5} text-anchor="middle">{edge.label}</text>
          {/if}
        {/each}

        {#each nodes as node (node.id)}
          {@const style = GROUPS[node.group]}
          <g id={`arch-node-${node.id}`} class="arch-node" class:sel={selectedId === node.id} class:dim={nodeDimmed(node.id)} class:match={matchIds?.has(node.id)} transform={`translate(${node.x} ${node.y})`} role="button" tabindex="0" aria-pressed={selectedId === node.id} aria-label={`${node.label}, ${style.label}. ${node.summary}`} onclick={() => toggle(node.id)} onkeydown={(event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); toggle(node.id, true); } }}>
            <rect class="frame" width={nodeW} height={nodeH} rx="10" fill={style.fill} stroke={style.stroke} stroke-width="1.5" />
            <text class="arch-grp" x="12" y="17">{style.label}</text>
            <text class="arch-lbl" x="12" y="42">{node.label}</text>
            {#if node.tag}
              <g class="arch-tag" transform={`translate(${nodeW - 42} -8)`}>
                <rect width="42" height="16" rx="8" />
                <text x="21" y="11.5" text-anchor="middle">{node.tag}</text>
              </g>
            {/if}
          </g>
        {/each}
      </svg>
    </div>

    <aside class="arch-drawer" class:open={selected !== null} aria-label="Component details">
      {#if selected}
        {@const style = GROUPS[selected.group]}
        <div class="arch-drawer-head">
          <span class="arch-badge"><span class="arch-swatch" style={`background:${style.fill};border-color:${style.stroke}`}></span>{style.label}</span>
          <button type="button" class="arch-close" onclick={() => close(true)} aria-label="Close details">×</button>
        </div>
        <h2 bind:this={drawerTitle} tabindex="-1">{selected.label}</h2>
        <p>{selected.summary}</p>
        <ul class="arch-bullets">
          {#each selected.details as detail}<li>{detail}</li>{/each}
        </ul>
        <dl class="arch-links">
          <div><dt>From</dt><dd>{upstream.length ? upstream.join(', ') : 'Starts here'}</dd></div>
          <div><dt>To</dt><dd>{downstream.length ? downstream.join(', ') : 'Ends here'}</dd></div>
        </dl>
        {#if selected.subflow}
          <button type="button" class="arch-sub-toggle" aria-expanded={subflowOpen} aria-controls="arch-subflow" onclick={() => (subflowOpen = !subflowOpen)}>
            {subflowOpen ? 'Hide' : 'Show'} sub-flow ({selected.subflow.length} steps)
          </button>
          {#if subflowOpen}
            <ol id="arch-subflow" class="arch-subflow">
              {#each selected.subflow as step}<li>{step}</li>{/each}
            </ol>
          {/if}
        {/if}
      {:else}
        <p class="arch-empty-title">Select a component</p>
        <p>Click or press Enter on any box to see its role and connections. Press Esc to close.</p>
      {/if}
    </aside>
  </div>

  <div class="arch-legend" aria-label="Legend">
    {#each Object.entries(GROUPS) as [key, style] (key)}
      <span class="arch-legend-item"><span class="arch-swatch" style={`background:${style.fill};border-color:${style.stroke}`}></span>{style.label}</span>
    {/each}
    <span class="arch-legend-item"><span class="arch-line"></span>Main path</span>
    <span class="arch-legend-item"><span class="arch-line dashed"></span>Optional or started by you</span>
    <span class="arch-legend-item"><span class="arch-tag-sample">NEW</span>Added in this version</span>
  </div>
  <p class="arch-note">Pre-rank is a loose structured match and makes no model call. The decision model runs only when you choose Analyze for a job.</p>
</section>

<style>
  .arch-intro { margin: 0 0 16px; max-width: 64ch; font-size: 13px; line-height: 1.6; color: var(--muted); }
  .arch-toolbar { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 12px; }
  .arch-search { flex: 1 1 220px; min-width: 0; display: block; }
  .arch-search input { width: 100%; min-height: 40px; border: 1px solid var(--line); border-radius: 6px; padding: 9px 12px; background: #fffefa; color: var(--ink); font: 13px 'DM Sans', sans-serif; }
  .arch-search input:focus-visible { outline: 2px solid #5b8a3c; outline-offset: 0; }
  .arch-results { display: flex; gap: 6px; flex-wrap: wrap; width: 100%; }
  .arch-result { min-height: 36px; padding: 6px 12px; border: 1px solid #cfd8bd; border-radius: 999px; background: #f4f6ee; color: var(--green); font: 500 12px 'DM Sans', sans-serif; cursor: pointer; }
  .arch-result[aria-pressed="true"] { background: var(--green); color: #f8f6ea; border-color: var(--green); }
  .arch-zoom { display: flex; border: 1px solid var(--line); border-radius: 6px; overflow: hidden; background: var(--paper); }
  .arch-zoom button { min-width: 44px; min-height: 40px; border: 0; background: transparent; color: var(--green); font: 500 13px 'DM Mono', monospace; cursor: pointer; }
  .arch-zoom button + button { border-left: 1px solid var(--line); }
  .arch-zoom button:disabled { opacity: .4; cursor: default; }
  .arch-layout { display: grid; grid-template-columns: minmax(0, 1fr) 300px; gap: 14px; align-items: start; }
  .arch-stage { min-width: 0; max-width: 100%; max-height: 560px; overflow: auto; overscroll-behavior: contain; -webkit-overflow-scrolling: touch; touch-action: pan-x pan-y; background: var(--paper); border: 1px solid var(--line); border-radius: 8px; padding: 10px; }
  .arch-stage:focus-visible { outline: 2px solid #5b8a3c; outline-offset: 2px; }
  .arch-stage svg { display: block; }
  .arch-edge { fill: none; stroke: #9aa193; stroke-width: 1.4; opacity: .85; transition: stroke .2s, opacity .2s, stroke-width .2s; }
  .arch-edge.dashed { stroke-dasharray: 5 4; }
  .arch-edge.hot { stroke: #244d3a; stroke-width: 2.4; opacity: 1; }
  .arch-edge.dim { opacity: .1; }
  .arch-edge-label { font: 500 10px 'DM Mono', monospace; fill: #5d6457; paint-order: stroke; stroke: var(--paper); stroke-width: 4px; stroke-linejoin: round; pointer-events: none; transition: opacity .2s; }
  .arch-edge-label.dim { opacity: .15; }
  .arch-node { cursor: pointer; outline: none; transition: opacity .2s; }
  .arch-node.dim { opacity: .25; }
  .arch-node:hover .frame { filter: drop-shadow(0 4px 6px #20261f26); }
  .arch-node.match .frame { stroke: #7da33f; stroke-width: 2.4; }
  .arch-node.sel .frame { stroke: var(--green); stroke-width: 3; }
  .arch-node:focus-visible .frame { stroke: #5b8a3c; stroke-width: 3.5; }
  .arch-node:focus-visible.sel .frame { stroke: #2f6b4f; }
  .arch-grp { font: 500 9px 'DM Mono', monospace; letter-spacing: .08em; text-transform: uppercase; fill: #6a7062; }
  .arch-lbl { font: 600 13px 'DM Sans', sans-serif; fill: var(--ink); }
  .arch-tag rect { fill: var(--lime); }
  .arch-tag text { font: 600 8px 'DM Mono', monospace; letter-spacing: .1em; fill: #1e392b; text-transform: uppercase; }
  .arch-drawer { background: var(--paper); border: 1px solid var(--line); border-radius: 8px; padding: 18px; min-width: 0; box-shadow: var(--shadow-card); }
  .arch-drawer-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-bottom: 10px; }
  .arch-badge { display: inline-flex; align-items: center; gap: 8px; font: 500 10px 'DM Mono', monospace; color: #4f5748; letter-spacing: .04em; }
  .arch-swatch { display: inline-block; width: 12px; height: 12px; border-radius: 3px; border: 1.5px solid; flex: none; }
  .arch-close { width: 44px; height: 44px; margin: -10px -10px -10px 0; border: 0; border-radius: 50%; background: transparent; color: var(--green); font-size: 22px; cursor: pointer; flex: none; }
  .arch-drawer h2 { font-size: 18px; font-weight: 600; letter-spacing: -.02em; margin: 0 0 8px; line-height: 1.25; }
  .arch-drawer > p { font-size: 13px; line-height: 1.55; color: var(--muted); margin: 0 0 12px; }
  .arch-empty-title { color: var(--ink) !important; font-weight: 600; }
  .arch-bullets { margin: 0; padding-left: 18px; font-size: 13px; line-height: 1.6; color: #4f5748; }
  .arch-bullets li + li { margin-top: 4px; }
  .arch-links { display: grid; gap: 8px; margin: 16px 0 0; padding-top: 14px; border-top: 1px solid #ecece5; font-size: 12px; }
  .arch-links div { display: grid; grid-template-columns: 52px minmax(0, 1fr); gap: 8px; }
  .arch-links dt { font: 500 10px 'DM Mono', monospace; color: #7a8072; text-transform: uppercase; letter-spacing: .06em; padding-top: 2px; }
  .arch-links dd { margin: 0; color: var(--ink); line-height: 1.45; overflow-wrap: anywhere; }
  .arch-sub-toggle { margin-top: 14px; min-height: 40px; padding: 8px 14px; border: 1px solid #cfd8bd; border-radius: 999px; background: #f4f6ee; color: var(--green); font: 500 12px 'DM Sans', sans-serif; cursor: pointer; }
  .arch-subflow { margin: 10px 0 0; padding-left: 20px; font-size: 12px; line-height: 1.6; color: #4f5748; }
  .arch-subflow li + li { margin-top: 4px; }
  .arch-legend { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 18px; margin-top: 16px; padding: 14px 16px; border: 1px solid var(--line); border-radius: 8px; background: var(--paper); font-size: 12px; color: var(--muted); }
  .arch-legend-item { display: inline-flex; align-items: center; gap: 7px; }
  .arch-line { display: inline-block; width: 26px; border-top: 1.5px solid #9aa193; }
  .arch-line.dashed { border-top-style: dashed; }
  .arch-tag-sample { display: inline-block; padding: 2px 7px; border-radius: 8px; background: var(--lime); color: #1e392b; font: 600 8px 'DM Mono', monospace; letter-spacing: .1em; }
  .arch-note { margin: 12px 0 0; font-size: 12px; line-height: 1.5; color: #858a80; }

  @media (max-width: 760px) {
    .arch-layout { grid-template-columns: minmax(0, 1fr); }
    .arch-drawer { position: fixed; left: 0; right: 0; bottom: 0; z-index: 50; max-height: 62vh; overflow: auto; border-radius: 16px 16px 0 0; border-bottom: 0; box-shadow: 0 -12px 40px #20261f33; padding: 16px 21px calc(18px + env(safe-area-inset-bottom, 0px)); }
    .arch-drawer:not(.open) { display: none; }
    .arch-drawer.open { animation: arch-sheet .25s var(--ease); }
    .arch-zoom button, .arch-result, .arch-sub-toggle { min-height: 44px; }
    .arch-stage { max-height: 62vh; }
  }
  @keyframes arch-sheet { from { transform: translateY(100%); } to { transform: none; } }
  @media (prefers-reduced-motion: reduce) {
    .arch-drawer.open { animation: none; }
    .arch-edge, .arch-edge-label, .arch-node { transition: none; }
  }
</style>
