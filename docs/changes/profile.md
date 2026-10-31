# Local profile API

The local API now provides `GET` and `PUT /api/profile/{username}`. A profile
contains `username`, `freeform_context`, and `structured_fields` with
`role_target`, `primary_skills`, `experience_years`, `preferred_locations`,
`remote_only`, `secondary_skills`, and `min_salary_inr`. Requests reject
unknown properties and enforce field limits.

Profiles are atomically saved as `user-assets/<username>/profile.json`. The
server creates `user-assets/<username>/files` for user-owned assets, but does
not expose files through the profile API. Usernames are restricted to a
single safe path component. The data root can be set with
`JEVSCOUT_USER_ASSETS_DIR`; by default it is `<JEVSCOUT_DATA_DIR>/user-assets`
(with `data` as the default data directory).
