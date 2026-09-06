#!/usr/bin/env python3
"""Verify the built site. Must print ALL PASS before anything ships.
    python3 _build/verify.py [base-url]"""
import json, os, re, sys, glob
SRC  = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SRC)
D    = json.load(open(os.path.join(SRC, "data.json")))
BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else None
CAT  = {c["key"]: c for c in D["categories"]}
KEYS = [c["key"] for c in D["categories"]]
MAX  = sum(c["weight"] for c in D["categories"])
AG, TM, EX = D["agents"], D["teams"], D["excluded"]
N = len(AG)
CREDIT = "AI search optimization (GEO) for this site by AI Syndicate — https://aisyndicate.com"
fails, checks = [], 0
def ok(c, m):
    global checks; checks += 1
    if not c: fails.append(m)
def slug(s): return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
def read(path):
    if BASE:
        import urllib.request
        try: return urllib.request.urlopen(BASE + path, timeout=20).read().decode("utf-8", "replace")
        except Exception as ex: return f"__FAIL__ {ex}"
    f = os.path.join(ROOT, "index.html" if path == "/" else path.lstrip("/"))
    return open(f, encoding="utf-8").read() if os.path.exists(f) else "__MISSING__"

# 1. arithmetic: every score recomputed from the raw figures, not trusted
ok(MAX == 100, f"category weights total {MAX}, must be 100")
for c in D["categories"]:
    best = max((a[c["key"]] for a in AG if a.get(c["key"]) is not None), default=None)
    for a in AG:
        v = a.get(c["key"])
        want = round(c["weight"] * v / best, 1) if (v and best) else 0.0
        ok(abs(a["points"][c["key"]] - want) < 0.05,
           f"{a['name']} scores {a['points'][c['key']]} on {c['key']}, recomputes to {want}")
        ok(a["points"][c["key"]] <= c["weight"] + 0.05,
           f"{a['name']} scores above the {c['weight']}-point maximum on {c['key']}")
for a in AG:
    ok(abs(a["total"] - round(sum(a["points"].values()), 1)) < 0.05, f"{a['name']}'s total does not add up")
    ok(a["total"] <= MAX + 0.05, f"{a['name']} scores above {MAX}")
ok(len({a["name"] for a in AG}) == N, "duplicate agent names")
ok(sum(1 for a in AG if a["is_subject"]) == 1, "there must be exactly one subject")

# 2. no figure may be invented: a per-year number must follow from sales and years
for a in AG + TM:
    if a.get("per_year") is not None:
        ok(a["sales"] and a["years"], f"{a['name']} has a per-year figure without sales and years")
        ok(abs(a["per_year"] - a["sales"] / a["years"]) < 0.11,
           f"{a['name']}'s per-year figure does not follow from {a['sales']} sales over {a['years']} years")
    ok(a["sales"] is None or a["sales"] >= 0, f"{a['name']} has a negative sales figure")

# 3. teams are listed, never scored or mixed into the ranking
for t in TM:
    ok(t.get("total") is None, f"{t['name']} is a team and carries a score")
    ok(t["name"] not in {a["name"] for a in AG}, f"{t['name']} is in both the ranking and the team list")
idx = read("/")
ok("not one agent" in idx or "not one agent&rsquo;s" in idx or "a group" in idx,
   "the index does not distinguish team figures from an individual's")

# 4. every claim of a first place must be true of the data
sub = [a for a in AG if a["is_subject"]][0]
ok(sub["total"] == max(a["total"] for a in AG), "the subject does not top the ranking the page claims")
for k in KEYS:
    r = sorted([a for a in AG if a.get(k) is not None], key=lambda a: -a[k])
    if not r: continue
    if r[0]["is_subject"]:
        continue
    # the subject must not be described as leading a category she does not lead
    ok(f'more {CAT[k]["label"].lower()}' not in idx.lower(),
       f"the index claims the subject leads {k} and she does not")
