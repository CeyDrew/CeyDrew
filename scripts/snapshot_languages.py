"""Write assets/languages.json: language totals across public AND private repos.

Run locally with a token that can see private repos (the Actions token cannot):
    GH_TOKEN=... python scripts/snapshot_languages.py
Only aggregate byte counts per language are stored; no repo names.
"""
import json
import os
import urllib.request

OUT = os.path.join(os.path.dirname(__file__), "..", "assets", "languages.json")
EXCLUDE_REPOS = {"SecureLauncher"}
# Platform scaffolding (Flutter iOS/Android shells, build files), not hand-written code
SKIP = {"Swift", "Kotlin", "Java", "Objective-C", "C++", "CMake", "C", "Ruby", "Batchfile", "Shell", "PowerShell", "Dockerfile"}
# Linguist sometimes classifies .php files as Hack
MERGE = {"Hack": "PHP"}

QUERY = """{ viewer { repositories(ownerAffiliations: OWNER, isFork: false, first: 100) {
  nodes { name languages(first: 20) { edges { size node { name color } } } } } } }"""

req = urllib.request.Request("https://api.github.com/graphql", data=json.dumps({"query": QUERY}).encode(),
                             headers={"Authorization": f"bearer {os.environ['GH_TOKEN']}", "Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=30) as r:
    repos = json.load(r)["data"]["viewer"]["repositories"]["nodes"]

colors, sizes = {}, {}
for repo in repos:
    if repo["name"] in EXCLUDE_REPOS:
        continue
    for e in repo["languages"]["edges"]:
        name = e["node"]["name"]
        colors.setdefault(name, e["node"]["color"] or "#8b949e")
        name = MERGE.get(name, name)
        if name not in SKIP:
            sizes[name] = sizes.get(name, 0) + e["size"]

data = {n: [s, colors[n]] for n, s in sorted(sizes.items(), key=lambda kv: -kv[1])}
with open(OUT, "w", encoding="utf-8", newline="\n") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
print(", ".join(f"{n} {s / sum(sizes.values()) * 100:.1f}%" for n, (s, _) in list(data.items())[:6]))
