#!/usr/bin/env python3
"""Run the public checks against every agent's primary published URL.
Everything here is fetched over plain HTTPS from a public address. No logins, no APIs.
Writes raw evidence to checks.json so every score on the site can be re-derived."""
import json, re, sys, time, urllib.parse as up
import requests

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")
H = {"User-Agent": UA, "Accept": "text/html,application/xhtml+xml,*/*"}
TIMEOUT = 25

AI_BOTS = ["gptbot", "oai-searchbot", "chatgpt-user", "perplexitybot", "claudebot",
           "anthropic-ai", "google-extended", "ccbot", "bingbot", "applebot-extended",
           "cohere-ai", "meta-externalagent", "youbot", "amazonbot", "perplexity-user"]

def get(url, allow_redirects=True):
    try:
        r = requests.get(url, headers=H, timeout=TIMEOUT, allow_redirects=allow_redirects)
        return {"ok": True, "status": r.status_code, "url": r.url,
                "text": r.text if len(r.text) < 900000 else r.text[:900000],
                "headers": {k.lower(): v for k, v in r.headers.items()}}
    except Exception as e:
        return {"ok": False, "status": None, "url": url, "text": "", "headers": {},
                "error": type(e).__name__ + ": " + str(e)[:200]}

def origin(url):
    p = up.urlparse(url if "://" in url else "https://" + url)
    return f"{p.scheme}://{p.netloc}"

def jsonld_blocks(html_text):
    out = []
    for m in re.finditer(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
                         html_text, re.S | re.I):
        raw = m.group(1).strip()
        try:
            out.append(json.loads(raw))
        except Exception:
            out.append({"__unparsed__": raw[:200]})
    return out

def types_in(obj, acc=None):
    if acc is None: acc = set()
    if isinstance(obj, dict):
        t = obj.get("@type")
        if isinstance(t, str): acc.add(t)
        elif isinstance(t, list): acc.update([x for x in t if isinstance(x, str)])
        for v in obj.values(): types_in(v, acc)
    elif isinstance(obj, list):
        for v in obj: types_in(v, acc)
    return acc

def check(agent):
    url = agent["primary_url"]
    o = origin(url)
    ev = {"primary_url": url, "origin": o, "checked_at": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())}
    page = get(url)
    ev["page_status"] = page["status"]
    ev["page_error"] = page.get("error")
    ev["final_url"] = page["url"]
    html_text = page["text"] or ""
    low = html_text.lower()

    # --- machine-readable identity: JSON-LD naming a person/agent
    blocks = jsonld_blocks(html_text)
    tset = set()
    for b in blocks: tset |= types_in(b)
    ev["jsonld_types"] = sorted(tset)
    ev["jsonld_count"] = len(blocks)
    person_types = {"RealEstateAgent", "Person", "LocalBusiness", "RealEstateOrganization"}
    name_in_ld = agent["name"].split()[-1].lower() in json.dumps(blocks).lower() if blocks else False
    ev["name_in_jsonld"] = name_in_ld
    ev["chk_schema"] = bool(tset & person_types) and name_in_ld

    # --- contact details on the page they publish
    phone_re = re.compile(r'(\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})')
    ev["phones_found"] = sorted(set(phone_re.findall(html_text)))[:6]
    mails = re.findall(r'mailto:([^"\'<>\s?]+)', html_text, re.I)
    mails += re.findall(r'[\w.+-]+@[\w-]+\.[\w.]{2,}', re.sub(r'<[^>]+>', ' ', html_text))
    mails = [m for m in mails if not m.lower().endswith(('.png', '.jpg', '.webp', '.svg'))]
    ev["emails_found"] = sorted(set(m.lower() for m in mails))[:6]
    ev["chk_phone"] = len(ev["phones_found"]) > 0
    ev["chk_email"] = len(ev["emails_found"]) > 0
    ev["chk_address"] = bool(re.search(r'\b(FL|Florida)\b[ ,]*3\d{4}', html_text)) or \
                        bool(re.search(r'\d{2,6}\s+[A-Z][A-Za-z.\- ]{2,30}\s(St|Street|Rd|Road|Hwy|Highway|Pkwy|Parkway|Ave|Avenue|Blvd|Boulevard|Dr|Drive|Way|Ln|Lane|Ct)\b', html_text))
    ev["chk_contact_full"] = ev["chk_phone"] and ev["chk_email"] and ev["chk_address"]

    # --- security / transport
    hdr = page["headers"]
    ev["response_headers"] = {k: hdr.get(k) for k in
        ["strict-transport-security", "content-security-policy", "x-content-type-options",
         "x-frame-options", "referrer-policy", "permissions-policy"] if hdr.get(k)}
    ev["chk_https"] = page["url"].startswith("https://") if page["ok"] else False
    ev["chk_headers"] = bool(hdr.get("strict-transport-security")) and \
                        bool(hdr.get("x-content-type-options")) and \
                        bool(hdr.get("content-security-policy") or hdr.get("x-frame-options"))

    # --- machine files
    for name, key in [("robots.txt", "robots"), ("llms.txt", "llms"),
                      ("agents.md", "agentsmd"), ("sitemap.xml", "sitemap")]:
        r = get(f"{o}/{name}")
        body = (r["text"] or "")
        ctype = r["headers"].get("content-type", "")
        looks_html = body.lstrip()[:200].lower().startswith(("<!doctype", "<html")) or "text/html" in ctype
        good = bool(r["ok"] and r["status"] == 200 and body.strip() and not looks_html)
        ev[f"{key}_status"] = r["status"]
        ev[f"{key}_bytes"] = len(body)
        ev[f"{key}_ok"] = good
        ev[f"{key}_head"] = body[:400]
    ev["chk_llms"] = ev["llms_ok"]
    ev["chk_agents_md"] = ev["agentsmd_ok"]
    ev["chk_sitemap"] = ev["sitemap_ok"] and ("<urlset" in ev["sitemap_head"] or "<sitemapindex" in ev["sitemap_head"])
    rb = ev["robots_head"].lower() + get(f"{o}/robots.txt")["text"].lower()
    named = sorted({b for b in AI_BOTS if b in rb})
    ev["ai_bots_named"] = named
    ev["chk_robots_ai"] = len(named) >= 2

    # --- live searchable listings on their own address
    idx_words = ["idx", "mls", "listing", "search homes", "property search", "advanced search"]
    ev["chk_listings"] = sum(1 for w in idx_words if w in low) >= 3 and \
                         bool(re.search(r'(idx|listing|property|home)[-_]?(search|results)|/search|search\.html|idxboost|ihomefinder|showcaseidx|realgeeks|sierra|rover', low))

    # --- own domain, not a brokerage profile
    ev["chk_own_domain"] = agent["own_domain"]
    return ev

if __name__ == "__main__":
    agents = json.load(open(sys.argv[1]))
    out = {}
    for a in agents:
        print("checking", a["name"], a["primary_url"], flush=True)
        out[a["name"]] = check(a)
    json.dump(out, open(sys.argv[2], "w"), indent=1)
    print("wrote", sys.argv[2])
