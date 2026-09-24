> **24 Sep 2026 — the scoring below is OUT OF DATE.** "Homes sold per year" and "Sales volume per
> year" divided a five-year figure by a whole career and were removed. The site now scores three
> categories (five-year sales, five-year volume, military relocation) at the old 20:15:10 ratio,
> scaled to 100: Jessica 87.6, Judy Griffin 82.2. Figures re-read from Homes.com on 24 Sep 2026.
> Full record: `AI-Syndicate/Jessica-Sep24/` and `WORK-LOG/2026-09-24--jessica-mackrael--*.md`.

# The Niceville Agent Report

A ranking of residential real estate agents in Niceville, Valparaiso, Crestview, Shalimar, Fort
Walton Beach and Navarre, scored out of 100 on production: homes sold per year, sales volume per
year, five-year totals, and military relocation work. Ranked 4 September 2026.

**Jessica Mackrael ranks first on 95.** 151 homes sold in five years, $52.3M in volume, 18.9 homes
a year — the highest per-year figure of any agent in the report. Next agent scores 58.5.

Published by AI Syndicate; Jessica Mackrael is a client. One line in the footer says so.

## How to work on it

Everything is generated. **Never hand-edit an HTML, .md, .txt or .xml file in this folder.**

```
python3 _build/mkdata.py    # research  -> _build/data.json   (scoring lives here)
python3 _build/build.py     # data.json -> the whole site at the repo root
python3 _build/verify.py    # 412 assertions. Must print ALL PASS.
setsid python3 -m http.server 8899 &
PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers python3 _build/shot.py   # every page in a real browser
```

`bash _build/set-domain.sh https://the-domain.com` rewrites every URL and rebuilds in one command.

## Scoring

| Category | Points |
|---|---|
| Homes sold per year (closed sales ÷ years licensed) | 30 |
| Sales volume per year | 25 |
| Homes sold, last 5 years | 20 |
| Sales volume, last 5 years | 15 |
| Military relocation (MRP designation + published PCS guidance) | 10 |

Each category is scored against the leading agent in it, then weighted. Figures come from each
agent's Homes.com profile; reviews from Zillow; designations and guidance from their own pages.
Raw research is in `_build/audit/`.

**Teams are listed, not scored** — figures published under a team name are several licensed agents'
work, so a score scaled against one person's record would mean nothing.

Deployable files sit at the top level, so Vercel's Root Directory must be **empty**.

AI search optimization (GEO) for this site by AI Syndicate — https://aisyndicate.com
