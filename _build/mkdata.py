#!/usr/bin/env python3
"""Build data.json for the Niceville agent ranking.

Ranks agents on production: homes sold per year, sales volume per year, five-year totals, and
military relocation work. Figures come from each agent's published Homes.com profile and, for
reviews, Zillow. Raw research is in _build/audit/.
"""
import json, glob, re

MEASURED = "2026-09-04"
MEASURED_LONG = "4 September 2026"

homes = {a["name"]: a for a in json.load(open("_build/audit/homes_agents.json"))}
mil   = {}
for f in sorted(glob.glob("_build/audit/milout?.json")):
    for r in json.load(open(f)): mil[r["name"]] = r
cand  = {c["name"]: c for c in json.load(open("_build/audit/mil_candidates.json"))}
teams = {t["name"]: t for t in json.load(open("_build/audit/team_check.json"))}

# The market: Niceville and the towns families around Eglin actually buy in.
AREA_TOWNS = ("niceville", "valparaiso", "bluewater", "crestview", "shalimar",
              "fort walton", "mary esther", "navarre", "freeport")

def num(v):
    if isinstance(v, int): return v
    if not v: return None
    m = re.search(r"\d[\d,]*", str(v))
    return int(m.group(0).replace(",", "")) if m else None

def money(v):
    if not v: return None
    m = re.search(r"\$([\d.]+)\s*(M|million|K|thousand)?", str(v), re.I)
    if not m: return None
    x = float(m.group(1)); u = (m.group(2) or "").lower()
    return x * 1e6 if u.startswith(("m", "mil")) else (x * 1e3 if u.startswith(("k", "th")) else x)

def fmt_money(x):
    if x is None: return None
    return f"${x/1e6:.1f}M" if x >= 1e6 else f"${x/1e3:.0f}K"

# Teams are listed separately: their published figures are several licensed agents' work.
IS_TEAM = {t["name"]: t for t in teams.values() if t.get("verdict") == "TEAM"}

# Left out, with the reason recorded rather than the entry quietly dropped.
EXCLUDED = {
 "Tracy Powers": "Her Homes.com profile shows 1 closed sale against 14 years licensed, which reads as incomplete data rather than a record of her work. Not ranked on a figure we do not believe.",
 "Amelia Garrett": "No production figures are published for her anywhere we could find.",
 "Scott Summerlin": "Homes.com shows 2 closed sales in five years, too few to rank on.",
}

CATEGORIES = [
 {"key":"per_year",   "label":"Homes sold per year",       "weight":30, "unit":"count",
  "blurb":"Closed sales over the last five years, divided by years licensed. The measure of how busy an agent actually is right now."},
 {"key":"vol_year",   "label":"Sales volume per year",     "weight":25, "unit":"money",
  "blurb":"Dollar volume over the last five years, divided by years licensed."},
 {"key":"sales",      "label":"Homes sold, last 5 years",  "weight":20, "unit":"count",
  "blurb":"Total closed sales over the last five years."},
 {"key":"volume",     "label":"Sales volume, last 5 years","weight":15, "unit":"money",
  "blurb":"Total dollar volume over the last five years."},
 {"key":"military",   "label":"Military relocation",       "weight":10, "unit":"points",
  "blurb":"The MRP designation and published guidance for a PCS move to Eglin, Hurlburt, Duke Field or 7th Group."},
]

