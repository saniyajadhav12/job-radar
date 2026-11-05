"""Settings for Job Radar. Edit this file to change what the portal shows."""

# ---------- Titles ----------
# A posting is kept only if its title matches INCLUDE_TITLE and does NOT match EXCLUDE_TITLE.
# Role types kept: general software engineer/developer, full-stack, front-end, mobile.
INCLUDE_TITLE = (
    r"\bsoftware (engineer|developer|development engineer|dev)\b"
    r"|\b(sde|swe)\b"
    r"|\bfull[\s-]?stack\b"
    r"|\b(front[\s-]?end|frontend)\b"
    r"|\bweb (developer|engineer)\b"
    r"|\bapplications? (developer|engineer)\b"
    r"|\bui (developer|engineer)\b"
    r"|\bproduct engineer\b"
    r"|\b(ios|android|mobile|react native) (engineer|developer)\b"
    r"|it specialist \(appsw"
)
EXCLUDE_TITLE = (
    r"\b(senior|sr|staff|principal|lead|manager|director|head|architect|vp|"
    r"intern|internship|co-?op|apprentice|distinguished|fellow|contractor|"
    r"part[\s-]?time|sales|support|solutions|recruiter|"
    r"iii|iv|level\s*[3-9])\b"
    r"|\b(engineer|developer|sde)\s*(3|4|5|6|v)\b"
)
# Specialties you don't want. Skipped when the title also says full-stack / front-end / mobile,
# so "Full Stack Engineer (Frontend + Backend)" is still kept.
SPECIALTY_EXCLUDE = (
    r"\b(back[\s-]?end|data|machine learning|ml|ai/ml|infrastructure|devops|sre|"
    r"site reliability|security|embedded|firmware|hardware|network|networking|kernel|compiler|"
    r"gpu|robotics|autonomy|simulation|test|testing|qa|sdet|quality|mechanical|electrical|"
    r"manufacturing|sourcing|supply chain|field|salesforce|mainframe|cobol)\b"
)
KEEP_EVEN_IF = r"\bfull[\s-]?stack\b|\b(front[\s-]?end|frontend)\b|\b(ios|android|mobile|react native)\b"

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
