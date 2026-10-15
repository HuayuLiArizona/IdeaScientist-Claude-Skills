#!/usr/bin/env python3
"""Create an idea-scientist run directory with empty, correctly-shaped run files.

Usage:
    python init_run.py <run_dir> [--depth quick|standard|deep] [--cutoff YYYY-MM-DD]
                       [--language en] [--backend web|api|vault]

Existing files are never overwritten, so it is safe to re-run.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

PROBLEM = """# Problem

## Problem definition
- Formal setting: <fill in>
- Inputs: <fill in>
- Outputs: <fill in>
- Constraints: <what may change and what is fixed>

## Challenge
- What fails and why: <fill in — what fails, never how to fix it>
- Why it matters: <fill in>
- Concrete failing example: <fill in>

## Challenge axes
- <axis 1, in the field's own terminology>

## Settings
- Depth: {depth}
- Literature cutoff: {cutoff}
- Output language: {language}
- Retrieval backend: {backend}
- Idea source: {source}
- Deliverable: {deliverable}
{user_idea}
## User notes
- <preferences, things already tried, directions to avoid>
"""

USER_IDEA_SECTION = """
## User idea
<the user's idea, verbatim>
"""

PLAN = """# Plan

Goal: ONE focused, well-grounded methodological intuition, developed into a full proposal.

## Axes
- [ ] <axis 1>

## Mode
- Execution: <subagents | inline>
- Deviations: none

## Active direction
- Gap: (none yet)
- Candidate: (none yet)
- Status: forming

## History
"""

STUBS = {
    "gaps.md": "# Gaps\n\n",
    "candidates.md": "# Candidates\n\n",
    "scores.md": "# Reviews\n\n",
    "checks.md": "# Sanity checks\n\nToy numerical checks run during ideation (references/sanity_checks.md). Not results.\n\n",
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_dir")
    ap.add_argument("--depth", choices=["quick", "standard", "deep"], default="standard")
    ap.add_argument("--cutoff", default="none", help="YYYY-MM-DD, or 'none'")
    ap.add_argument("--language", default="en", help="output language code, e.g. en, zh")
    ap.add_argument("--backend", choices=["web", "api", "vault"], default="web")
    ap.add_argument("--user-idea", action="store_true",
                    help="Mode B: the user brought their own idea (novelty check / development)")
    ap.add_argument("--deliverable", choices=["proposal", "novelty-check"], default=None,
                    help="default: 'proposal', or 'novelty-check' with --user-idea")
    args = ap.parse_args()

    if args.cutoff != "none" and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.cutoff):
        print(f"error: --cutoff must be YYYY-MM-DD or 'none', got {args.cutoff!r}", file=sys.stderr)
        return 2

    run = Path(args.run_dir)
    (run / "papers").mkdir(parents=True, exist_ok=True)
    (run / "checks").mkdir(exist_ok=True)

    created, kept = [], []
    files = {
        "problem.md": PROBLEM.format(
            depth=args.depth, cutoff=args.cutoff, language=args.language, backend=args.backend,
            source="user" if args.user_idea else "problem",
            deliverable=args.deliverable or ("novelty-check" if args.user_idea else "proposal"),
            user_idea=USER_IDEA_SECTION if args.user_idea else "",
        ),
        "plan.md": PLAN,
        **STUBS,
    }
    started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S%z")
    files["plan.md"] = files["plan.md"].replace("## Axes", f"Started: {started}\n\n## Axes", 1)
    for name, content in files.items():
        p = run / name
        if p.exists():
            kept.append(name)
        else:
            p.write_text(content, encoding="utf-8")
            created.append(name)
    meta = run / ".run_meta.json"
    if not meta.exists():
        meta.write_text(json.dumps({"started": started, "depth": args.depth}) + "\n", encoding="utf-8")

    print(f"run directory: {run.resolve()}")
    if created:
        print("created: " + ", ".join(created) + ", papers/")
    if kept:
        print("kept existing: " + ", ".join(kept))
    if args.user_idea:
        print("next: fill in problem.md (problem, challenge, the user's idea verbatim), then run the innovator "
              "with USER_IDEA: yes to formalize it as C1, then the reviewer with MODE: novelty-survey.")
    else:
        print("next: fill in problem.md (problem definition, challenge, axes), then start the gap finder.")
    print("after every role call: python <skill_dir>/scripts/status.py <run_dir>  (CONTINUE / WRAP UP / STOP)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
