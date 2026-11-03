#!/usr/bin/env python3
"""Job Radar: pulls job postings from company career boards and job APIs,
keeps entry-level US software roles, scores fit, and writes docs/jobs.json."""
import hashlib
import html
import json
import os
import re
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import requests

import config

ROOT = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(ROOT, "docs")
NOW = datetime.now(timezone.utc)
SESSION = requests.Session()
SESSION.headers["User-Agent"] = "job-radar/1.0 (personal job search tool)"

STATUS = {}  # source label -> {"ok": bool|None, "count": int, "error"/"note": str}


class SkipSource(Exception):
    """Raised when a source is intentionally turned off (e.g. its API key isn't set)."""


# ---------------------------------------------------------------- helpers
def get_json(url, **kw):
    kw.setdefault("timeout", 25)
    r = SESSION.get(url, **kw)
    r.raise_for_status()
    return r.json()


TAG_RE = re.compile(r"<[^>]+>")


def clean(text):
    if not text:
        return ""
    t = html.unescape(html.unescape(str(text)))  # Greenhouse double-escapes HTML
    t = TAG_RE.sub(" ", t)
    return re.sub(r"\s+", " ", t).strip()


def to_iso(v):
    if v in (None, "", 0):
        return None
    try:
        if isinstance(v, (int, float)) or (isinstance(v, str) and v.isdigit()):
            v = float(v)
            if v > 1e12:
                v /= 1000
            return datetime.fromtimestamp(v, timezone.utc).isoformat()
        d = datetime.fromisoformat(str(v).strip().replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d.astimezone(timezone.utc).isoformat()
    except Exception:
        for fmt in ("%B %d, %Y", "%m/%d/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(str(v).strip(), fmt).replace(tzinfo=timezone.utc).isoformat()
            except Exception:
                pass
    return None


def make(company, title, location, url, posted, desc, source, remote=False, sponsor=None):
    return {
        "company": (company or "").strip(),
        "title": clean(title),
        "location": clean(location),
        "url": url,
        "posted": to_iso(posted),
        "desc": clean(desc)[:8000],
        "source": source,
        "remote": bool(remote),
        "sponsor_hint": sponsor,
    }


def run_source(label, fn, *args):
    try:
        result = fn(*args)
        if isinstance(result, tuple):  # (jobs, note) from probe()
            jobs, note = result
            STATUS[label] = {"ok": True, "count": len(jobs), "note": note}
        else:
            jobs = result
            STATUS[label] = {"ok": True, "count": len(jobs)}
        return jobs
    except SkipSource as e:
        STATUS[label] = {"ok": None, "count": 0, "note": str(e)}
        print(f"  - {label}: {e}")
        return []
    except Exception as e:
        msg = str(e).split("\n")[0][:160]
        STATUS[label] = {"ok": False, "count": 0, "error": msg}
        print(f"  ! {label}: {msg}")
        return []


# ---------------------------------------------------------------- company boards
def greenhouse(slug, name):
    d = get_json(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true")
    return [
        make(name, j.get("title"), (j.get("location") or {}).get("name"), j.get("absolute_url"),
             j.get("first_published") or j.get("updated_at"), j.get("content"), "Greenhouse")
        for j in d.get("jobs", [])
    ]


def lever(slug, name):
    d = get_json(f"https://api.lever.co/v0/postings/{slug}?mode=json")
    out = []
    for j in d:
        cat = j.get("categories") or {}
        loc = cat.get("location") or ", ".join(cat.get("allLocations") or [])
        desc = " ".join([j.get("descriptionPlain") or ""]
                        + [clean(x.get("content")) for x in j.get("lists") or []]
                        + [j.get("additionalPlain") or ""])
        out.append(make(name, j.get("text"), loc, j.get("hostedUrl"), j.get("createdAt"), desc, "Lever",
                        remote=(j.get("workplaceType") == "remote")))
    return out


def ashby(slug, name):
    d = get_json(f"https://api.ashbyhq.com/posting-api/job-board/{slug}")
    out = []
    for j in d.get("jobs", []):
        if j.get("isListed") is False:
            continue
        locs = [j.get("location") or ""] + [s.get("location", "") for s in j.get("secondaryLocations") or []]
        out.append(make(name, j.get("title"), "; ".join(x for x in locs if x), j.get("jobUrl"),
                        j.get("publishedAt"), j.get("descriptionPlain") or j.get("descriptionHtml"), "Ashby",
                        remote=bool(j.get("isRemote")) or j.get("workplaceType") == "Remote"))
    return out


def workable(slug, name):
    d = get_json(f"https://apply.workable.com/api/v1/widget/accounts/{slug}?details=true")
    out = []
    for j in d.get("jobs", []):
        loc = ", ".join(x for x in [j.get("city"), j.get("state"), j.get("country")] if x)
        out.append(make(name, j.get("title"), loc, j.get("url") or j.get("application_url"),
                        j.get("published_on") or j.get("created_at"), j.get("description"), "Workable",
                        remote=j.get("telecommuting")))
    return out


def smartrecruiters(slug, name):
    d = get_json(f"https://api.smartrecruiters.com/v1/companies/{slug}/postings",
                 params={"limit": 100, "country": "us"})
    out = []
    for j in d.get("content", []):
        loc = j.get("location") or {}
        loc_s = ", ".join(x for x in [loc.get("city"), loc.get("region"), loc.get("country")] if x)
        out.append(make(name, j.get("name"), loc_s, f"https://jobs.smartrecruiters.com/{slug}/{j.get('id')}",
                        j.get("releasedDate"), "", "SmartRecruiters", remote=loc.get("remote")))
    return out


def probe(name, candidates):
    """Try each candidate board ID on Greenhouse, Lever and Ashby; use the first that works."""
    for slug in candidates:
        for platform, fn in (("Greenhouse", greenhouse), ("Lever", lever), ("Ashby", ashby)):
            try:
                return fn(slug, name), f"found on {platform} as '{slug}'"
            except requests.HTTPError:
                continue
    raise RuntimeError("not found on Greenhouse, Lever or Ashby (likely Workday or its own site); "
                       "remove it from 'try' in companies.json")


def amazon():
    out = []
    for q in config.AMAZON_QUERIES:
        d = get_json("https://www.amazon.jobs/en/search.json",
                     params={"base_query": q, "country": "USA", "result_limit": 100, "offset": 0, "sort": "recent"})
        for j in d.get("jobs", []):
            desc = " ".join(j.get(k) or "" for k in ("description", "basic_qualifications", "preferred_qualifications"))
            out.append(make("Amazon", j.get("title"), j.get("normalized_location") or j.get("location"),
                            "https://www.amazon.jobs" + (j.get("job_path") or ""), j.get("posted_date"), desc, "Amazon Jobs"))
    return out


# ---------------------------------------------------------------- lists & aggregators
SIMPLIFY_SPONSOR = {
    "Offers Sponsorship": "offers",
    "Does Not Offer Sponsorship": "no_sponsorship",
    "U.S. Citizenship is Required": "citizenship",
}


def simplify():
    last = None
    for branch in ("dev", "main"):
        try:
            d = get_json(f"https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/{branch}/.github/scripts/listings.json")
            break
        except Exception as e:
            last = e
    else:
        raise last
    out = []
    for j in d:
        if not j.get("active", True) or j.get("is_visible") is False:
            continue
        locs = "; ".join(j.get("locations") or [])
        out.append(make(j.get("company_name"), j.get("title"), locs, j.get("url"), j.get("date_posted"), "",
                        "SimplifyJobs New-Grad list", remote="remote" in locs.lower(),
                        sponsor=SIMPLIFY_SPONSOR.get(j.get("sponsorship"))))
    return out


def jsearch():
    key = os.environ.get("JSEARCH_KEY")
    if not key:
        raise SkipSource("turned off (JSEARCH_KEY secret not set)")
    headers = {"X-RapidAPI-Key": key, "X-RapidAPI-Host": "jsearch.p.rapidapi.com"}
    out = []
    for q in config.JSEARCH_QUERIES:
        # JSearch v5: no "page" param (pagination uses "cursor"); jobs are under data.jobs
        r = SESSION.get("https://jsearch.p.rapidapi.com/search", headers=headers, timeout=40,
                        params={"query": q, "num_pages": 1, "country": "us", "language": "en",
                                "date_posted": "3days"})
        if not r.ok:
            raise RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
        d = r.json()
        data = d.get("data") or []
        rows = data.get("jobs", []) if isinstance(data, dict) else data
        for j in rows:
            loc = ", ".join(x for x in [j.get("job_city"), j.get("job_state"), j.get("job_country")] if x)
            pub = j.get("job_publisher") or "web"
            out.append(make(j.get("employer_name"), j.get("job_title"), loc, j.get("job_apply_link"),
                            j.get("job_posted_at_datetime_utc"), j.get("job_description"),
                            f"Google for Jobs via JSearch ({pub})", remote=j.get("job_is_remote")))
    return out


def adzuna():
    app_id, app_key = os.environ.get("ADZUNA_APP_ID"), os.environ.get("ADZUNA_APP_KEY")
    if not (app_id and app_key):
        raise SkipSource("turned off (Adzuna keys not set)")
    out = []
    for q in config.ADZUNA_QUERIES:
        for page in (1, 2):
            d = get_json(f"https://api.adzuna.com/v1/api/jobs/us/search/{page}",
                         params={"app_id": app_id, "app_key": app_key, "results_per_page": 50,
                                 "what": q, "max_days_old": 14, "sort_by": "date"})
            for j in d.get("results", []):
                loc = ((j.get("location") or {}).get("display_name") or "") + ", US"
                out.append(make((j.get("company") or {}).get("display_name"), j.get("title"), loc,
                                j.get("redirect_url"), j.get("created"), j.get("description"), "Adzuna"))
    return out


def usajobs():
    key, email = os.environ.get("USAJOBS_KEY"), os.environ.get("USAJOBS_EMAIL")
    if not (key and email):
        raise SkipSource("turned off (USAJOBS secrets not set)")
    headers = {"Host": "data.usajobs.gov", "User-Agent": email, "Authorization-Key": key}
    out = []
    for q in config.USAJOBS_QUERIES:
        d = get_json("https://data.usajobs.gov/api/search", headers=headers,
                     params={"Keyword": q, "ResultsPerPage": 100, "DatePosted": 30})
        for item in (d.get("SearchResult") or {}).get("SearchResultItems", []):
            j = item.get("MatchedObjectDescriptor") or {}
            summary = ((j.get("UserArea") or {}).get("Details") or {}).get("JobSummary", "")
            url = (j.get("ApplyURI") or [j.get("PositionURI")])[0]
            out.append(make(j.get("OrganizationName"), j.get("PositionTitle"),
                            (j.get("PositionLocationDisplay") or "") + ", United States", url,
                            j.get("PublicationStartDate"), summary, "USAJOBS", sponsor="citizenship"))
    return out


def himalayas():
    out = []
    for offset in (0, 100, 200):
        d = get_json("https://himalayas.app/jobs/api", params={"limit": 100, "offset": offset})
        for j in d.get("jobs", []):
            restr = j.get("locationRestrictions") or []
            restr_s = ", ".join(r if isinstance(r, str) else (r.get("name") or "") for r in restr)
            if restr and "united states" not in restr_s.lower() and "usa" not in restr_s.lower():
                continue
            loc = "Remote, United States" if restr else "Remote"
            out.append(make(j.get("companyName"), j.get("title"), loc, j.get("applicationLink") or j.get("guid"),
                            j.get("pubDate"), j.get("description") or j.get("excerpt"), "Himalayas", remote=True))
    return out


def remotive():
    d = get_json("https://remotive.com/api/remote-jobs", params={"category": "software-dev", "limit": 300})
    out = []
    for j in d.get("jobs", []):
        loc = j.get("candidate_required_location") or ""
        out.append(make(j.get("company_name"), j.get("title"), "Remote, " + loc, j.get("url"),
                        j.get("publication_date"), j.get("description"), "Remotive", remote=True))
    return out


def remoteok():
    d = get_json("https://remoteok.com/api")
    out = []
    for j in d:
        if not isinstance(j, dict) or "position" not in j:
            continue  # first item is their legal notice
        out.append(make(j.get("company"), j.get("position"), "Remote, " + (j.get("location") or ""),
                        j.get("url"), j.get("date"), j.get("description"), "Remote OK", remote=True))
    return out


# ---------------------------------------------------------------- filtering
INCLUDE = re.compile(config.INCLUDE_TITLE, re.I)
ROLE = re.compile(config.ROLE_WORD, re.I)
EXCLUDE = re.compile(config.EXCLUDE_TITLE, re.I)
LEVEL_II = re.compile(r"\b(engineer|developer|sde)\s*(ii|2)\b|\bsde[\s-]?(ii|2)\b|\blevel\s*2\b", re.I)
NEW_GRAD = re.compile(r"new grad|graduate|early career|university|entry|associate|junior|\bjr\b|"
                      r"\b(engineer|developer|sde)\s*(i|1)\b|\bsde[\s-]?(i|1)\b|\blevel\s*1\b|202[6-7]", re.I)

STATES = ("AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY "
          "NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC").split()
STATE_NAMES = ("alabama|alaska|arizona|arkansas|california|colorado|connecticut|delaware|florida|georgia|hawaii|"
               "idaho|illinois|indiana|iowa|kansas|kentucky|louisiana|maine|maryland|massachusetts|michigan|"
               "minnesota|mississippi|missouri|montana|nebraska|nevada|new hampshire|new jersey|new mexico|new york|"
               "north carolina|north dakota|ohio|oklahoma|oregon|pennsylvania|rhode island|south carolina|"
               "south dakota|tennessee|texas|utah|vermont|virginia|washington|west virginia|wisconsin|wyoming")
US_CITY = (r"san francisco|seattle|boston|austin|chicago|los angeles|denver|atlanta|nyc|bay area|silicon valley|"
           r"palo alto|mountain view|sunnyvale|san jose|menlo park|redmond|bellevue|cambridge, ma|pittsburgh|"
           r"philadelphia|miami|dallas|houston|portland|salt lake|raleigh|washington, d\.?c")
US_RE = re.compile(rf"\b(united states|usa|u\.s\.a?\.?|us|{STATE_NAMES}|{US_CITY})\b", re.I)
STATE_RE = re.compile(r"(?:,|\s)\s*(" + "|".join(STATES) + r")\b")
NON_US_RE = re.compile(r"\b(canada|toronto|vancouver|montreal|ontario|london|united kingdom|uk|england|ireland|dublin|"
                       r"germany|berlin|munich|france|paris|netherlands|amsterdam|spain|madrid|barcelona|poland|"
                       r"warsaw|india|bangalore|bengaluru|hyderabad|pune|mumbai|delhi|gurgaon|chennai|singapore|"
                       r"japan|tokyo|australia|sydney|melbourne|brazil|sao paulo|mexico|argentina|israel|tel aviv|"
                       r"china|beijing|shanghai|hong kong|taiwan|korea|seoul|philippines|emea|apac|latam|europe|"
                       r"switzerland|zurich|sweden|stockholm|denmark|portugal|lisbon|romania|czech|prague)\b", re.I)
BOSTON_RE = re.compile(r"boston|cambridge,?\s*ma|somerville|waltham|burlington,?\s*ma|lexington,?\s*ma|"
                       r"massachusetts|\bMA\b|woburn|needham|quincy,?\s*ma")

NO_SPONSOR_RE = re.compile(
    r"(not|unable to|cannot|can't|won't|will not|do not|does not|don't|no)\s+(\w+\s+){0,4}sponsor"
    r"|without (the need for |requiring |needing )?(\w+\s+){0,3}sponsorship"
    r"|sponsorship (is |will )?not (be )?(available|offered|provided)", re.I)
CITIZEN_RE = re.compile(
    r"u\.?s\.? citizen(ship)?\s*(is\s+)?(required|only)|must be (a )?u\.?s\.? citizen|citizenship is required"
    r"|(security|secret|ts/sci|top secret) clearance|u\.?s\.? persons? (only|status)|\bitar\b", re.I)


def is_us(loc, remote):
    if not loc:
        return bool(remote)
    has_us = bool(US_RE.search(loc) or STATE_RE.search(loc))
    if has_us:
        return True
    if NON_US_RE.search(loc):
        return False
    return remote or "remote" in loc.lower() or "anywhere" in loc.lower()


SKILL_RES = [(label, re.compile(rx, re.I), w) for label, rx, w in config.SKILLS]


def fit(title, desc):
    if len(desc) < 200:
        return None, []  # not enough text to score honestly
    text = f"{title} {desc}"
    matched = [(label, w) for label, rx, w in SKILL_RES if rx.search(text)]
    score = min(100, round(100 * sum(w for _, w in matched) / config.FIT_TARGET))
    return score, [label for label, _ in matched]


def sponsorship(job):
    if job.get("sponsor_hint"):
        return job["sponsor_hint"]
    text = f"{job['title']} {job['desc']}"
    if CITIZEN_RE.search(text):
        return "citizenship"
    if NO_SPONSOR_RE.search(text):
        return "no_sponsorship"
    return None


def norm(s):
    s = (s or "").lower()
    s = re.sub(r"\b(inc|llc|ltd|corp|corporation|co|technologies|the)\b\.?", "", s)
    return re.sub(r"[^a-z0-9]+", "", s)


SOURCE_RANK = {"Greenhouse": 0, "Lever": 0, "Ashby": 0, "Workable": 0, "SmartRecruiters": 0, "Amazon Jobs": 0,
               "SimplifyJobs New-Grad list": 1, "Himalayas": 2, "Remotive": 2, "Remote OK": 2, "USAJOBS": 2,
               "Adzuna": 4}


def rank(src):
    return SOURCE_RANK.get(src, 3)  # JSearch = 3


def keep(job):
    t = job["title"]
    if not job["url"] or not t or not INCLUDE.search(t) or not ROLE.search(t) or EXCLUDE.search(t):
        return False
    if not is_us(job["location"], job["remote"]):
        return False
    if job["posted"] and datetime.fromisoformat(job["posted"]) < NOW - timedelta(days=config.MAX_AGE_DAYS):
        return False
    return True


# ---------------------------------------------------------------- main
def main():
    companies = json.load(open(os.path.join(ROOT, "companies.json")))
    board_fns = {"greenhouse": greenhouse, "lever": lever, "ashby": ashby,
                 "workable": workable, "smartrecruiters": smartrecruiters}
    tasks = []
    for kind, fn in board_fns.items():
        for slug, name in (companies.get(kind) or {}).items():
            tasks.append((f"{name} ({kind.title()})", fn, slug, name))
    for name, candidates in (companies.get("try") or {}).items():
        tasks.append((f"{name} (auto-detect)", probe, name, candidates))
    for label, fn in [("Amazon Jobs", amazon), ("SimplifyJobs New-Grad list", simplify),
                      ("JSearch (Google for Jobs)", jsearch), ("Adzuna", adzuna), ("USAJOBS", usajobs),
                      ("Himalayas", himalayas), ("Remotive", remotive), ("Remote OK", remoteok)]:
        tasks.append((label, fn))

    print(f"Fetching {len(tasks)} sources...")
    raw = []
    with ThreadPoolExecutor(max_workers=16) as pool:
        for jobs in pool.map(lambda t: run_source(t[0], t[1], *t[2:]), tasks):
            raw.extend(jobs)
    print(f"Fetched {len(raw)} postings")

    # filter + dedupe
    merged = {}
    for j in filter(keep, raw):
        loc0 = re.split(r"[;|/]", j["location"] or "remote")[0]
        key = f"{norm(j['company'])}|{norm(j['title'])}|{norm(loc0.split(',')[0])}"
        cur = merged.get(key)
        if cur is None:
            j["sources"] = [j["source"]]
            merged[key] = j
            continue
        if j["source"] not in cur["sources"]:
            cur["sources"].append(j["source"])
        if rank(j["source"]) < rank(cur["source"]):
            for f in ("url", "location", "company", "title", "source"):
                cur[f] = j[f]
        if len(j["desc"]) > len(cur["desc"]):
            cur["desc"] = j["desc"]
        cur["sponsor_hint"] = cur["sponsor_hint"] or j["sponsor_hint"]
        cur["posted"] = cur["posted"] or j["posted"]
        cur["remote"] = cur["remote"] or j["remote"]

    # first-seen tracking (for "New today")
    seen_path = os.path.join(DOCS, "seen.json")
    seen = json.load(open(seen_path)) if os.path.exists(seen_path) else {}
    first_run = not seen
    out = []
    for key, j in merged.items():
        jid = hashlib.sha1(key.encode()).hexdigest()[:12]
        first = seen.get(jid) or NOW.isoformat()
        seen[jid] = first
        score, matched = fit(j["title"], j["desc"])
        title = j["title"]
        level = "II" if LEVEL_II.search(title) else ("Entry" if NEW_GRAD.search(title) or "Simplify" in j["source"] else "Unspecified")
        out.append({
            "id": jid, "company": j["company"], "title": title, "location": j["location"] or "Remote",
            "url": j["url"], "posted": j["posted"], "first_seen": first,
            "new": (not first_run) and datetime.fromisoformat(first) > NOW - timedelta(hours=26),
            "remote": j["remote"] or "remote" in (j["location"] or "").lower(),
            "boston": bool(BOSTON_RE.search(j["location"] or "")),
            "level": level, "sponsor": sponsorship(j), "fit": score, "matched": matched,
            "source": j["source"], "sources": j["sources"],
        })

    cutoff = NOW - timedelta(days=90)
    seen = {k: v for k, v in seen.items() if datetime.fromisoformat(v) > cutoff}
    out.sort(key=lambda x: x["posted"] or x["first_seen"], reverse=True)

    os.makedirs(DOCS, exist_ok=True)
    json.dump({"generated_at": NOW.isoformat(), "count": len(out), "jobs": out},
              open(os.path.join(DOCS, "jobs.json"), "w"), separators=(",", ":"))
    json.dump(seen, open(seen_path, "w"), separators=(",", ":"))
    json.dump({"generated_at": NOW.isoformat(), "sources": STATUS},
              open(os.path.join(DOCS, "status.json"), "w"), indent=1)
    ok = sum(1 for s in STATUS.values() if s["ok"])
    off = sum(1 for s in STATUS.values() if s["ok"] is None)
    print(f"Kept {len(out)} jobs. Sources OK: {ok}/{len(STATUS) - off} ({off} turned off)")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        raise
