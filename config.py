"""Settings for Job Radar. Edit this file to change what the portal shows."""

# ---------- Titles ----------
# A posting is kept only if its title matches INCLUDE_TITLE and ROLE_WORD,
# and does NOT match EXCLUDE_TITLE.
INCLUDE_TITLE = (
    r"\b(software|sde|swe|full[\s-]?stack|front[\s-]?end|frontend|web|"
    r"applications?|ui|react|product)\b|it specialist \(appsw"
)
ROLE_WORD = r"\b(engineer|developer|sde|swe|programmer|appsw)"
EXCLUDE_TITLE = (
    r"\b(senior|sr|staff|principal|lead|manager|director|head|architect|vp|"
    r"intern|internship|co-?op|apprentice|distinguished|fellow|contractor|"
    r"part[\s-]?time|sales|support|solutions|test|qa|sdet|recruiter|"
    r"iii|iv|level\s*[3-9])\b"
    r"|\b(engineer|developer|sde)\s*(3|4|5|6|v)\b"
)

# ---------- Freshness ----------
MAX_AGE_DAYS = 30          # drop postings older than this (when a date is known)

# ---------- Your skills (fit score) ----------
# (label, regex, weight). Fit % = matched weight / FIT_TARGET, capped at 100.
SKILLS = [
    ("React", r"\breact(\.js|js)?\b(?![\s-]?native)", 3),
    ("React Native", r"\breact[\s-]?native\b", 3),
    ("TypeScript", r"\btypescript\b", 3),
    ("JavaScript", r"\bjavascript\b", 2),
    ("Next.js", r"\bnext\.?js\b", 2),
    ("Node.js", r"\bnode(\.js|js)?\b", 2),
    ("Python", r"\bpython\b", 2),
    ("FastAPI", r"\bfastapi\b", 2),
    ("Front-end", r"\bfront[\s-]?end\b", 2),
    ("Full-stack", r"\bfull[\s-]?stack\b", 2),
    ("PostgreSQL", r"\bpostgres(ql)?\b", 1),
    ("SQL", r"\bsql\b", 1),
    ("Docker", r"\bdocker\b", 1),
    ("REST", r"\brest(ful)?\b", 1),
    ("GraphQL", r"\bgraphql\b", 1),
    ("AWS", r"\baws\b|amazon web services", 1),
    ("HTML/CSS", r"\bhtml5?\b|\bcss3?\b", 1),
    ("Redux", r"\bredux\b", 1),
    ("Mobile", r"\bmobile\b|\bios\b|\bandroid\b", 1),
    ("CI/CD", r"\bci/cd\b|github actions", 1),
]
FIT_TARGET = 14

# ---------- Search queries for aggregator APIs ----------
# JSearch's free tier allows only a small number of requests per month.
# Each query below = 1 request per day, so keep this list short (4 = ~120/month).
JSEARCH_QUERIES = [
    "software engineer new grad in United States",
    "entry level software engineer in United States",
    "frontend engineer entry level in United States",
    "full stack engineer entry level in United States",
]
ADZUNA_QUERIES = [
    "software engineer",
    "software developer",
    "frontend engineer",
    "full stack engineer",
]
USAJOBS_QUERIES = ["software developer", "software engineer"]
AMAZON_QUERIES = ["software development engineer", "software engineer"]