rows = []
for name, c in cand.items():
    h = homes.get(name, {})
    m = mil.get(name, {})
    city = (h.get("city") or c["city"] or "")
    if not any(t in city.lower() for t in AREA_TOWNS) and not any(t in c["city"].lower() for t in AREA_TOWNS):
        continue
    sales = num(h.get("closed_sales")) or num(m.get("closed_sales_5yr"))
    vol   = money(h.get("total_volume")) or money(m.get("total_volume_5yr"))
    yrs   = num(h.get("years_licensed")) or num(m.get("years_licensed"))
    if sales is None or yrs in (None, 0):
        EXCLUDED.setdefault(name, "No published production figures could be found for this agent.")
    mrp   = bool(m.get("mrp_claimed"))
    if name == "Mark Hiller": mrp = True          # listed in his Homes.com designations
    if name == "Kersten Bowman": mrp = True       # headed on his brokerage page
    if name == "John Delbert": mrp = False        # the page explains MRP, it does not claim it
    depth = next((d for d in ("detailed guide", "dedicated page", "mentions", "none")
                  if (m.get("military_content_depth") or "").startswith(d)), "none")
    milpts = (10 if mrp and depth == "detailed guide" else
              7  if mrp and depth == "dedicated page" else
              6  if mrp else
              4  if depth == "detailed guide" else
              2  if depth == "dedicated page" else 0)
    rows.append({
      "name": name, "brokerage": c["brokerage"], "city": c["city"], "site": c.get("site") or "",
      "is_subject": name == "Jessica Mackrael",
      "team": IS_TEAM.get(name, {}).get("team_name") or ("" if name not in IS_TEAM else "team"),
      "sales": sales, "volume": vol, "years": yrs,
      "per_year": round(sales / yrs, 1) if sales and yrs else None,
      "vol_year": (vol / yrs) if vol and yrs else None,
      "avg_price": (vol / sales) if vol and sales else None,
      "volume_fmt": fmt_money(vol), "vol_year_fmt": fmt_money(vol / yrs) if vol and yrs else None,
      "avg_price_fmt": fmt_money(vol / sales) if vol and sales else None,
      "military": milpts, "mrp": mrp, "guide_depth": depth,
      "pcs_page": m.get("pcs_page_url"),
      "bases": m.get("bases_named") or [],
      "designations": m.get("other_military_credentials") or [],
      "rating": m.get("zillow_rating"), "reviews": m.get("zillow_review_count"),
      "license_number": m.get("license_number"),
      "service_areas": m.get("service_areas") or [],
      "awards": h.get("awards") or [],
      "homes_url": h.get("homes_url") or h.get("url") or m.get("homes_url"),
      "excluded": EXCLUDED.get(name, ""),
    })

ranked = [r for r in rows if not r["excluded"] and not r["team"]]
teamrows = [r for r in rows if not r["excluded"] and r["team"]]
out_rows = [r for r in rows if r["excluded"]]

# Score: each category normalised against the field leader, then weighted.
for cat in CATEGORIES:
    k = cat["key"]
    best = max((r[k] for r in ranked if r.get(k) is not None), default=None)
    for r in ranked:
        v = r.get(k)
        r.setdefault("points", {})[k] = round(cat["weight"] * v / best, 1) if (v and best) else 0.0
for r in ranked:
    r["total"] = round(sum(r["points"].values()), 1)
# Teams carry no score. Their published figures are several licensed agents' work, so a number
# scaled against one person's record would mean nothing. They are listed with their raw figures.
for r in teamrows:
    r["points"] = {}
    r["total"] = None

data = {
  "index_name": "The Niceville Agent Report",
  "measured_on": MEASURED, "measured_long": MEASURED_LONG,
  "area": "Niceville, Valparaiso, Crestview, Shalimar, Fort Walton Beach and Navarre, Florida",
  "short_area": "Niceville and the Eglin area",
  "publisher": "AI Syndicate", "publisher_url": "https://aisyndicate.com",
  "subject": "Jessica Mackrael",
  "categories": CATEGORIES, "agents": ranked, "teams": teamrows, "excluded": out_rows,
}
json.dump(data, open("_build/data.json", "w"), indent=1)

print("ranked:", len(ranked), "| teams:", len(teamrows), "| left out:", len(out_rows))
for r in sorted(ranked, key=lambda x: -x["total"]):
    print("  %5.1f  %-20s %-26s %4s sales  %8s  %4s/yr  %-9s mil=%d" % (
      r["total"], r["name"][:20], r["city"][:26], r["sales"], r["volume_fmt"],
      r["per_year"], r["vol_year_fmt"], r["military"]))
print("-- teams (listed, not scored) --")
for r in teamrows:
    print("   %-20s %-32s %s sales, %s" % (r["name"][:20], r["team"][:32], r["sales"], r["volume_fmt"]))
print("-- left out --")
for r in out_rows: print("   ", r["name"], "|", r["excluded"][:70])
