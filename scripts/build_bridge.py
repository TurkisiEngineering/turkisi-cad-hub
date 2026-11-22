#!/usr/bin/env python3
"""Hub README'sindeki köprü bölümlerini üretir.

- MEMBERS: community/members.yml içindeki owners → ekip kartları
- BRIDGE : her owner için `topic` taşıyan açık, arşivlenmemiş, fork olmayan repolar

Kullanım:
  python scripts/build_bridge.py --readme README.md --members community/members.yml
  python scripts/build_bridge.py ... --dry-run              # README'yi yazmaz, çıktıyı basar
  python scripts/build_bridge.py ... --fixture repos.json   # ağ yok; test için {owner: [repo,...]}

GITHUB_TOKEN ortam değişkeni varsa kullanılır (Actions'ta otomatik gelir).
Yalnızca stdlib + PyYAML.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

import yaml

API = "https://api.github.com"


def gh_get(url: str) -> dict:
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "turkisi-cad-hub-bridge",
    })
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            # search API rate limit → bekle ve tekrar dene
            if e.code in (403, 429) and attempt < 2:
                time.sleep(20 * (attempt + 1))
                continue
            raise
    raise RuntimeError("unreachable")


def search_repos(owner: dict, topic: str) -> list[dict]:
    qual = "org" if owner.get("type") == "org" else "user"
    q = f"topic:{topic} {qual}:{owner['login']} archived:false fork:false is:public"
    url = f"{API}/search/repositories?" + urllib.parse.urlencode(
        {"q": q, "sort": "updated", "order": "desc", "per_page": 100})
    try:
        data = gh_get(url)
    except urllib.error.HTTPError as e:
        # 422: GitHub bu kullanıcıyı aramada gösteremiyor (ör. hiç public reposu yok ya da hesap yeni).
        # Tek bir üye yüzünden tüm liste çökmesin: o üyeyi atla, uyarı yaz.
        if e.code == 422:
            print(f"! {owner['login']}: GitHub araması bu hesabı listeleyemedi (422), atlandı", file=sys.stderr)
            return []
        raise
    return data.get("items", [])


def esc(text: str | None) -> str:
    text = (text or "").replace("\n", " ").strip()
    return text.replace("|", "\\|")


def render_members(owners: list[dict]) -> str:
    cells = []
    for o in owners:
        login = o["login"]
        if "_GH_USERNAME" in login:  # doldurulmamış yer tutucu
            continue
        cells.append(
            f'<td align="center" width="160">'
            f'<a href="https://github.com/{login}">'
            f'<img src="https://github.com/{login}.png?size=96" width="64" alt="{login}"><br>'
            f'<b>{o.get("display", login)}</b></a><br>'
            f'<sub>{o.get("role", "")}</sub></td>'
        )
    if not cells:
        return "_Henüz üye yok._"
    return "<table><tr>" + "".join(cells) + "</tr></table>"


def render_bridge(owners: list[dict], repos_by_owner: dict[str, list[dict]],
                  exclude: set[str]) -> str:
    out: list[str] = []
    total = 0
    for o in owners:
        login = o["login"]
        if "_GH_USERNAME" in login:
            continue
        repos = [r for r in repos_by_owner.get(login, [])
                 if r["full_name"].lower() not in exclude]
        if not repos:
            continue
        repos.sort(key=lambda r: (-r.get("stargazers_count", 0), r["name"].lower()))
        out.append(f'### [{o.get("display", login)}](https://github.com/{login})\n')
        out.append("| Proje | Açıklama | ⭐ | Güncelleme |")
        out.append("|---|---|---:|---|")
        for r in repos:
            pushed = (r.get("pushed_at") or "")[:10]
            out.append(
                f'| [{r["name"]}]({r["html_url"]}) | {esc(r.get("description"))} '
                f'| {r.get("stargazers_count", 0)} | {pushed} |'
            )
            total += 1
        out.append("")
    # Tarih damgası bilinçli olarak yok: liste değişmedikçe README değişmesin (günlük boş commit olmasın).
    if total == 0:
        out.append("_Henüz listelenecek proje yok._\n")
    out.append(f"<sub>{total} proje · tüm liste: "
               f"[topics/{TOPIC}](https://github.com/topics/{TOPIC})</sub>")
    return "\n".join(out)


def replace_block(text: str, name: str, content: str) -> str:
    pat = re.compile(rf"(<!-- {name}:START -->)(.*?)(<!-- {name}:END -->)", re.S)
    if not pat.search(text):
        sys.exit(f"README içinde <!-- {name}:START/END --> işaretleri bulunamadı.")
    return pat.sub(lambda m: f"{m.group(1)}\n{content}\n{m.group(3)}", text, count=1)


TOPIC = "turkisi-community"


def main() -> None:
    global TOPIC
    for s in (sys.stdout, sys.stderr):
        s.reconfigure(encoding="utf-8")   # yerel Windows denemeleri için (Actions zaten UTF-8)
    ap = argparse.ArgumentParser()
    ap.add_argument("--readme", default="README.md")
    ap.add_argument("--members", default="community/members.yml")
    ap.add_argument("--fixture", help="Ağ yerine JSON dosyası: {owner_login: [repo, ...]}")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cfg = yaml.safe_load(open(args.members, encoding="utf-8"))
    TOPIC = cfg.get("topic", TOPIC)
    owners = cfg.get("owners", [])
    exclude = {x.lower() for x in cfg.get("exclude_repos", [])}

    if args.fixture:
        repos_by_owner = json.load(open(args.fixture, encoding="utf-8"))
    else:
        repos_by_owner = {}
        for o in owners:
            if "_GH_USERNAME" in o["login"]:
                print(f"! yer tutucu atlandı: {o['login']}", file=sys.stderr)
                continue
            repos_by_owner[o["login"]] = search_repos(o, TOPIC)
            time.sleep(2)  # search API: 30 istek/dk (token ile)

    readme = open(args.readme, encoding="utf-8").read()
    new = replace_block(readme, "MEMBERS", render_members(owners))
    new = replace_block(new, "BRIDGE", render_bridge(owners, repos_by_owner, exclude))

    if args.dry_run:
        print(new)
        return
    if new != readme:
        open(args.readme, "w", encoding="utf-8").write(new)
        print("README güncellendi.")
    else:
        print("Değişiklik yok.")


if __name__ == "__main__":
    main()
