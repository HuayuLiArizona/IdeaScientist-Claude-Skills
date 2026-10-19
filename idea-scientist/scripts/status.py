#!/usr/bin/env python3
"""Run budget check: how much has this run consumed, and should it keep going?

Usage:
    python status.py <run_dir> [--json]

Run it after EVERY role call and obey the verdict on the last line:

    CONTINUE  under every limit; carry on with the loop
    WRAP UP   a limit is reached: no new gap-finder or innovator calls. Commit the
              best candidate (forced commit if none survived), run the report
              writer once, validate, deliver.
    STOP      hard limit reached: no more reading or searching. Deliver now with
              what exists (see the "Next" line).

Limits by depth (from problem.md):

                         quick   standard   deep
    papers read (total)    20       45       80
    axes mapped             1        2        3
    candidates (C<n>)       2        4        6
    sanity checks (K<n>)    1        3        6   (reaching it only ends checks, not the run)
    wrap-up after (min)    30       75      150
    hard stop after (min)  45      120      240

Elapsed time is measured from .run_meta.json (written by init_run.py), else the
"Started:" line in plan.md, else the oldest file in the run directory.

It also lists each candidate's lever (references/thinking_traps.md §1) and, when the
next step is a fresh innovator call, the levers to pass as AVOID_LEVER.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _levers import run_levers  # noqa: E402

LIMITS = {
    "quick":    {"papers": 20, "axes": 1, "candidates": 2, "checks": 1, "wrap_min": 30,  "stop_min": 45},
    "standard": {"papers": 45, "axes": 2, "candidates": 4, "checks": 3, "wrap_min": 75,  "stop_min": 120},
    "deep":     {"papers": 80, "axes": 3, "candidates": 6, "checks": 6, "wrap_min": 150, "stop_min": 240},
}


def _checks(run: Path) -> tuple[list[str], list[str]]:
    """(all check ids, ids whose Result is still pending) from checks.md."""
    text = _read(run / "checks.md")
    ids, pending = [], []
    for kid, body in re.findall(r"^###\s+(K\d+)\b(.*?)(?=^###\s+K\d+\b|\Z)", text, re.M | re.S):
        ids.append(kid)
        m = re.search(r"\*\*Result:\*\*[ \t]*(.*)", body)
        if not m or not m.group(1).strip() or m.group(1).strip().lower().startswith("pending"):
            pending.append(kid)
    return ids, pending


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""


def _depth(run: Path) -> str:
    m = re.search(r"Depth:\s*(quick|standard|deep)", _read(run / "problem.md"), re.I)
    return m.group(1).lower() if m else "standard"


def _parse_ts(s: str) -> float | None:
    s = s.strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%d %H:%M:%S%z", "%Y-%m-%dT%H:%M:%S"):
        try:
            dt = datetime.strptime(s.replace("Z", "+0000"), fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.timestamp()
        except ValueError:
            continue
    return None


def _started(run: Path) -> tuple[float, str]:
    meta = run / ".run_meta.json"
    if meta.exists():
        try:
            ts = _parse_ts(json.loads(_read(meta)).get("started", ""))
            if ts:
                return ts, ".run_meta.json"
        except json.JSONDecodeError:
            pass
    m = re.search(r"Started:\s*(\S+)", _read(run / "plan.md"))
    if m and _parse_ts(m.group(1)):
        return _parse_ts(m.group(1)), "plan.md"
    files = [p for p in run.rglob("*") if p.is_file()]
    if files:
        return min(p.stat().st_mtime for p in files), "oldest file (approximate)"
    return time.time(), "now (empty run)"


def collect(run: Path) -> dict:
    depth = _depth(run)
    lim = LIMITS[depth]
    papers = len(list((run / "papers").glob("*.md"))) if (run / "papers").is_dir() else 0
    axes = len(re.findall(r"^##\s+Axis:", _read(run / "gaps.md"), re.M))
    cand_text = _read(run / "candidates.md")
    candidates = sorted(set(re.findall(r"^###\s+(C\d+)\b(?!\s+verdict)", cand_text, re.M)), key=lambda c: int(c[1:]))
    scores = _read(run / "scores.md")
    verdicts: dict[str, str] = {}
    for cid, body in re.findall(r"^###\s+(C\d+)\s+verdict\b(.*?)(?=^###\s+C\d+\s+verdict\b|\Z)", scores, re.M | re.S | re.I):
        m = re.search(r"\*\*Verdict:\*\*\s*`?(survive|revise|reject)", body, re.I)
        verdicts[cid] = m.group(1).lower() if m else "unparsed"
    survived = [c for c, v in verdicts.items() if v == "survive"]
    unreviewed = [c for c in candidates if c not in verdicts]
    checks, pending_checks = _checks(run)
    levers = run_levers(cand_text)
    report = (run / "report.json").exists()
    rendered = (run / "report.md").exists()
    started, source = _started(run)
    elapsed = (time.time() - started) / 60

    reasons_wrap, reasons_stop = [], []
    if elapsed >= lim["stop_min"]:
        reasons_stop.append(f"elapsed {elapsed:.0f} min ≥ hard stop {lim['stop_min']} min")
    elif elapsed >= lim["wrap_min"]:
        reasons_wrap.append(f"elapsed {elapsed:.0f} min ≥ wrap-up {lim['wrap_min']} min")
    if papers >= int(lim["papers"] * 1.5):
        reasons_stop.append(f"{papers} papers read ≥ 1.5× limit {lim['papers']}")
    elif papers >= lim["papers"]:
        reasons_wrap.append(f"{papers} papers read ≥ limit {lim['papers']}")
    if len(candidates) >= lim["candidates"]:
        reasons_wrap.append(f"{len(candidates)} candidates ≥ limit {lim['candidates']}")
    if axes > lim["axes"]:
        reasons_wrap.append(f"{axes} axes mapped > limit {lim['axes']}")

    if reasons_stop:
        verdict = "STOP"
    elif reasons_wrap:
        verdict = "WRAP UP"
    else:
        verdict = "CONTINUE"

    problem = _read(run / "problem.md")
    user_mode = bool(re.search(r"Idea source:\s*user", problem, re.I))
    novelty_only = bool(re.search(r"Deliverable:\s*novelty", problem, re.I))
    latest = candidates[-1] if candidates else None
    latest_verdict = verdicts.get(latest) if latest else None

    if user_mode and latest_verdict == "reject":
        nxt = (f"the user's idea ({latest}) was rejected (collision or fatal flaw). Deliver the verdict and the "
               "collision report from scores.md; don't pivot to a different idea. Offer a differentiated variant "
               "or problem mode instead.")
    elif user_mode and novelty_only and survived and not report:
        nxt = (f"{survived[-1]} survived the novelty survey. Deliver the novelty assessment (verdict, closest work, "
               "novelty argument) and offer to develop it into a proposal; no report writer unless asked.")
    elif user_mode and not candidates and verdict == "CONTINUE":
        nxt = "formalize the user's idea as C1: innovator with USER_IDEA: yes."
    elif user_mode and latest and latest_verdict is None and len(candidates) == 1 and verdict == "CONTINUE":
        nxt = f"novelty survey: reviewer on {latest} with MODE: novelty-survey."
    elif rendered and report:
        nxt = "report.md exists — validate once if not yet done, then deliver."
    elif report:
        nxt = "report.json exists — validate (at most 2 fix rounds), render_report.py, deliver."
    elif verdict == "STOP":
        if candidates:
            best = survived[-1] if survived else candidates[-1]
            if survived:
                why = "survived"
            elif best in verdicts:
                why = "FORCED COMMIT — it did not survive review; say so in the delivery"
            else:
                why = "FORCED COMMIT — never reviewed; say so in the delivery"
            nxt = (f"no more reading or searching. Run the report writer once on {best} using only existing digests "
                   f"({why}); if that cannot finish, deliver a summary of candidates.md and gaps.md instead.")
        else:
            nxt = "no candidate exists. Deliver the gap analysis (gaps.md) and say the run stopped before ideation."
    elif verdict == "WRAP UP":
        if survived:
            nxt = f"run the report writer on {survived[-1]}."
        elif unreviewed:
            nxt = f"review {unreviewed[-1]} once; then commit it (forced commit if it does not survive) and run the report writer."
        elif candidates:
            nxt = f"forced commit to the best reviewed candidate (latest is {candidates[-1]}) and run the report writer; flag it in the delivery."
        else:
            nxt = "run ONE innovator on the best gap, then the report writer (skip review if time is the limit, and say so)."
    else:
        if survived:
            nxt = f"{survived[-1]} survived — run the report writer."
        elif unreviewed:
            nxt = f"review {unreviewed[-1]}."
        elif not axes:
            nxt = "run the gap finder on the most central axis."
        else:
            nxt = "continue the loop (innovator on the chosen gap, or act on the last verdict)."

    notes = []
    used = []
    for info in levers.values():
        if info["lever"] and info["origin"] != "user" and info["lever"] not in used:
            used.append(info["lever"])
    fresh_levers = [i["lever"] for i in levers.values() if not i["rebuild"] and i["origin"] != "user"]
    if len(fresh_levers) >= 2 and len(set(fresh_levers)) == 1 and fresh_levers[0]:
        notes.append(f"every fresh candidate uses the '{fresh_levers[0]}' lever (thinking_traps.md, T3)")
    fresh_next = (verdict == "CONTINUE" and not user_mode and not survived and not unreviewed and not report
                  and latest_verdict == "reject")
    if used and fresh_next:
        notes.append("next innovator call is a fresh intuition — pass AVOID_LEVER: " + ", ".join(used))
    if verdict == "STOP":
        notes.append("no more sanity checks (STOP)")
    elif len(checks) >= lim["checks"]:
        notes.append(f"sanity-check budget used ({len(checks)}/{lim['checks']}) — no more checks this run")
    if pending_checks:
        notes.append(f"checks with no recorded result: {', '.join(pending_checks)} — record the outcome "
                     "(or 'timed out' / 'error'); don't re-run")

    return {
        "mode": "user-idea" if user_mode else "problem",
        "depth": depth, "limits": lim, "elapsed_min": round(elapsed, 1), "started_from": source,
        "papers": papers, "axes": axes, "candidates": candidates, "verdicts": verdicts,
        "checks": checks, "pending_checks": pending_checks,
        "levers": {c: i["lever"] for c, i in levers.items()}, "levers_used": used,
        "report_json": report, "report_md": rendered,
        "verdict": verdict, "reasons": reasons_stop + reasons_wrap, "notes": notes, "next": nxt,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_dir")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    run = Path(args.run_dir)
    if not run.is_dir():
        print(f"error: {run} is not a directory", file=sys.stderr)
        return 2
    s = collect(run)
    if args.json:
        print(json.dumps(s, ensure_ascii=False, indent=1))
        return 0
    lim = s["limits"]
    vs = ", ".join(f"{c}:{v}" for c, v in s["verdicts"].items()) or "none"
    lv = ", ".join(f"{c}:{v or '?'}" for c, v in s["levers"].items()) or "none"
    print(f"mode {s['mode']} · depth {s['depth']} · elapsed {s['elapsed_min']:.0f}/{lim['wrap_min']}/{lim['stop_min']} min "
          f"(wrap/stop; start from {s['started_from']})")
    print(f"papers {s['papers']}/{lim['papers']} · axes {s['axes']}/{lim['axes']} · "
          f"candidates {len(s['candidates'])}/{lim['candidates']} · checks {len(s['checks'])}/{lim['checks']} · "
          f"verdicts {vs} · report.json {'yes' if s['report_json'] else 'no'}")
    print(f"levers {lv}")
    if s["reasons"]:
        print("why: " + "; ".join(s["reasons"]))
    for n in s["notes"]:
        print("note: " + n)
    print(f"Next: {s['next']}")
    print(s["verdict"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
