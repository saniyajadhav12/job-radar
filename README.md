# Job Radar

A personal job portal that collects entry-level US software engineering roles every morning, from company career boards and job APIs, into one page. Each listing links straight to the application.

## What it pulls from

| Source | What it covers | Key needed |
|---|---|---|
| Greenhouse, Lever, Ashby, SmartRecruiters (Workable supported) | ~130 company career boards listed in `companies.json` | No |
| Amazon Jobs | Amazon SDE / SWE postings | No |
| SimplifyJobs New-Grad list | Community-maintained new-grad list, incl. Google, Microsoft, Meta, Apple | No |
| JSearch | Google for Jobs (listings that also appear on LinkedIn, Indeed, Glassdoor, ZipRecruiter) | Yes |
| Adzuna | Large US job aggregator | Yes |
| USAJOBS | Federal software jobs (marked as citizenship-required) | Yes |
| Himalayas, Remotive, Remote OK | Remote roles | No |

Postings are filtered to software/front-end/full-stack titles, entry level or Level II (no senior, staff, lead, intern), US or US-remote, and posted in the last 30 days. Duplicates across sources are merged, with the company's own posting preferred.

## One-time setup (about 15 minutes)

### 1. Create the repository
1. Go to github.com → **New repository**. Name it `job-radar`.
2. Choose **Public** (needed for free GitHub Pages; if you have the free GitHub Student Developer Pack you can choose Private). Don't add a README.
3. In Terminal, go into the unzipped `job-radar` folder (the one containing this README) and run:
   ```bash
   cd ~/Downloads/job-radar   # adjust if you moved it
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/YOUR-USERNAME/job-radar.git
   git push -u origin main
   ```

### 2. Get the three API keys
- **JSearch:** sign up at rapidapi.com, open the "JSearch" API (by OpenWeb Ninja), subscribe to the free **Basic** plan, and copy your `X-RapidAPI-Key`. The free plan allows only a limited number of requests per month; the portal uses 4 per day by default. Check the plan page for the current limit and trim `JSEARCH_QUERIES` in `config.py` if needed.
- **Adzuna:** sign up at developer.adzuna.com → copy your **Application ID** and **Application Key**.
- **USAJOBS:** request a key at developer.usajobs.gov/apirequest. The key is emailed to you. Note which email you used.

### 3. Add the keys to GitHub
In the repo: **Settings → Secrets and variables → Actions → New repository secret**. Add five secrets (names must match exactly):

| Name | Value |
|---|---|
| `JSEARCH_KEY` | your RapidAPI key |
| `ADZUNA_APP_ID` | Adzuna Application ID |
| `ADZUNA_APP_KEY` | Adzuna Application Key |
| `USAJOBS_KEY` | USAJOBS key |
| `USAJOBS_EMAIL` | the email you requested the USAJOBS key with |

Secrets are never visible on the page or in the repo. If a key is missing, that source is just skipped.

### 4. Turn on the website
**Settings → Pages →** Source: **Deploy from a branch**, Branch: **main**, Folder: **/docs** → Save.
Your portal will be at `https://YOUR-USERNAME.github.io/job-radar/`. Bookmark it.

### 5. Run it the first time
**Actions** tab → if asked, click **"I understand my workflows, go ahead and enable them"** → choose **Update jobs** → **Run workflow**. It takes a few minutes; then refresh your portal.

After this it runs on its own every morning (about 6–7 AM Boston time).

## Using the portal
- **Apply** opens the posting. **Mark applied** moves it to the Applied tab with the date. **Hide** removes it from your list (undo from the Hidden tab).
- Applied and Hidden are saved in your browser, so use the same browser on the same device. (They don't sync between laptop and phone.)
- **New today** means the role first appeared in the last daily update. On the very first run nothing is marked new.
- **Fit** is a keyword match between the job description and your skills in `config.py`. It shows "–" when the source gives no description (SimplifyJobs, SmartRecruiters). It's a quick sorting aid, not a judgment of the role.
- **Sponsorship tags** come from SimplifyJobs' labels where available, and otherwise from phrases in the job description (e.g. "unable to sponsor", "must be a U.S. citizen", "security clearance"). Wording varies, so always confirm on the posting itself.

## Customizing
- **Add/remove companies:** edit `companies.json`. The key is the board ID from the company's careers URL: `boards.greenhouse.io/<id>`, `jobs.lever.co/<id>`, `jobs.ashbyhq.com/<id>`.
- **Failing sources:** expand "Sources" at the bottom of the portal. A 404 usually means that company uses a different board ID or a different job system; fix or delete its line.
- **Titles, skills, fit scoring, age limit, search queries:** edit `config.py`.
- **Run time:** change the `cron` line in `.github/workflows/update-jobs.yml`.

## Run locally (optional)
```bash
pip install -r requirements.txt
export JSEARCH_KEY=... ADZUNA_APP_ID=... ADZUNA_APP_KEY=... USAJOBS_KEY=... USAJOBS_EMAIL=...
python fetch_jobs.py
cd docs && python -m http.server 8000   # open http://localhost:8000
```
