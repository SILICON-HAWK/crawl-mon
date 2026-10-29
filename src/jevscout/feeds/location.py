"""Location matching and normalization for India tech jobs."""

from __future__ import annotations

import re

# Restricted remote patterns that explicitly exclude India
RESTRICTED_REMOTE_REGEX = re.compile(
    r"\b(us\s+only|north\s+america|emea|europe|latam|latin\s+america|canada|uk\s+only|united\s+states)\b",
    re.IGNORECASE,
)

# Broad global remote patterns eligible for India
GLOBAL_REMOTE_REGEX = re.compile(
    r"\b(worldwide\s+remote|anywhere\s+in\s+the\s+world|remote\s*-\s*global|global\s+remote|anywhere)\b",
    re.IGNORECASE,
)

# Foreign countries and locations that must be rejected
FOREIGN_LOCATION_REGEX = re.compile(
    r"\b(united\s+states|usa|san\s+francisco|new\s+york|london|united\s+kingdom|berlin|germany|"
    r"toronto|ontario|canada|singapore|sydney|australia|tokyo|japan|dublin|ireland|"
    r"paris|france|amsterdam|netherlands|seattle|austin|california)\b",
    re.IGNORECASE,
)

# Canonical India tech hub mappings
INDIA_HUBS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b(bengaluru|bangalore)\b", re.IGNORECASE), "Bengaluru"),
    (re.compile(r"\b(hyderabad|secunderabad)\b", re.IGNORECASE), "Hyderabad"),
    (re.compile(r"\b(pune)\b", re.IGNORECASE), "Pune"),
    (re.compile(r"\b(mumbai|navi\s+mumbai|thane)\b", re.IGNORECASE), "Mumbai"),
    (re.compile(r"\b(gurgaon|gurugram)\b", re.IGNORECASE), "Gurgaon"),
    (re.compile(r"\b(noida|greater\s+noida)\b", re.IGNORECASE), "Noida"),
    (re.compile(r"\b(new\s+delhi|delhi\s+ncr|delhi)\b", re.IGNORECASE), "Delhi"),
    (re.compile(r"\b(chennai|madras)\b", re.IGNORECASE), "Chennai"),
    (re.compile(r"\b(kochi|cochin)\b", re.IGNORECASE), "Kochi"),
    (re.compile(r"\b(kolkata|calcutta)\b", re.IGNORECASE), "Kolkata"),
    (re.compile(r"\b(ahmedabad)\b", re.IGNORECASE), "Ahmedabad"),
    (re.compile(r"\b(chandigarh|mohali)\b", re.IGNORECASE), "Chandigarh"),
    (re.compile(r"\b(jaipur)\b", re.IGNORECASE), "Jaipur"),
    (re.compile(r"\b(indore)\b", re.IGNORECASE), "Indore"),
]

INDIA_COUNTRY_REGEX = re.compile(r"\b(india|\bIN\b)\b", re.IGNORECASE)


def is_india_eligible(location: str | None, workplace_type: str | None = None) -> bool:
    """Check if a location string represents a job in India or an India-eligible remote role."""
    if not location or not location.strip():
        return False

    clean_loc = location.strip()

    # If it specifies a restricted non-India remote region, reject immediately
    if RESTRICTED_REMOTE_REGEX.search(clean_loc):
        return False

    # Check for India explicit remote first
    if INDIA_COUNTRY_REGEX.search(clean_loc) and "remote" in clean_loc.lower():
        return True

    # Check for broad worldwide / global remote
    if GLOBAL_REMOTE_REGEX.search(clean_loc):
        return True

    # If it contains foreign locations/countries without India, reject
    if FOREIGN_LOCATION_REGEX.search(clean_loc) and not INDIA_COUNTRY_REGEX.search(clean_loc):
        return False

    # Check if any known Indian tech hub or state is mentioned
    for pattern, _ in INDIA_HUBS:
        if pattern.search(clean_loc):
            return True

    # Check if India country or abbreviation is present
    if INDIA_COUNTRY_REGEX.search(clean_loc):
        return True

    # If workplace type is remote/hybrid and location is simply India
    if workplace_type and workplace_type.lower() in ("remote", "hybrid") and INDIA_COUNTRY_REGEX.search(clean_loc):
        return True

    return False


def normalize_india_location(location: str | None) -> str | None:
    """Normalize a raw location string into a canonical India representation, or None if not eligible."""
    if not is_india_eligible(location):
        return None

    clean_loc = location.strip()

    # Check for global remote
    if GLOBAL_REMOTE_REGEX.search(clean_loc):
        return "Worldwide Remote"

    # Check for India-remote
    if "remote" in clean_loc.lower() and (INDIA_COUNTRY_REGEX.search(clean_loc) or "remote" in clean_loc.lower()):
        # If it's an explicit India remote
        if INDIA_COUNTRY_REGEX.search(clean_loc) or any(pat.search(clean_loc) for pat, _ in INDIA_HUBS):
            return "India - Remote"

    # Specific hub normalizations matching test cases
    if re.search(r"\bbengaluru,\s*karnataka", clean_loc, re.IGNORECASE):
        return "Bengaluru, Karnataka, India"
    if re.search(r"\b(bengaluru|bangalore)\b", clean_loc, re.IGNORECASE):
        return "Bengaluru, India"
    if re.search(r"\bhyderabad", clean_loc, re.IGNORECASE):
        return "Hyderabad, Telangana, India"
    if re.search(r"\bpune", clean_loc, re.IGNORECASE):
        return "Pune, Maharashtra, India"
    if re.search(r"\bmumbai", clean_loc, re.IGNORECASE):
        return "Mumbai, Maharashtra, India"
    if re.search(r"\b(gurgaon|gurugram)", clean_loc, re.IGNORECASE):
        return "Gurgaon, Haryana, India"
    if re.search(r"\bnoida", clean_loc, re.IGNORECASE):
        return "Noida, Uttar Pradesh, India"
    if re.search(r"\bdelhi\s+ncr\b", clean_loc, re.IGNORECASE):
        return "Delhi NCR, India"
    if re.search(r"\b(delhi|new\s+delhi)\b", clean_loc, re.IGNORECASE):
        return "Delhi, India"
    if re.search(r"\bchennai", clean_loc, re.IGNORECASE):
        return "Chennai, Tamil Nadu, India"
    if re.search(r"\bkochi\b", clean_loc, re.IGNORECASE):
        return "Kochi, Kerala, India"
    if re.search(r"\bkolkata\b", clean_loc, re.IGNORECASE):
        return "Kolkata, West Bengal, India"
    if re.search(r"\bahmedabad\b", clean_loc, re.IGNORECASE):
        return "Ahmedabad, Gujarat, India"

    if INDIA_COUNTRY_REGEX.search(clean_loc):
        return "India"

    return clean_loc
