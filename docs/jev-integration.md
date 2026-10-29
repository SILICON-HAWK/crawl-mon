# JEV integration research

Verified against TypeSafe's official documentation on October 29, 2026. No authenticated API call has been made.

## Verified API

- Endpoint: `POST https://api.typesafe.ai/v1/systemone`.
- Authentication: bearer API key. Obtain a key from the [TypeSafe console](https://console.typesafe.ai/) and keep it in `TYPESAFE_API_KEY`.
- Required body fields: `model`, `state`, and named `questions`. State accepts a string, object, or array.
- Responses contain named `answers`, the model used, and token usage.

Sources: [API reference](https://docs.typesafe.ai/api/system-one), [quick start](https://docs.typesafe.ai/introduction/quickstart).

## Relevant outputs

| Primitive | Output | Proposed JevScout use |
| --- | --- | --- |
| Choice | Selected option, probabilities, confidence | Fit category with an explicit unknown option |
| Score | Score, probabilities, confidence | Skills, seniority, and role fit against descriptive rubrics |
| Noul | Probability from 0 to 1 | Narrow checks where sufficient evidence exists |

Jev does not generate prose. Build user-facing summaries from dimension results, predefined descriptions, and extracted facts. Keep source evidence separate from model judgments. A typed result can still be incorrect.

Sources: [introduction](https://docs.typesafe.ai/introduction), [Choice](https://docs.typesafe.ai/primitives/choice), [Score](https://docs.typesafe.ai/primitives/score).

## Model and operational facts

The models page currently lists `jev-1.14.0` and `jev-1.13.0`; `jev-latest` points to `jev-1.14.0`. Pin a version for repeatable evaluations and retain the response model identifier.

Documented standard context limits are 64k tokens per request and 32k per question. The listed price is $0.042 per million input tokens, with output tokens free. Rate limits are organization-specific and visible in the console. Confirm these details before implementation because they may change.

Source: [models](https://docs.typesafe.ai/models).

Official SDK options include Python's `typesafe-sdk` and JavaScript/TypeScript's `@typesafe-ai/sdk`. The stack remains a project decision. Source: [quick start](https://docs.typesafe.ai/introduction/quickstart).

## Proposed personalized matching

Send one normalized listing and the relevant profile/preferences as structured state. Ask separate questions about skills, seniority, role relevance, and other selected dimensions. Combine normalized scores with configurable weights in application code. TypeSafe documents this composition pattern, including a résumé-screening example: [composite scoring](https://docs.typesafe.ai/patterns/composite-scoring).

Keep deterministic constraints in code when structured facts are available. Missing salary or authorization information remains unknown rather than a rejection. Use an explicit information-availability check or an unknown Choice option before evaluating an uncertain constraint. Do not interpret a low Noul probability as proof that information is missing.

Store raw dimension outputs, uncertainty, rubric and weight versions, job/profile versions, and the final application-derived score. The aggregate score is a preference-based ranking, not a probability of being hired. Thresholds and weights require validation against the user's judgments.

## Data handling and remaining work

TypeSafe documents a commitment not to train on customer data and offers enterprise zero data retention. Do not assume ordinary account requests have zero retention. Review the linked processing terms and confirm account-specific handling before sending a real résumé. Source: [legal documentation](https://docs.typesafe.ai/legal).

Next: confirm account access, select sources and fit rubrics, choose the stack, then test the documented API with synthetic profile/job data. Live quotas, account availability, error handling, and actual matching quality remain unverified.
