"""Lever helpers shared by validate.py and status.py.

A candidate's **Lever:** line names the lever carrying its core bet, then the
alternatives it was chosen over (references/thinking_traps.md §1):

    - **Lever:** inference — alternatives considered: objective: …; representation: …
"""

from __future__ import annotations

import re

LEVERS = ("objective", "representation", "architecture", "data", "inference", "interface", "formulation", "systems")
_LEVER_WORD = re.compile(r"\b(" + "|".join(LEVERS) + r")\b", re.I)
_FIELD = re.compile(r"\*\*Lever:\*\*[ \t]*(.*?)(?=\n\s*-\s*\*\*[A-Z][^*]*:\*\*|\Z)", re.S)
_ALT_SPLIT = re.compile(r"alternatives?\s+considered\s*:?", re.I)


def candidate_blocks(text: str) -> dict[str, str]:
    """Map C<n> -> body for every '### C<n>' block in candidates.md (verdict headers skipped)."""
    out: dict[str, str] = {}
    pieces = re.split(r"^###\s+(C\d+)\b", text, flags=re.M)
    for i in range(1, len(pieces) - 1, 2):
        if re.match(r"\s*verdict", pieces[i + 1], re.I):
            continue
        out[pieces[i]] = out.get(pieces[i], "") + pieces[i + 1]
    return out


def parse_lever(body: str) -> dict:
    """Parse a candidate's Lever line.

    Returns {"present": bool, "lever": str|None (a known lever, lower-case),
             "raw_head": str (text before 'alternatives considered'), "alternatives": [known levers]}.
    """
    m = _FIELD.search(body)
    if not m:
        return {"present": False, "lever": None, "raw_head": "", "alternatives": []}
    raw = m.group(1).strip()
    parts = _ALT_SPLIT.split(raw, maxsplit=1)
    head = parts[0]
    alt = parts[1] if len(parts) > 1 else ""
    lm = _LEVER_WORD.search(head)
    lever = lm.group(1).lower() if lm else None
    alts = []
    for a in _LEVER_WORD.findall(alt):
        a = a.lower()
        if a != lever and a not in alts:
            alts.append(a)
    return {"present": True, "lever": lever, "raw_head": head.strip(" -—–:`*"), "alternatives": alts}


def is_rebuild(body: str) -> bool:
    m = re.search(r"\*\*If improving prior candidate:\*\*[ \t]*(.*)", body)
    if not m:
        return False
    v = m.group(1).strip().lower()
    return bool(v) and not v.startswith(("n/a", "none", "—", "-"))


def origin(body: str) -> str:
    m = re.search(r"\*\*Origin:\*\*[ \t]*(\w+)", body)
    return m.group(1).lower() if m else "system"


def run_levers(candidates_text: str) -> dict[str, dict]:
    """C<n> -> {"lever", "rebuild", "origin"} for every candidate, in file order."""
    out = {}
    for cid, body in candidate_blocks(candidates_text).items():
        out[cid] = {"lever": parse_lever(body)["lever"], "rebuild": is_rebuild(body), "origin": origin(body)}
    return out
