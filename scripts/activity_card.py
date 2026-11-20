"""Render assets/activity.svg: last-12-months GitHub activity card.

Usage: GH_TOKEN=... python scripts/activity_card.py [username]
Standard library only, so it runs on a bare GitHub Actions runner.
"""
import datetime as dt
import json
import os
import sys
import urllib.request
from html import escape

USER = sys.argv[1] if len(sys.argv) > 1 else "CeyDrew"
OUT = os.path.join(os.path.dirname(__file__), "..", "assets", "activity.svg")
# Flutter/React Native platform scaffolding, not hand-written code
SKIP_LANGS = {"Swift", "Kotlin", "Objective-C", "C++", "CMake", "C", "Ruby", "Batchfile", "Shell", "PowerShell", "Dockerfile"}
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      totalPullRequestContributions
      restrictedContributionsCount
      contributionCalendar { totalContributions weeks { contributionDays { contributionCount date } } }
    }
    repositories(ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC, first: 100) {
      totalCount
      nodes { languages(first: 10, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name color } } } }
    }
  }
}
"""


def fetch():
    now = dt.datetime.now(dt.timezone.utc)
    body = json.dumps({"query": QUERY, "variables": {
        "login": USER, "from": (now - dt.timedelta(days=365)).isoformat(), "to": now.isoformat()}}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", data=body, headers={
        "Authorization": f"bearer {os.environ['GH_TOKEN']}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data:
        sys.exit(f"GraphQL error: {data['errors'][0].get('message')}")
    return data["data"]["user"]


def render(u):
    cc = u["contributionsCollection"]
    days = [d for w in cc["contributionCalendar"]["weeks"] for d in w["contributionDays"]]
    weeks = [sum(d["contributionCount"] for d in w["contributionDays"]) for w in cc["contributionCalendar"]["weeks"]][-52:]
    stats = [
        (cc["contributionCalendar"]["totalContributions"], "CONTRIBUTIONS"),
        (cc["totalCommitContributions"] + cc["restrictedContributionsCount"], "COMMITS"),
        (u["repositories"]["totalCount"], "PUBLIC REPOS"),
        (sum(1 for d in days if d["contributionCount"] > 0), "ACTIVE DAYS"),
    ]
    langs = {}
    for repo in u["repositories"]["nodes"]:
        for e in repo["languages"]["edges"]:
            n = e["node"]["name"]
            if n in SKIP_LANGS:
                continue
            size, color = langs.get(n, (0, e["node"]["color"] or "#8b949e"))
            langs[n] = (size + e["size"], color)
    top = sorted(langs.items(), key=lambda kv: -kv[1][0])[:6]
    total = sum(s for _, (s, _) in top) or 1

    W, H = 840, 300
    parts = []
    # stats
    for k, (n, label) in enumerate(stats):
        x = 36 + k * 132
        parts.append(f'<g class="up" style="animation-delay:{0.1 + k * 0.12:.2f}s"><text x="{x}" y="88" class="num">{n:,}</text>'
                     f'<text x="{x}" y="110" class="lab">{label}</text></g>')
    # weekly bars
    bx, by, bw, bh = 590, 46, 214, 64
    peak = max(weeks) or 1
    step = bw / len(weeks)
    for k, v in enumerate(weeks):
        h = max(1.5, v / peak * bh)
        op = 0.35 + 0.65 * (v / peak)
        parts.append(f'<rect x="{bx + k * step:.1f}" y="{by + bh - h:.1f}" width="{max(1.2, step - 1.2):.1f}" height="{h:.1f}" rx="1" '
                     f'fill="url(#bar)" opacity="{op:.2f}" class="grow" style="animation-delay:{0.3 + k * 0.012:.2f}s"/>')
    parts.append(f'<line x1="{bx}" y1="{by + bh + .5}" x2="{bx + bw}" y2="{by + bh + .5}" stroke="#30363d"/>')
    parts.append(f'<text x="{bx + bw}" y="{by + bh + 22}" text-anchor="end" class="lab">CONTRIBUTIONS PER WEEK</text>')
    # language bar
    parts.append('<text x="36" y="168" class="lab">LANGUAGES</text>')
    x, lw = 36.0, W - 72
    parts.append(f'<clipPath id="lc"><rect x="36" y="182" width="{lw}" height="10" rx="5"/></clipPath><g clip-path="url(#lc)">')
    for name, (size, color) in top:
        w = size / total * lw
        parts.append(f'<rect x="{x:.1f}" y="182" width="{w + .5:.1f}" height="10" fill="{color}"/>')
        x += w
    parts.append('</g>')
    lx = 36
    for name, (size, color) in top:
        label = f"{name} {size / total * 100:.0f}%"
        parts.append(f'<circle cx="{lx + 5}" cy="219" r="5" fill="{color}"/><text x="{lx + 16}" y="224" class="leg">{escape(label)}</text>')
        lx += 22 + len(label) * 7.4

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#161b22"/><stop offset=".55" stop-color="#0d1117"/><stop offset="1" stop-color="#111827"/></linearGradient>
  <linearGradient id="sheen" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".06"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
  <linearGradient id="bar" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#1f6feb"/><stop offset="1" stop-color="#3fb950"/></linearGradient>
  <filter id="blur" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="45"/></filter>
  <clipPath id="card"><rect width="{W}" height="{H}" rx="18"/></clipPath>
</defs>
<style>
  .num{{font:700 30px {SANS};fill:#f0f6fc}}
  .lab{{font:600 11px {SANS};fill:#8b949e;letter-spacing:1.2px}}
  .leg{{font:500 13px {SANS};fill:#c9d1d9}}
  .cap{{font:600 11px {SANS};fill:#58a6ff;letter-spacing:1.5px}}
</style>
<g clip-path="url(#card)">
  <rect width="{W}" height="{H}" fill="url(#bg)"/>
  <circle cx="120" cy="-20" r="140" fill="#1f6feb" opacity=".18" filter="url(#blur)"/>
  <circle cx="760" cy="320" r="150" fill="#3fb950" opacity=".12" filter="url(#blur)"/>
  <rect x="-300" y="0" width="300" height="{H}" fill="url(#sheen)" transform="skewX(-20)">
    <animate attributeName="x" values="-300;1200" dur="6s" repeatCount="indefinite"/>
  </rect>
  <rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="18" fill="none" stroke="#30363d"/>
  <text x="36" y="40" class="cap">LAST 12 MONTHS</text>
  {"".join(parts)}
</g>
</svg>'''


if __name__ == "__main__":
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(render(fetch()))
    print("wrote", os.path.normpath(OUT))
