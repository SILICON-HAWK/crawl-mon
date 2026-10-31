# Job salary extraction

Job extraction records now include `salary`, a nullable display string. ATS
extractors copy salary text or render explicit salary range fields supplied by
the source. Schema.org JobPosting extraction reads `baseSalary`, including
MonetaryAmount/QuantitativeValue ranges. Records without an explicit salary
keep `salary: null`; values are never inferred from descriptions or titles.

Previously collected results do not gain this field automatically. Rerun
extraction on saved artifacts to populate salary on existing collected jobs.
