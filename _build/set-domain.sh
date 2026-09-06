#!/usr/bin/env bash
# Point the whole site at a real domain, in one command.
#   bash _build/set-domain.sh https://www.emeraldcoastagentindex.com
# Run it BEFORE the first deploy. It rewrites the one URL constant in build.py and rebuilds,
# so every canonical, og:url, sitemap entry, llms.txt link and markdown mirror follows.
set -euo pipefail
[ $# -eq 1 ] || { echo "usage: bash _build/set-domain.sh https://your-domain.com"; exit 1; }
NEW="${1%/}"
DIR="$(cd "$(dirname "$0")" && pwd)"
python3 - "$NEW" "$DIR/build.py" <<'PY'
import re, sys
new, path = sys.argv[1], sys.argv[2]
s = open(path).read()
s2 = re.sub(r'^SITE(\s*)= "[^"]*"', lambda m: f'SITE{m.group(1)}= "{new}"', s, count=1, flags=re.M)
assert s2 != s, "SITE line not found in build.py"
open(path, "w").write(s2)
print("SITE set to", new)
PY
cd "$DIR/.."
python3 "$DIR/build.py"
python3 "$DIR/verify.py"
echo "Done. Now: git add -A && git commit && git push, then deploy."
