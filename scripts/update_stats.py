"""Build profile cards from GitHub's public API; no third-party image service.

Local use: python scripts/update_stats.py --username Kieranmcm07
GITHUB_TOKEN is optional locally and supplied by the scheduled workflow.
Stars and forks count public, owned, non-fork repositories only.
"""

import argparse
from datetime import datetime, timezone
from html import escape
import json
import os
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
from xml.etree import ElementTree


def fetch_json(path):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "github-profile-snapshot",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token := os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"
    request = Request(f"https://api.github.com{path}", headers=headers)
    for attempt in range(3):
        try:
            with urlopen(request, timeout=30) as response:
                return json.load(response)
        except HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise
        except (URLError, TimeoutError):
            if attempt == 2:
                raise
        time.sleep(2 ** attempt)


def collect_stats(username, fetch=fetch_json):
    user_path = f"/users/{quote(username, safe='')}"
    profile = fetch(user_path)
    repositories = []
    page = 1
    while True:
        batch = fetch(f"{user_path}/repos?type=owner&per_page=100&page={page}")
        repositories.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    originals = [repo for repo in repositories if not repo["fork"] and not repo["private"]]
    return {
        "username": profile["login"],
        "repositories": profile["public_repos"],
        "stars": sum(repo["stargazers_count"] for repo in originals),
        "forks": sum(repo["forks_count"] for repo in originals),
        "followers": profile["followers"],
        "updated": datetime.now(timezone.utc).strftime("%d %b %Y"),
    }


def render_card(stats, theme):
    bg, border, fg, muted, accent = {
        "dark": ("#0d1117", "#30363d", "#f0f6fc", "#a8b3bf", "#7dd3fc"),
        "light": ("#ffffff", "#d0d7de", "#1f2328", "#59636e", "#0969da"),
    }[theme]
    metrics = [("repositories", "Public repos"), ("stars", "Stars earned"),
               ("forks", "Project forks"), ("followers", "Followers")]
    content = []
    for index, (key, label) in enumerate(metrics):
        x = 38 + index * 184
        content.append(
            f'<text x="{x}" y="104" fill="{fg}" font-size="34" font-weight="700">'
            f'{stats[key]:,}</text>'
            f'<text x="{x}" y="132" fill="{muted}" font-size="15">{label}</text>'
        )
    username = escape(stats["username"])
    updated = escape(stats["updated"])
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="760" height="196" viewBox="0 0 760 196" role="img" aria-labelledby="title desc">
  <title id="title">{username}'s GitHub snapshot</title>
  <desc id="desc">{stats['repositories']} public repositories, {stats['stars']} stars earned, {stats['forks']} project forks and {stats['followers']} followers. Stars and forks exclude forked repositories. Updated {updated}.</desc>
  <rect x="1" y="1" width="758" height="194" rx="14" fill="{bg}" stroke="{border}" />
  <g font-family="Segoe UI, Arial, sans-serif">
    <text x="38" y="39" fill="{accent}" font-size="17" font-weight="600">A little of what I've shared on GitHub</text>
    {''.join(content)}
    <text x="38" y="175" fill="{muted}" font-size="12">Stars and forks from original public repos · Updated {updated}</text>
  </g>
</svg>
'''


def update_cards(username, output_dir, fetch=fetch_json):
    # Fetch and validate everything before replacing either last-known-good card.
    stats = collect_stats(username, fetch)
    cards = {theme: render_card(stats, theme) for theme in ("dark", "light")}
    for card in cards.values():
        ElementTree.fromstring(card)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for theme, card in cards.items():
        destination = output_dir / f"github-stats-{theme}.svg"
        temporary = destination.with_suffix(".svg.tmp")
        temporary.write_text(card, encoding="utf-8")
        temporary.replace(destination)
    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--username", default="Kieranmcm07")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parents[1] / "assets")
    args = parser.parse_args()
    print(json.dumps(update_cards(args.username, args.output_dir), indent=2))
