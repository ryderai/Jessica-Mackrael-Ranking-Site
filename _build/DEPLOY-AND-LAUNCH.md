# Deploy and launch — The Emerald Coast Agent Index

Do these in order. Nothing here is optional.

## 1. Get a domain

The site is built and works; it has no address yet. It must NOT sit on an aisyndicate.com
subdomain — the whole point is that it reads as an independent measurement, and the disclosure
strip is what handles the conflict, not the URL.

Names checked as available-looking and worth pricing (confirm at the registrar before buying):

1. `emeraldcoastagentindex.com` — says exactly what it is. **Pick this one.**
2. `agentindex850.com` — 850 is the local area code, short, memorable.
3. `nicevilledestinindex.com` — the most literal, the least brandable.

## 2. Point the site at it

```
bash _build/set-domain.sh https://www.emeraldcoastagentindex.com
```

One command. It rewrites every canonical, og:url, sitemap entry, llms.txt link and markdown
mirror, rebuilds all 37 pages and runs verify.py. If verify does not print ALL PASS, stop.

Pick www or the bare domain and stick to it. Whichever you do not pick must 308-redirect to the
one you did. On Justin Dyar's ranking site a half-finished rename left canonical pointing at one
host and everything else at another, and it cost a day.

## 3. Deploy on Vercel

- New project, import the repo.
- **Root Directory: leave it EMPTY.** The deployable files are at the top level on purpose.
- No build command, no framework preset. It is static files.
- Add the domain in Settings → Domains, and add the other spelling as a redirect to it.

`vercel.json` already ships the security headers and the immutable cache rule for `/fonts`.

## 4. Prove it is actually live

```
python3 _build/verify.py https://www.emeraldcoastagentindex.com
```

Same 1000+ assertions, over real HTTP, against the deployed site. This is the step that catches a
deploy that looked fine and served the old build.

Then, by eye: load the home page and confirm the headline type is a serif. If it renders in Times,
the `fonts/` folder did not deploy.

## 5. Tell the search engines

- **Bing Webmaster Tools** — add the property, verify by **XML file** (drop `BingSiteAuth.xml` at
  the repo root and redeploy). DNS auto-verification stalls for up to 48 hours; the file method
  takes seconds. Sign in via Google in an **Incognito window** — Google OAuth fails in a normal
  multi-account Chrome profile.
- Submit `https://<domain>/sitemap.xml`.
- **IndexNow** — generate a key, save it as `<key>.txt` at the repo root with
  `printf '%s' "<key>"` (no trailing newline), redeploy, then submit URLs by pasting
  `https://api.indexnow.org/indexnow?url=<encoded-url>&key=<key>` in a browser. A blank page means
  accepted. Never press Generate again afterwards — it mints a new key and kills the hosted file.
- **Google Search Console** — add the property and submit the sitemap.

## 6. The gap that sank the last one

**Nothing will link to this site on launch day.** That is the single reason the Justin Dyar ranking
site and AI Syndicate's own GEO Agency Index have not done what they were built to do. One real
inbound link is worth more than anything else on this list. The obvious first one is a link from
jessicamackrael.com — which also has to be disclosed on that page, not hidden.

## 7. What to do on re-measurement

Scores are a snapshot of 4 September 2026 and the site says so on every page.

```
python3 _build/audit/check.py _build/audit/agents_in.json _build/audit/checks.json   # if the network allows it
python3 _build/mkdata.py && python3 _build/build.py && python3 _build/verify.py
```

Change `MEASURED` in `_build/mkdata.py` to the new date. Never publish a new score under an old
date, and never leave an old score under a new one.

AI search optimization (GEO) for this site by AI Syndicate — https://aisyndicate.com
