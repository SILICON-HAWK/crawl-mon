# Browserless Career Feeds and Endpoints (India & Global)

Status: Research and architecture documentation, October 2026.
Branch: `gemini/feature/job-portal`.

## 1. Executive Summary

Traditional job boards in India (Naukri, Foundit/Monster, Cutshort, Instahyre) aggressively block browserless requests via Cloudflare and Akamai bot management, offering no public REST/JSON/RSS endpoints without paid enterprise recruiter agreements.

However, modern technology companies hiring in India—from startups and unicorns (e.g., Swiggy, Razorpay, Zepto, Postman, CRED, InMobi, Clevertap) to multinational engineering hubs (e.g., Atlassian, Uber, Stripe, Twilio, Datadog)—publish their real-time job openings directly to **public Application Tracking System (ATS) endpoints**.

These endpoints are:
1. **Completely browserless**: standard HTTP `GET` returning clean JSON or structured feeds.
2. **Zero-credential**: no API keys, accounts, or cookies required for public job board listings.
3. **Structured & authoritative**: direct from the employer, avoiding scraped aggregator stale data.
4. **Richly filterable**: include location names, office hierarchies, department, workplace type (hybrid/remote), and full job descriptions.

---

## 2. Supported Public Browserless ATS Endpoints

### 2.1 Greenhouse Public Board API

- **Endpoint**: `GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true`
- **Single Job**: `GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs/{job_id}`
- **Authentication**: None required.
- **Payload Format**: JSON.
- **Key Fields**:
  - `id`: Unique posting integer ID.
  - `title`: Job title.
  - `location.name`: Location string (e.g., `"Bengaluru, Karnataka, India"`, `"Remote - India"`).
  - `offices`: Array of office objects (`id`, `name`, `location`).
  - `departments`: Array of department objects (`id`, `name`).
  - `content`: Unescaped HTML description.
  - `updated_at`: ISO 8601 timestamp.
  - `absolute_url`: Canonical application link.
- **India Usage**: Heavy. Thousands of tech companies with India offices (e.g., InMobi, Datadog India, Stripe India, Twilio India, Elastic, GoTo, Figma, etc.).

### 2.2 Lever Postings API

- **Endpoint**: `GET https://api.lever.co/v0/postings/{company_slug}?mode=json`
- **Single Job**: `GET https://api.lever.co/v0/postings/{company_slug}/{posting_id}`
- **Authentication**: None required.
- **Payload Format**: JSON.
- **Key Fields**:
  - `id`: Posting UUID.
  - `text`: Job title.
  - `categories.location`: Location string (e.g., `"Bangalore"`, `"Hyderabad"`, `"Pune"`).
  - `categories.team`: Team / department.
  - `categories.commitment`: E.g., `"Full-time"`.
  - `workplaceType`: `"on-site"`, `"remote"`, or `"hybrid"`.
  - `description`: HTML description.
  - `descriptionPlain`: Plain text description.
  - `hostedUrl`: Canonical application link.
  - `createdAt`: Millisecond unix timestamp.
- **India Usage**: Very high among top Indian SaaS and product startups (e.g., Postman, Atlassian India, Razorpay, Zepto, Hasura, BrowserStack).

### 2.3 Ashby Public Job Posting API

- **Endpoint**: `GET https://api.ashbyhq.com/posting-api/job-board/{board_name}?includeCompensation=true`
- **Authentication**: None required.
- **Payload Format**: JSON.
- **Key Fields**:
  - `jobs[].id`: Posting UUID.
  - `jobs[].title`: Job title.
  - `jobs[].location`: Primary location (e.g., `"Bengaluru, India"`).
  - `jobs[].secondaryLocations`: Array of secondary locations.
  - `jobs[].department`: Department name.
  - `jobs[].employmentType`: Employment type.
  - `jobs[].isRemote`: Boolean flag.
  - `jobs[].jobUrl`: Canonical application link.
  - `jobs[].publishedAt`: ISO 8601 timestamp.
  - `jobs[].descriptionHtml`: HTML description.
  - `jobs[].compensation`: Structured compensation tier if published.
- **India Usage**: Rapidly expanding; standard for AI startups, Y Combinator companies, and modern scale-ups hiring remote or India-based engineers (e.g., Retool, Linear, Ramp, Cursor/Anysphere).

### 2.4 SmartRecruiters Public Postings API

- **Endpoint**: `GET https://api.smartrecruiters.com/v1/companies/{company}/postings`
- **Detail**: `GET https://api.smartrecruiters.com/v1/companies/{company}/postings/{posting_id}`
- **Authentication**: None required.
- **Payload Format**: JSON.
- **Key Fields**:
  - `content[].id`: Unique posting ID.
  - `content[].name`: Job title.
  - `content[].location.city`: City name (e.g., `"Bangalore"`, `"Gurugram"`).
  - `content[].location.region`: State / Region.
  - `content[].location.country`: ISO country code (`"in"`).
  - `content[].department.label`: Department.
  - `content[].releasedDate`: ISO 8601 timestamp.
