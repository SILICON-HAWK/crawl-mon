// Shared job helpers used by the Jobs board, the All jobs debug page and the job cards.
// Behaviour is unchanged from the helpers that previously lived inline in App.svelte.

export const isObject = (item) => item && typeof item === 'object';

export const matchedSkills = (job) => job?.matched_skills ?? job?.matchedSkills ?? job?.skills_matched ?? [];

export const requirementsOf = (job) => {
  const supplied = job?.requirements ?? job?.required_skills ?? job?.skills ?? job?.qualifications;
  if (supplied) return supplied;
  const text = String(job?.description ?? '');
  const match = /(?:requirements|qualifications|what you(?:’|'| a)ll bring|what we(?:’|'| a)re looking for)/i.exec(text);
  return match ? text.slice(match.index, match.index + 500) : null;
};

export const sourceUrlOf = (job) => job?.listing_url ?? job?.source_url ?? job?.provenance?.source_url ?? job?.provenance?.seed_url ?? job?.seed_url ?? null;
export const applyUrlOf = (job) => job?.application_url ?? job?.apply_url ?? job?.url ?? null;
export const jobUrlOf = (job) => job?.url ?? job?.application_url ?? job?.apply_url ?? job?.source_url ?? null;

// Pre-rank: optional `pre_rank` object on /api/jobs items. Anything malformed is treated as absent.
export const clampScore = (value) => {
  const n = Number(value);
  return Number.isFinite(n) ? Math.max(0, Math.min(100, Math.round(n))) : 0;
};
export const preRankOf = (job) => {
  const pr = job?.pre_rank;
  if (!isObject(pr) || pr.score == null || pr.score === '' || !Number.isFinite(Number(pr.score))) return null;
  return {
    score: clampScore(pr.score),
    title: clampScore(pr.title),
    salary: clampScore(pr.salary),
    location: clampScore(pr.location),
    reasons: Array.isArray(pr.reasons) ? pr.reasons.filter((reason) => typeof reason === 'string' && reason.trim()).slice(0, 4) : []
  };
};
export const preRankTier = (score) => score >= 70 ? 'high' : score >= 40 ? 'mid' : 'low';

export const availabilityText = (job) => {
  const state = job?.availability?.state;
  const base = state === 'available' ? 'Page reachable' : state === 'unavailable' ? 'Not found' : state === 'unknown' ? 'Check inconclusive' : 'Not checked';
  return job?.availability?.status_code ? `${base} · HTTP ${job.availability.status_code}` : base;
};
export const availabilityTone = (job) => {
  const state = job?.availability?.state;
  return state === 'available' ? 'chip-good' : state === 'unavailable' ? 'chip-bad' : state === 'unknown' ? 'chip-warn' : '';
};
