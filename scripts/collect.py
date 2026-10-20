"""Coleta a atividade real do GitHub (incluindo repos privados) e grava scripts/data.json.

Usa GH_STATS_TOKEN (Action) ou o token do `gh` local. Só agregados saem daqui:
nenhum código, mensagem de commit ou nome de repo privado fora da allowlist do build.
"""
import json, os, subprocess, urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

LOGIN = "Art-rh"
BRT = timezone(timedelta(hours=-3))
HERE = os.path.dirname(os.path.abspath(__file__))

def token():
    return os.environ.get("GH_STATS_TOKEN") or subprocess.run(
        ["gh", "auth", "token"], capture_output=True, text=True).stdout.strip()

TOKEN = token()

def gql(query, **variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        body = json.load(r)
    if body.get("errors"):
        raise RuntimeError(body["errors"])
    return body["data"]

PROFILE = gql("""query($login:String!){ user(login:$login){ id createdAt followers{totalCount}
  repositories(ownerAffiliations:OWNER, first:100, orderBy:{field:PUSHED_AT,direction:DESC}){ totalCount
    nodes{ name isPrivate isFork pushedAt stargazerCount primaryLanguage{name color}
      languages(first:12, orderBy:{field:SIZE,direction:DESC}){ edges{ size node{name color} } } } }
  contributionsCollection{ totalCommitContributions totalPullRequestContributions
    totalPullRequestReviewContributions contributionCalendar{ totalContributions } } } }""", login=LOGIN)["user"]

HISTORY = """query($owner:String!,$name:String!,$uid:ID!,$after:String){ repository(owner:$owner,name:$name){
  defaultBranchRef{ target{ ... on Commit{ all: history(author:{id:$uid}){ totalCount }
    history(author:{id:$uid}, first:100, after:$after){ pageInfo{hasNextPage endCursor}
      nodes{ committedDate additions deletions } } } } } } }"""

def main():
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=371)
    repos = [r for r in PROFILE["repositories"]["nodes"] if not r["isFork"]]

    total_commits = 0
    per_day = Counter()            # yyyy-mm-dd (BRT) -> commits
    hours, weekdays = Counter(), Counter()
    per_repo_30d, per_repo_year = Counter(), Counter()
    repo_last = {}
    additions = deletions = 0
    langs = defaultdict(lambda: [0, None])

    for repo in repos:
        for e in repo["languages"]["edges"]:
            langs[e["node"]["name"]][0] += e["size"]
            langs[e["node"]["name"]][1] = e["node"]["color"]
        after, first_page = None, True
        while True:
            data = gql(HISTORY, owner=LOGIN, name=repo["name"], uid=PROFILE["id"], after=after)
            ref = data["repository"]["defaultBranchRef"]
            if not ref:
                break
            target = ref["target"]
            if first_page:
                total_commits += target["all"]["totalCount"]
                first_page = False
            page = target["history"]
            stop = False
            for c in page["nodes"]:
                t = datetime.fromisoformat(c["committedDate"].replace("Z", "+00:00"))
                if t < since:
                    stop = True
                    break
                local = t.astimezone(BRT)
                per_day[local.date().isoformat()] += 1
                hours[local.hour] += 1
                weekdays[local.weekday()] += 1
                per_repo_year[repo["name"]] += 1
                if now - t <= timedelta(days=30):
                    per_repo_30d[repo["name"]] += 1
                repo_last[repo["name"]] = max(repo_last.get(repo["name"], ""), c["committedDate"])
                additions += c["additions"]; deletions += c["deletions"]
            if stop or not page["pageInfo"]["hasNextPage"]:
                break
            after = page["pageInfo"]["endCursor"]

    # sequências (dias consecutivos com commit, em BRT)
    today = now.astimezone(BRT).date()
    days = [(today - timedelta(days=i)).isoformat() for i in range(365)]
    current = 0
    for i, d in enumerate(days):
        if per_day[d]:
            current += 1
        elif i > 0:
            break
    longest = run = 0
    for d in reversed(days):
        run = run + 1 if per_day[d] else 0
        longest = max(longest, run)

    repo_meta = {r["name"]: {"private": r["isPrivate"], "lang": (r["primaryLanguage"] or {}).get("name"),
                             "color": (r["primaryLanguage"] or {}).get("color"), "stars": r["stargazerCount"]}
                 for r in repos}
    lang_total = sum(v[0] for v in langs.values()) or 1
    out = {
        "generated_at": now.isoformat(),
        "account_created": PROFILE["createdAt"],
        "repos_total": PROFILE["repositories"]["totalCount"],
        "repos_private": sum(r["isPrivate"] for r in repos),
        "commits_all_time": total_commits,
        "commits_year": sum(per_day[d] for d in days),
        "commits_30d": sum(per_day[d] for d in days[:30]),
        "additions_year": additions, "deletions_year": deletions,
        "prs_year": PROFILE["contributionsCollection"]["totalPullRequestContributions"],
        "reviews_year": PROFILE["contributionsCollection"]["totalPullRequestReviewContributions"],
        "active_days_year": sum(1 for d in days if per_day[d]),
        "streak_current": current, "streak_longest": longest,
        "per_day": {d: per_day[d] for d in days},
        "hours": [hours[h] for h in range(24)],
        "weekdays": [weekdays[w] for w in range(7)],
        "languages": [{"name": k, "pct": v[0] * 100 / lang_total, "color": v[1]}
                      for k, v in sorted(langs.items(), key=lambda kv: -kv[1][0])],
        "repos_30d": [{"name": n, "commits": c, "last": repo_last[n], **repo_meta[n]}
                      for n, c in per_repo_30d.most_common(6)],
        "last_commit": max(repo_last.values()) if repo_last else None,
        "lang_commits": dict(sum((Counter({repo_meta[n]["lang"]: c}) for n, c in per_repo_year.items()
                                  if repo_meta[n]["lang"]), Counter()).most_common()),
        "lang_colors": {m["lang"]: m["color"] for m in repo_meta.values() if m["lang"]},
    }
    with open(os.path.join(HERE, "data.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print({k: v for k, v in out.items() if not isinstance(v, (dict, list))})

if __name__ == "__main__":
    main()
