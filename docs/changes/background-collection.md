# Bounded background collection

Ran the existing local Crawlee CLI against five public ATS board entry URLs on 2026-10-31. Every run used `--max-pages 1 --max-depth 0 --timeout-seconds 30`; no private profile, account cookies, or AI/API keys were used. Each URL was submitted and executed as its own approved run.

## Results

| Source | Run ID | Status | Pages saved | Jobs extracted | Quality notes |
| --- | --- | --- | ---: | ---: | --- |
| Greenhouse / Stripe (`boards.greenhouse.io/stripe`) | `ae79df40-0572-4a8f-934a-5ad4b710751b` | completed | 1 | 0 | Redirect candidate to `job-boards.greenhouse.io/stripe` was outside scope; no failure reported. |
| Lever / Spotify (`jobs.lever.co/spotify`) | `b04761d6-1b58-4d2f-9d8f-db994c93a896` | completed | 1 | 0 | Two outside-origin candidates recorded; neither fetched. |
| Ashby / Linear (`jobs.ashbyhq.com/linear`) | `2078d53b-9b39-494e-8149-5869c4cc87ba` | completed | 1 | 0 | HTTP 200; no JobPosting JSON-LD extracted. |
| Ashby / Figma (`jobs.ashbyhq.com/figma`) | `25ac960e-0bd0-44a4-9a0a-0288a12123ef` | failed | 0 | 0 | One request failed; no page evidence saved. |
| Lever / Anthropic (`jobs.lever.co/anthropic`) | `dafd43ea-4822-4a20-b8ab-e8daca599e51` | failed | 0 | 0 | One request failed; no page evidence saved. |

Totals: 5 sources attempted, 3 pages saved, 0 jobs extracted, 2 failed runs. The target of roughly 100 jobs was not reached. These board landing pages do not yield a meaningful job set through this pipeline: the current extractor reads schema.org `JobPosting` JSON-LD from saved HTML, while most ATS boards populate job listings dynamically or expose provider-specific feeds. The one-page cap also intentionally prevents following job links. The collection is useful as a bounded compatibility probe, not as a representative job dataset.

The failed runs have generic `request_failed` reports and no saved page evidence, so the underlying causes are unknown. Successful run reports had no request failures but also no extracted records. The source URLs were kept to public company board entry points, and only the exact seed origin was contacted under the requested scope.

## Feed API retry

Retried with four known public ATS feed endpoints, stored under `data/live-trial`. Each run used one seed, `--max-pages 1 --max-depth 0 --timeout-seconds 30`; all runs completed with one page saved and no failed requests.

| Feed | Run ID | Jobs extracted |
| --- | --- | ---: |
| Greenhouse SonicWall | `b1db5106-13de-44b2-b789-36e0a61dbce2` | 48 |
| Ashby Firstwork | `c1673f15-2f4a-40c8-810e-6d1997686c07` | 13 |
| Recruitee TransPerfect | `a2a37de7-7a75-4d85-848c-15664dd98b32` | 686 |
| Breezy NextHire | `09a7f296-f045-473c-8cd3-33a5c1627a26` | 1 |

Total: 748 extracted job records from 4 sources and 4 saved pages, exceeding the 100-job target. All are public feed responses; no credentials or AI/API keys were used. The Recruitee response dominated the total (686 records), so the combined count is heavily skewed to that one employer and should not be read as a balanced sample. The Recruitee result inspection showed rich descriptions, locations, dates, and application URLs on sampled entries; fields such as company were populated with categories like `Sales` or `QA Testing`, indicating taxonomy values may be mapped into company. Feed endpoint/parser-specific normalization and duplicate/active-posting validation remain quality follow-up. The preceding landing-page probe remains as the initial attempt; this feed retry demonstrates the CLI's existing feed extraction can reach the requested volume with bounded requests.