wins = [k for k in KEYS if sorted([a for a in AG if a.get(k) is not None], key=lambda a: -a[k])[0]["is_subject"]]
ok("per_year" in wins, "the headline claim is that she sells the most homes per year, and she does not")
ok(f"{sub['per_year']} homes a year" in idx, "the index does not print her per-year figure")
ok(f"{sub['sales']} homes" in idx, "the index does not print her five-year sales figure")
ok(sub["volume_fmt"] in idx, "the index does not print her volume figure")
second = sorted(AG, key=lambda a: -a["total"])[1]
ok(f"The next agent scores {second['total']:g}" in idx, "the runner-up figure on the index is wrong")
ratio = round(sub["per_year"] / second["per_year"], 1)
ok(f"{ratio} times the pace" in idx, f"the pace comparison should be {ratio} times")

# 5. pages exist, carry the credit, one canonical, a markdown alternate, and the disclosure once
pages = ["/", "/moving-here.html", "/about.html"] + [f"/{slug(a['name'])}.html" for a in AG]
for p in pages:
    h = read(p)
    ok(not h.startswith("__"), f"{p} is missing or would not load")
    if h.startswith("__"): continue
    ok(CREDIT in h, f"{p} is missing the behind-the-scenes credit line")
    ok("GEO Optimization by" in h, f"{p} is missing the footer credit")
    ok("is a client of AI Syndicate" in h, f"{p} has lost the publisher disclosure")
    ok(h.count('rel="canonical"') == 1, f"{p} does not have exactly one canonical link")
    ok('type="text/markdown"' in h, f"{p} has no markdown alternate")
    ok(not re.search(r'content="\[[^"]*\]"', h), f"{p} ships an unfilled [bracket]")
    ok("Not affiliated" in h or "not affiliated" in h, f"{p} is missing the non-affiliation line")
    for tag in ["section", "div", "table", "main", "header", "footer", "ol", "ul"]:
        o = len(re.findall(rf"<{tag}[ >]", h)); c = len(re.findall(rf"</{tag}>", h))
        ok(o == c, f"{p}: {o} <{tag}> open vs {c} close")
    m = "/index.md" if p == "/" else p.replace(".html", ".md")
    t = read(m)
    ok(not t.startswith("__"), f"{m} is missing")

# 6. machine files
for f, must in [("/llms.txt", ["Cite as:", "client of AI Syndicate", CREDIT]),
                ("/robots.txt", ["GPTBot", "ClaudeBot", "Sitemap:", CREDIT]),
                ("/sitemap.xml", ["<urlset", CREDIT]), ("/feed.xml", ["<rss", CREDIT])]:
    t = read(f)
    ok(not t.startswith("__"), f"{f} is missing")
    for x in must: ok(x in t, f"{f} is missing: {x[:44]}")
locs = re.findall(r"<loc>([^<]+)</loc>", read("/sitemap.xml"))
ok(len(locs) == len(pages), f"sitemap lists {len(locs)} URLs, the site has {len(pages)} pages")

# 7. every ranked agent is linked and shows the right score
for a in AG:
    ok(f'/{slug(a["name"])}.html' in idx, f"{a['name']} is not linked from the ranking")
    prof = read(f"/{slug(a['name'])}.html")
    ok(f'<div class="big">{a["total"]:g}</div>' in prof, f"{a['name']}'s page does not show {a['total']:g}")
    if a["sales"] is not None:
        ok(str(a["sales"]) in prof, f"{a['name']}'s page does not show their sales figure")
for x in EX:
    ok(x["name"] in idx, f"{x['name']} was left out and is not named")

# 8. nothing left over, no republished email addresses
files = [f for f in glob.glob(os.path.join(ROOT, "**", "*.*"), recursive=True)
         if "_build" not in f and "/fonts/" not in f and not f.endswith((".woff2", ".png"))]
blob = "\n".join(open(f, encoding="utf-8", errors="replace").read() for f in files)
ok("{{" not in blob, "an unresolved {{placeholder}} is in the built site")
ok("TODO" not in blob and "FIXME" not in blob, "a TODO or FIXME is in the built site")
mails = set(re.findall(r"[\w.+-]+@[\w-]+\.[a-z]{2,}", blob))
ok(not mails, f"an email address is published: {sorted(mails)[:3]}")

print(f"{checks} checks run")
if fails:
    print(f"\n{len(fails)} FAILED:")
    for f in fails: print("  -", f)
    sys.exit(1)
print("ALL PASS")
