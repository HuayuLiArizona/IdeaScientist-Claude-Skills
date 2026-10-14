"""Paper-ID helpers shared by the idea-scientist scripts.

IDs are prefixed strings such as ``arXiv:1706.02093`` or ``doi:10.1145/3477495.3532050``.
They are cited inline as ``[arXiv:1706.02093]`` and each has a digest at
``papers/<safe_id>.md``.
"""

from __future__ import annotations

import re
from pathlib import Path

PREFIXES = {
    "arxiv": "arXiv",
    "doi": "doi",
    "acl": "acl",
    "openreview": "openreview",
    "pmid": "pmid",
    "vault": "vault",
    "s2": "s2",
    "ref": "ref",
}

_ID_TOKEN = re.compile(r"^(arxiv|doi|acl|openreview|pmid|vault|s2|ref):(\S+)$", re.I)
_BRACKET = re.compile(r"\[([^\[\]\n]{3,400})\]")
_ARXIV_NEW = re.compile(r"^(\d{4})\.(\d{4,5})(v\d+)?$")
_ARXIV_OLD = re.compile(r"^([a-z\-]+(?:\.[A-Z]{2})?/\d{7})(v\d+)?$")
_ARXIV_URL = re.compile(r"arxiv\.org/(?:abs|pdf|html)/([a-z\-]+(?:\.[A-Z]{2})?/\d{7}|\d{4}\.\d{4,5})(?:v\d+)?", re.I)


def canonical(raw: str) -> str | None:
    """Normalize an ID token; return None if it is not a recognized ID."""
    tok = raw.strip().strip(".,;:)(")
    m = _ID_TOKEN.match(tok)
    if not m:
        return None
    prefix = PREFIXES[m.group(1).lower()]
    value = m.group(2)
    if prefix == "arXiv":
        n = _ARXIV_NEW.match(value)
        o = _ARXIV_OLD.match(value)
        if n:
            value = f"{n.group(1)}.{n.group(2)}"
        elif o:
            value = o.group(1)
    if prefix == "doi":
        value = value.lower()
        a = re.match(r"^10\.48550/arxiv\.(\d{4}\.\d{4,5})$", value)
        if a:
            return f"arXiv:{a.group(1)}"
    return f"{prefix}:{value}"


def is_id(raw: str) -> bool:
    return canonical(raw) is not None


def safe_id(pid: str) -> str:
    c = canonical(pid) or pid
    return re.sub(r"[^A-Za-z0-9._-]", "_", c)


def digest_path(run_dir: Path | str, pid: str) -> Path:
    """Where the digest for ``pid`` lives. If a file exists whose name matches
    case-insensitively (e.g. a DOI digest written with upper-case letters), that
    file is returned, so read-before-cite does not fail on letter case."""
    papers = Path(run_dir) / "papers"
    want = f"{safe_id(pid)}.md"
    exact = papers / want
    if exact.exists() or not papers.is_dir():
        return exact
    low = want.lower()
    for f in papers.iterdir():
        if f.name.lower() == low:
            return f
    return exact


def extract_ids(text: str) -> list[str]:
    """All canonical IDs cited in bracket form, in order of first appearance."""
    seen: dict[str, None] = {}
    for m in _BRACKET.finditer(text or ""):
        for tok in re.split(r"[,;]\s*|\s+", m.group(1)):
            c = canonical(tok)
            if c and c not in seen:
                seen[c] = None
    return list(seen)


def arxiv_id_from_url(url: str) -> str | None:
    m = _ARXIV_URL.search(url or "")
    return f"arXiv:{m.group(1)}" if m else None


def arxiv_yymm(pid: str) -> str | None:
    """'YYYY-MM' encoded in a new-style arXiv ID, else None."""
    c = canonical(pid) or ""
    m = re.match(r"^arXiv:(\d{2})(\d{2})\.\d{4,5}$", c)
    if not m:
        return None
    return f"20{m.group(1)}-{m.group(2)}"


def url_for(pid: str) -> str | None:
    c = canonical(pid)
    if not c:
        return None
    prefix, value = c.split(":", 1)
    return {
        "arXiv": f"https://arxiv.org/abs/{value}",
        "doi": f"https://doi.org/{value}",
        "acl": f"https://aclanthology.org/{value}",
        "openreview": f"https://openreview.net/forum?id={value}",
        "pmid": f"https://pubmed.ncbi.nlm.nih.gov/{value}/",
        "s2": f"https://www.semanticscholar.org/paper/{value}",
    }.get(prefix)


DATE_RE = re.compile(r"\b(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?\b")


def clean_date(text: str | None) -> str | None:
    """The first YYYY[-MM[-DD]] in ``text``, or None."""
    m = DATE_RE.search(text or "")
    if not m:
        return None
    return "-".join(p for p in m.groups() if p)


def read_digest_meta(path: Path) -> dict:
    """Title, date, version, access, source and note parsed from a digest header.

    ``date`` is the raw Date line; ``date_clean`` is just its YYYY[-MM[-DD]];
    ``version_date`` is the date found on the Version line, if any.
    """
    meta = {"title": None, "date": None, "version": None, "access": None, "source": None, "note": None}
    if not path.exists():
        return {**meta, "date_clean": None, "version_date": None}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[:25]:
        s = line.strip()
        if s.startswith("# ") and meta["title"] is None:
            meta["title"] = s[2:].strip()
        low = s.lower()
        for key in ("date", "version", "access", "source", "note"):
            if low.startswith(f"- {key}:") and meta[key] is None:
                meta[key] = s.split(":", 1)[1].strip()
    meta["date_clean"] = clean_date(meta["date"])
    meta["version_date"] = clean_date(meta["version"])
    return meta