- **India Usage**: Prominent among large technology consulting firms, GCCs (Global Capability Centers), and enterprise tech hubs in India (e.g., Visa, Bosch India, Publicis Sapient, Informatica).

### 2.5 Workable Public API

- **Endpoint**: `GET https://apply.workable.com/api/v1/widget/accounts/{company_slug}` or `GET https://apply.workable.com/api/v2/accounts/{company_slug}/jobs`
- **Authentication**: None required.
- **Payload Format**: JSON.
- **Key Fields**: `title`, `department`, `city`, `country`, `state`, `telecommuting`, `shortlink`.
- **India Usage**: Mid-sized tech companies and digital agencies with offices in India.

### 2.6 Remote & Developer Feeds (Worldwide / India Eligible)

- **RemoteOK Public API**: `GET https://remoteok.com/api` (Public JSON array of developer postings; includes `location` field and country eligibility).
- **Hacker News "Who is Hiring?"**: `https://hacker-news.firebaseio.com/v0/item/{story_id}.json` (Official Firebase API; pure JSON discussion item with nested comments; parsed for `[India]`, `[Remote]`, `[Bangalore]`, etc.).

---

## 3. Strict Location Filtering for India

Per user requirement, filtering is strictly limited to **India and India-eligible remote roles**:

### 3.1 Accepted Locations
1. **Direct Indian Cities & States**:
   - `"Bengaluru"`, `"Bangalore"`, `"Karnataka"`
   - `"Hyderabad"`, `"Secunderabad"`, `"Telangana"`, `"Andhra Pradesh"`
   - `"Pune"`, `"Mumbai"`, `"Navi Mumbai"`, `"Thane"`, `"Maharashtra"`
   - `"Gurgaon"`, `"Gurugram"`, `"Noida"`, `"Greater Noida"`, `"Delhi"`, `"New Delhi"`, `"NCR"`
   - `"Chennai"`, `"Tamil Nadu"`
   - `"Kolkata"`, `"West Bengal"`
   - `"Kochi"`, `"Cochin"`, `"Kerala"`
   - `"Ahmedabad"`, `"Gujarat"`
   - `"Chandigarh"`, `"Mohali"`, `"Jaipur"`, `"Indore"`
   - Country name: `"India"`, `", IN"`, `"country: in"`

2. **India-Eligible Remote Roles**:
   - Explicit India remote: `"Remote - India"`, `"India - Remote"`, `"Remote (India)"`, `"Remote, India"`
   - Broad / Global remote: `"Worldwide Remote"`, `"Anywhere in the world"`, `"Remote - Global"`, `"Remote (APAC / India)"`

### 3.2 Strictly Rejected Locations
- Explicit other countries: `"United States"`, `"USA"`, `"UK"`, `"London"`, `"Germany"`, `"Berlin"`, `"Canada"`, `"Toronto"`, `"Singapore"`, `"Australia"`, etc.
- Region-locked remote that excludes India:
  - `"Remote - US"`, `"Remote (US Only)"`, `"Remote - North America"`, `"US Remote"`
  - `"Remote - EMEA"`, `"Remote - Europe"`, `"Remote - UK"`
  - `"Remote - LatAm"`
- Unspecified "Remote" without country context if the employer's board indicates non-India default (or flagged for inspection).

---

## 4. Architecture: The `FeedSourceAdapter` Pattern

Rather than writing custom one-off scrapers, we introduce a modular `FeedSourceAdapter` interface in `src/jevscout/feeds/`:

```
src/jevscout/feeds/
├── __init__.py
├── base.py            # FeedAdapter protocol and NormalizedFeedJob data structure
├── registry.py        # Feed registry (detects and routes by URL or source name)
├── greenhouse.py      # Greenhouse JSON feed adapter
├── lever.py           # Lever JSON feed adapter
├── ashby.py           # Ashby JSON feed adapter
└── location.py        # India location matcher and normalizer
```

### Key Contract:
1. **Input**: A seed URL (e.g. `https://boards.greenhouse.io/stripe` or API URL) or a configured board identifier (`greenhouse:stripe`, `lever:postman`).
2. **Fetch**: Uses the existing application HTTP client (zero browser, respect redirect and timeout boundaries).
3. **Parse**: Maps provider-specific JSON fields into [`JobPosting`](../src/jevscout/extraction.py) records directly, populating source URL, provenance, and title.
4. **Filter**: Optional India filter matching city, state, country, or remote eligibility.
5. **Storage**: The raw feed JSON is saved as an artifact in `./data/runs/<id>/artifacts/pages/` for auditability and offline re-extraction.
