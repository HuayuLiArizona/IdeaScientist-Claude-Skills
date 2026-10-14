#!/usr/bin/env python3
"""Literature search from the shell, for environments that allow it.

Subcommands:
    check                         which backends are reachable from this shell
    search --backend B Q [Q ...]  search one backend with one or more queries
    fulltext ID                   print a paper's full text (vault backend only)
    path ID                       print the digest path for an ID

Backends:
    arxiv     arXiv export API
    s2        Semantic Scholar Graph API (set S2_API_KEY for higher rate limits)
    openalex  OpenAlex works API
    vault     local Svalbard Idea Vault: IDEASCIENTIST_KEYWORD_INDEX (FTS5 index)
              and IDEA_VAULT_DB (paper database)

Output of `search` is JSON: [{id, title, date, url, abstract}], deduplicated across
queries. Hosted sandboxes often block these hosts; when `check` reports a backend
as unreachable, search with WebSearch instead (see references/retrieval.md).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _ids import canonical, safe_id  # noqa: E402

UA = "idea-scientist-skill/1.0 (research ideation; polite use)"
TIMEOUT = 20


def _get(url: str, headers: dict | None = None) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read()


def _trim(text: str | None, n: int = 600) -> str:
    t = re.sub(r"\s+", " ", text or "").strip()
    return t if len(t) <= n else t[: n - 1] + "…"


def _terms(q: str) -> list[str]:
    return [w for w in re.findall(r"[A-Za-z0-9\-]+", q) if len(w) >= 3][:12]


# ------------------------------------------------------------------ backends

def search_arxiv(query: str, k: int) -> list[dict]:
    ns = {"a": "http://www.w3.org/2005/Atom"}
    terms = _terms(query)
    if not terms:
        return []
    out: list[dict] = []
    for joiner in ("+AND+", "+OR+"):
        sq = joiner.join("all:" + urllib.parse.quote(t) for t in terms)
        url = f"https://export.arxiv.org/api/query?search_query={sq}&max_results={k}&sortBy=relevance"
        root = ET.fromstring(_get(url))
        out = []
        for e in root.findall("a:entry", ns):
            raw = (e.findtext("a:id", default="", namespaces=ns) or "").rsplit("/abs/", 1)[-1]
            pid = canonical(f"arXiv:{raw}")
            if not pid:
                continue
            out.append({
                "id": pid,
                "title": _trim(e.findtext("a:title", default="", namespaces=ns), 300),
                "date": (e.findtext("a:published", default="", namespaces=ns) or "")[:10],
                "url": f"https://arxiv.org/abs/{pid.split(':', 1)[1]}",
                "abstract": _trim(e.findtext("a:summary", default="", namespaces=ns)),
            })
        if out or len(terms) == 1:
            break
        time.sleep(3)  # arXiv asks for ~3 s between API calls
    return out


def search_s2(query: str, k: int) -> list[dict]:
    fields = "title,year,publicationDate,externalIds,abstract,url"
    url = ("https://api.semanticscholar.org/graph/v1/paper/search?"
           + urllib.parse.urlencode({"query": query, "limit": min(k, 100), "fields": fields}))
    headers = {"x-api-key": os.environ["S2_API_KEY"]} if os.environ.get("S2_API_KEY") else None
    data = json.loads(_get(url, headers))
    out = []
    for p in data.get("data", []) or []:
        ext = p.get("externalIds") or {}
        if ext.get("ArXiv"):
            pid = canonical(f"arXiv:{ext['ArXiv']}")
        elif ext.get("DOI"):
            pid = canonical(f"doi:{ext['DOI']}")
        elif ext.get("ACL"):
            pid = canonical(f"acl:{ext['ACL']}")
        elif ext.get("PubMed"):
            pid = canonical(f"pmid:{ext['PubMed']}")
        else:
            pid = canonical(f"s2:{p.get('paperId')}")
        if not pid:
            continue
        out.append({
            "id": pid,
            "title": _trim(p.get("title"), 300),
            "date": p.get("publicationDate") or (str(p["year"]) if p.get("year") else ""),
            "url": p.get("url") or "",
            "abstract": _trim(p.get("abstract")),
        })
    return out


def _openalex_abstract(inv: dict | None) -> str:
    if not inv:
        return ""
    pos = sorted((i, w) for w, idxs in inv.items() for i in idxs)
    return " ".join(w for _, w in pos)


def search_openalex(query: str, k: int) -> list[dict]:
    url = ("https://api.openalex.org/works?"
           + urllib.parse.urlencode({
               "search": query,
               "per-page": min(k, 50),
               "select": "id,title,publication_date,doi,abstract_inverted_index",
           }))
    data = json.loads(_get(url))
    out = []
    for w in data.get("results", []) or []:
        doi = (w.get("doi") or "").replace("https://doi.org/", "")
        pid = canonical(f"doi:{doi}") if doi else None
        if not pid:
            continue
        out.append({
            "id": pid,
            "title": _trim(w.get("title"), 300),
            "date": w.get("publication_date") or "",
            "url": w.get("doi") or w.get("id") or "",
            "abstract": _trim(_openalex_abstract(w.get("abstract_inverted_index"))),
        })
    return out


def _vault_paths() -> tuple[Path | None, Path | None]:
    idx = os.environ.get("IDEASCIENTIST_KEYWORD_INDEX")
    db = os.environ.get("IDEA_VAULT_DB")
    return (Path(idx) if idx else None, Path(db) if db else None)


def search_vault(query: str, k: int, before: str | None) -> list[dict]:
    idx, db = _vault_paths()
    if not idx or not idx.exists():
        raise RuntimeError("IDEASCIENTIST_KEYWORD_INDEX is not set or does not exist")
    expr = " OR ".join(f'"{w}"' for w in _terms(query))
    if not expr:
        return []
    con = sqlite3.connect(f"file:{idx}?mode=ro&immutable=1", uri=True)
    try:
        sql = ("SELECT f.rowid, m.title, m.collect_date, bm25(papers_fts) AS s "
               "FROM papers_fts f JOIN papers_meta m ON m.paper_id = f.rowid "
               "WHERE papers_fts MATCH ? ")
        params: list = [expr]
        if before:
            sql += "AND m.collect_date != '' AND m.collect_date < ? "
            params.append(before)
        sql += "ORDER BY s LIMIT ?"
        params.append(k)
        rows = con.execute(sql, params).fetchall()
    finally:
        con.close()
    abstracts: dict[int, str] = {}
    if db and db.exists() and rows:
        dcon = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        try:
            q = "SELECT id, abstract FROM papers WHERE id IN (%s)" % ",".join("?" * len(rows))
            abstracts = {int(i): a for i, a in dcon.execute(q, [int(r[0]) for r in rows])}
        except sqlite3.Error:
            pass
        finally:
            dcon.close()
    return [{
        "id": f"vault:{int(pid)}",
        "title": _trim(title, 300),
        "date": date or "",
        "url": "",
        "abstract": _trim(abstracts.get(int(pid))),
    } for pid, title, date, _ in rows]


# ------------------------------------------------------------------ commands

def cmd_search(args) -> int:
    merged: dict[str, dict] = {}
    errors = []
    for i, q in enumerate(args.queries):
        try:
            if args.backend == "arxiv":
                if i:
                    time.sleep(3)
                hits = search_arxiv(q, args.k)
            elif args.backend == "s2":
                hits = search_s2(q, args.k)
            elif args.backend == "openalex":
                hits = search_openalex(q, args.k)
            else:
                hits = search_vault(q, args.k, args.before)
        except Exception as exc:  # noqa: BLE001 - report and continue with other queries
            errors.append(f"{q!r}: {type(exc).__name__}: {exc}")
            continue
        for h in hits:
            if args.before and h.get("date") and h["date"][: len(args.before)] >= args.before:
                continue
            h.setdefault("queries", [])
            if h["id"] in merged:
                merged[h["id"]]["queries"].append(q)
            else:
                h["queries"] = [q]
                merged[h["id"]] = h
    print(json.dumps(list(merged.values()), ensure_ascii=False, indent=1))
    if errors:
        print("errors:\n  " + "\n  ".join(errors), file=sys.stderr)
        if not merged:
            print("no results — if the backend is unreachable, use WebSearch (references/retrieval.md)", file=sys.stderr)
            return 1
    return 0


def cmd_check(_args) -> int:
    report = {}
    probes = {
        "arxiv": lambda: search_arxiv("cascade ranking", 1),
        "s2": lambda: search_s2("cascade ranking", 1),
        "openalex": lambda: search_openalex("cascade ranking", 1),
    }
    for name, fn in probes.items():
        try:
            fn()
            report[name] = "ok"
        except Exception as exc:  # noqa: BLE001
            report[name] = f"unreachable ({type(exc).__name__}: {str(exc)[:120]})"
    idx, db = _vault_paths()
    if idx and idx.exists():
        report["vault"] = "ok" + ("" if db and db.exists() else " (search only; IDEA_VAULT_DB missing, no fulltext)")
    else:
        report["vault"] = "not configured"
    report["recommendation"] = (
        "api" if any(v == "ok" for k, v in report.items() if k in probes)
        else ("vault" if report["vault"].startswith("ok") else "web")
    )
    print(json.dumps(report, indent=1))
    return 0


def cmd_fulltext(args) -> int:
    pid = canonical(args.id)
    if not pid or not pid.startswith("vault:"):
        print("fulltext is only available for vault: IDs; read other papers with WebFetch "
              "(https://arxiv.org/pdf/<id>), see references/retrieval.md", file=sys.stderr)
        return 2
    _, db = _vault_paths()
    if not db or not db.exists():
        print("IDEA_VAULT_DB is not set or does not exist", file=sys.stderr)
        return 2
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        row = con.execute(
            "SELECT p.title, p.date, t.full_text FROM papers p "
            "LEFT JOIN paper_full_text t ON t.paper_id = p.id WHERE p.id = ?",
            (int(pid.split(":", 1)[1]),),
        ).fetchone()
    finally:
        con.close()
    if not row:
        print(f"{pid} not found", file=sys.stderr)
        return 1
    title, date, text = row
    print(f"# {title}\n- ID: {pid}\n- Date: {date}\n")
    print((text or "(no full text stored)")[: args.max_chars])
    return 0


def cmd_path(args) -> int:
    pid = canonical(args.id)
    if not pid:
        print(f"not a recognized ID: {args.id!r} (expected prefix arXiv:, doi:, acl:, openreview:, pmid:, vault:, s2:)",
              file=sys.stderr)
        return 2
    print(f"papers/{safe_id(pid)}.md")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    s = sub.add_parser("search")
    s.add_argument("--backend", choices=["arxiv", "s2", "openalex", "vault"], default="arxiv")
    s.add_argument("--k", type=int, default=20)
    s.add_argument("--before", help="drop results dated on/after this YYYY-MM-DD (literature cutoff)")
    s.add_argument("queries", nargs="+")
    f = sub.add_parser("fulltext")
    f.add_argument("id")
    f.add_argument("--max-chars", type=int, default=120_000)
    p = sub.add_parser("path")
    p.add_argument("id")
    args = ap.parse_args()
    return {"check": cmd_check, "search": cmd_search, "fulltext": cmd_fulltext, "path": cmd_path}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
