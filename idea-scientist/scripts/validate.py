#!/usr/bin/env python3
"""Validity gates for an idea-scientist run.

Usage:
    python validate.py <run_dir> [--stage all|papers|gaps|candidates|scores|checks|report]
                       [--cutoff YYYY-MM-DD] [--json]

Checks, mirroring the IdeaScientist reward gates:
  papers      digest structure; Date format; under a cutoff, both the paper's date and the
              date of the version actually read must precede it
  gaps        schema per axis; at most 2 gaps; all five gap fields; read-before-cite
  candidates  schema per C<n>; source cited by id; read-before-cite; lever named and
              compared with alternatives; fresh candidates not all on one lever
  scores      verdict format; target candidate exists; idea-shape line; read-before-cite
  checks      sanity checks: all fields, kill criterion written, no pending results,
              every [check K<n>] reference resolves
  report      valid JSON; every schema field present and filled; no placeholders;
              [check K<n>] only in falsifiable_predictions / limitations;
              cited ids resolve to digests; heuristics for measured results;
              prediction kinds (an upside prediction; safety + cost at most half);
              lever named; thesis that reads like an analysis paper
FAIL = must be fixed before delivery (exit code 1). WARN = look at it, use judgment.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from _ids import arxiv_yymm, canonical, digest_path, extract_ids, read_digest_meta  # noqa: E402
from _levers import LEVERS, is_rebuild, parse_lever  # noqa: E402

SCHEMA_PATH = HERE.parent / "assets" / "report_schema.json"

GAP_FIELDS = [
    "**Near-miss methods and coverage:**",
    "**Methodological deficiency:**",
    "**Why it matters:**",
    "**Evidence route:**",
]
CANDIDATE_FIELDS = [
    "**Intuition:**",
    "**Gap it attacks:**",
    "**Lever:**",
    "**Core bet:**",
    "**Source inspiration:**",
    "**How it maps to this problem:**",
    "**Why it could work",
    "**Novelty vs. closest in-domain work:**",
    "**Main risk:**",
]
VERDICT_RE = re.compile(
    r"\*\*Verdict:\*\*\s*`?(survive|revise\(\s*focus\s*=\s*(novelty|coherence|feasibility|clarity|mapping|grounding|ambition|lever)\s*\)"
    r"|reject\(\s*reason\s*=.+?\))`?",
    re.I,
)
SOFT_EMPTY = {"key_hyperparameters", "pseudocode", "model", "notes"}
PLACEHOLDER_RE = re.compile(r"\bTODO\b|\bTBD\b|<fill in>|XXXX\.XXXXX|lorem ipsum", re.I)
RESULT_RE = re.compile(
    r"\b(achiev(?:es|ed)|improv(?:es|ed)|outperform(?:s|ed)|reduc(?:es|ed)|gain(?:s|ed)?)\b[^.;]{0,50}?"
    r"\b\d+(?:\.\d+)?\s*(?:%|x\b|×|points?\b|pp\b)",
    re.I,
)
PAST_RESULT_RE = re.compile(r"\b(we observed|our experiments show|results show|we found that|empirically, our)\b", re.I)
CHECK_REF_RE = re.compile(r"\[\s*check\s+(K\d+)\s*\]", re.I)
PRED_KINDS = ("upside", "mechanism", "safety", "cost")
ANALYSIS_THESIS_RE = re.compile(
    r"^\s*(?:(?:we|this (?:paper|work|proposal))\s+)?(?:systematically\s+)?"
    r"(?:analy[sz]e|investigate|probe|characteri[sz]e|benchmark|examine|diagnose|measure|study whether)(?:s|d|ed)?(?=\s)"
    r"|^\s*an?\s+(?:systematic\s+)?(?:analysis|study|benchmark|investigation)\s+of\b"
    r"|^\s*(?:本文|我们|本提案)?\s*(?:系统(?:性)?地?)?\s*(?:分析|探究|探讨|考察|刻画|诊断|测量)",
    re.I,
)


class Report:
    def __init__(self) -> None:
        self.items: list[tuple[str, str, str]] = []

    def fail(self, stage: str, msg: str) -> None:
        self.items.append(("FAIL", stage, msg))

    def warn(self, stage: str, msg: str) -> None:
        self.items.append(("WARN", stage, msg))

    @property
    def n_fail(self) -> int:
        return sum(1 for lvl, _, _ in self.items if lvl == "FAIL")


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""


def _cutoff_from_problem(run: Path) -> str | None:
    m = re.search(r"Literature cutoff:\s*(\d{4}-\d{2}-\d{2})", _read(run / "problem.md"))
    return m.group(1) if m else None


def check_citations(run: Path, stage: str, text: str, rep: Report, where: str = "") -> list[str]:
    ids = extract_ids(text)
    for pid in ids:
        if not digest_path(run, pid).exists():
            rep.fail(stage, f"{where}cites [{pid}] but {digest_path(run, pid).relative_to(run)} does not exist "
                            "(read before cite: read it and write the digest, or drop the citation)")
        elif (read_digest_meta(digest_path(run, pid))["access"] or "").lower().startswith("abstract"):
            rep.warn(stage, f"{where}cites [{pid}], whose digest is abstract-only — fine for context, "
                            "not for mechanism-level claims")
    return ids


# ------------------------------------------------------------------ papers

def check_papers(run: Path, rep: Report, cutoff: str | None) -> None:
    pdir = run / "papers"
    files = sorted(pdir.glob("*.md")) if pdir.exists() else []
    if not files:
        rep.warn("papers", "no digests in papers/ yet")
        return
    for f in files:
        text = _read(f)
        name = f.name
        if not re.search(r"^# \S", text, re.M):
            rep.fail("papers", f"{name}: missing '# <title>' header")
        if "## What this paper does" not in text:
            rep.warn("papers", f"{name}: missing '## What this paper does'")
        if "## Goal-by-goal answers" not in text:
            rep.warn("papers", f"{name}: missing '## Goal-by-goal answers'")
        meta = read_digest_meta(f)
        date = meta["date_clean"]
        id_line = re.search(r"^- ID:\s*(\S+)", text, re.M)
        pid = canonical(id_line.group(1)) if id_line else None
        if not id_line:
            rep.warn("papers", f"{name}: missing '- ID:' line")
        if not date:
            rep.warn("papers", f"{name}: missing or unparseable '- Date:' line")
        elif meta["date"].strip() != date:
            rep.warn("papers", f"{name}: Date line should hold only YYYY[-MM[-DD]] (got {meta['date']!r}); "
                               "put remarks on a '- Note:' line")
        if cutoff:
            _cutoff_check(rep, name, "dated", date, cutoff)
            if pid and arxiv_yymm(pid) and arxiv_yymm(pid) > cutoff[:7]:
                rep.fail("papers", f"{name}: arXiv ID {pid} was posted after the cutoff {cutoff}")
            if pid and pid.startswith("arXiv:"):
                if not meta["version_date"]:
                    rep.fail("papers", f"{name}: cutoff run but no '- Version: vN (YYYY-MM-DD)' line — "
                                       "arxiv.org/pdf/<id> serves the latest version, which may post-date the cutoff; "
                                       "check the abs page's submission history and read a pre-cutoff version")
                else:
                    _cutoff_check(rep, name, "read version dated", meta["version_date"], cutoff)


def _cutoff_check(rep: Report, name: str, what: str, date: str | None, cutoff: str) -> None:
    """FAIL if ``date`` is on/after ``cutoff``; WARN if its precision makes that ambiguous."""
    if not date:
        return
    n = len(date)
    if n >= 10:
        if date[:10] >= cutoff:
            rep.fail("papers", f"{name}: {what} {date}, on/after the literature cutoff {cutoff}")
        return
    head = cutoff[:n]
    if date > head:
        rep.fail("papers", f"{name}: {what} {date}, after the literature cutoff {cutoff}")
    elif date == head:
        if cutoff[n:].strip("-") in ("01", "01-01", ""):
            rep.fail("papers", f"{name}: {what} {date}, which is not before the literature cutoff {cutoff}")
        else:
            rep.warn("papers", f"{name}: {what} {date} — too coarse to tell whether it precedes the cutoff {cutoff}; "
                               "record the full date")


# ------------------------------------------------------------------ gaps

def check_gaps(run: Path, rep: Report, strict: bool) -> None:
    text = _read(run / "gaps.md")
    parts = re.split(r"^##\s+Axis:\s*", text, flags=re.M)[1:]
    if not parts:
        (rep.fail if strict else rep.warn)("gaps", "gaps.md has no '## Axis:' sections")
        return
    names = []
    for part in parts:
        axis = part.splitlines()[0].strip()
        names.append(axis.lower())
        tag = f"axis '{axis[:60]}': "
        if not axis:
            rep.fail("gaps", "an '## Axis:' header has no axis name")
        if "### What has been done" not in part:
            rep.fail("gaps", tag + "missing '### What has been done'")
        m = re.search(r"### Open gaps on this axis(.*)", part, re.S)
        if not m:
            rep.fail("gaps", tag + "missing '### Open gaps on this axis'")
            continue
        open_gaps = m.group(1)
        blocks = re.split(r"^\s*-\s*\*\*Gap:\*\*", open_gaps, flags=re.M)[1:]
        if len(blocks) > 2:
            rep.fail("gaps", tag + f"{len(blocks)} gaps — at most 2 per axis")
        if not blocks:
            rep.warn("gaps", tag + "zero gaps (fine if honest — make sure the search trail is recorded)")
        for i, b in enumerate(blocks, 1):
            for field in GAP_FIELDS:
                if field not in b:
                    rep.fail("gaps", tag + f"gap {i} is missing {field}")
            nm = re.search(r"\*\*Near-miss methods and coverage:\*\*(.*?)(?=\n\s*-\s*\*\*|\Z)", b, re.S)
            if nm and len(extract_ids(nm.group(1))) < 2:
                rep.warn("gaps", tag + f"gap {i} names fewer than 2 near-miss papers — "
                                       "acceptable only if the search shows a single real near miss")
        check_citations(run, "gaps", part, rep, tag)
    dupes = {n for n in names if names.count(n) > 1}
    if dupes:
        rep.warn("gaps", f"duplicate axis sections: {sorted(dupes)}")


# ------------------------------------------------------------------ candidates

def _candidate_sections(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    pieces = re.split(r"^###\s+(C\d+)\b", text, flags=re.M)
    for i in range(1, len(pieces) - 1, 2):
        cid = pieces[i]
        if re.match(r"\s*verdict", pieces[i + 1], re.I):
            continue
        out.setdefault(cid, "")
        out[cid] += pieces[i + 1]
    return out


def check_candidates(run: Path, rep: Report, strict: bool) -> set[str]:
    text = _read(run / "candidates.md")
    heads = re.findall(r"^###\s+(C\d+)\b", text, flags=re.M)
    secs = _candidate_sections(text)
    if not secs:
        (rep.fail if strict else rep.warn)("candidates", "candidates.md has no '### C<n>' sections")
        return set()
    dupes = {h for h in heads if heads.count(h) > 1}
    if dupes:
        rep.fail("candidates", f"duplicate candidate ids: {sorted(dupes)} — every innovator call writes a new C<n>")
    for cid, body in secs.items():
        tag = f"{cid}: "
        for field in CANDIDATE_FIELDS:
            if field not in body:
                rep.fail("candidates", tag + f"missing {field}")
        origin = re.search(r"\*\*Origin:\*\*[ \t]*(\w+)", body)
        user_idea = bool(origin and origin.group(1).lower() == "user")
        if not origin:
            rep.warn("candidates", tag + "missing **Origin:** (system | user)")
        src = re.search(r"\*\*Source inspiration:\*\*(.*?)(?=\n\s*-\s*\*\*|\Z)", body, re.S)
        if src and not extract_ids(src.group(1)):
            if user_idea:
                if "own construction" not in src.group(1).lower():
                    rep.warn("candidates", tag + "user idea: Source inspiration cites no paper — write "
                                             "\"user's own construction\" if it draws on none")
            else:
                rep.fail("candidates", tag + "Source inspiration cites no paper id")
        nov = re.search(r"\*\*Novelty vs\. closest in-domain work:\*\*(.*?)(?=\n\s*-\s*\*\*|\Z)", body, re.S)
        if nov and not extract_ids(nov.group(1)) and not (user_idea and "to be assessed" in nov.group(1).lower()):
            rep.warn("candidates", tag + "novelty line names no closest in-domain paper id")
        lv = parse_lever(body)
        if lv["present"]:
            if not lv["lever"]:
                rep.warn("candidates", tag + f"Lever {lv['raw_head'][:40]!r} is not one of {', '.join(LEVERS)} — "
                                         "fine if none fits, but check it isn't a relabelled objective change")
            elif not user_idea and len(lv["alternatives"]) < 2:
                rep.warn("candidates", tag + "Lever line compares against fewer than 2 other levers — list the "
                                         "alternatives considered and why each lost (thinking_traps.md, T3)")
        check_citations(run, "candidates", body, rep, tag)
    fresh = {cid: parse_lever(b)["lever"] for cid, b in secs.items()
             if not is_rebuild(b) and not re.search(r"\*\*Origin:\*\*[ \t]*user", b, re.I)}
    fresh_levers = {lv for lv in fresh.values() if lv}
    if len(fresh) >= 2 and len(fresh_levers) == 1:
        rep.warn("candidates", f"every fresh candidate ({', '.join(fresh)}) uses the '{fresh_levers.pop()}' lever — "
                               "pass AVOID_LEVER to the next fresh innovator call (thinking_traps.md, T3)")
    return set(secs)


# ------------------------------------------------------------------ scores

def check_scores(run: Path, rep: Report, candidates: set[str], strict: bool) -> dict[str, str]:
    text = _read(run / "scores.md")
    pieces = re.split(r"^###\s+(C\d+)\s+verdict\b", text, flags=re.M | re.I)
    verdicts: dict[str, str] = {}
    if len(pieces) < 3:
        (rep.fail if strict else rep.warn)("scores", "scores.md has no '### C<n> verdict' sections")
        return verdicts
    for i in range(1, len(pieces) - 1, 2):
        cid, body = pieces[i], pieces[i + 1]
        tag = f"{cid} verdict: "
        if candidates and cid not in candidates:
            rep.fail("scores", tag + f"reviews {cid}, which does not exist in candidates.md")
        m = VERDICT_RE.search(body)
        if not m:
            rep.fail("scores", tag + "Verdict must be survive | revise(focus=<novelty|coherence|feasibility|"
                                     "clarity|mapping|grounding|ambition|lever>) | reject(reason=<...>)")
        else:
            verdicts[cid] = m.group(1).split("(")[0].lower()
        if "**Evidence:**" not in body:
            rep.fail("scores", tag + "missing **Evidence:**")
        if "**Strongest objection" not in body:
            rep.fail("scores", tag + "missing **Strongest objection:**")
        if "**Search trail:**" not in body:
            rep.warn("scores", tag + "missing **Search trail:** — list the novelty queries run "
                                     "(or why none could run), so the review can be checked")
        if "**Closest work:**" not in body:
            rep.warn("scores", tag + "missing **Closest work:** — compare the closest papers on problem / method / contribution")
        if "**Idea shape:**" not in body:
            rep.warn("scores", tag + "missing **Idea shape:** — lever, core/support/guard counts, dominating "
                                     "alternative lever, upside on the standard metric (reviewer.md step 7)")
        verdict_line = m.group(0) if m else ""
        collision = bool(re.search(r"reject\(\s*reason\s*=\s*collision", verdict_line, re.I))
        if verdicts.get(cid) in ("survive", "revise") and not _field(body, "Novelty argument"):
            rep.warn("scores", tag + "missing **Novelty argument:** — one paragraph on what is added over the "
                                     "closest work and why it matters (the report writer reuses it)")
        if collision:
            report_text = _field(body, "Collision report")
            if not report_text:
                rep.fail("scores", tag + "reject(collision) needs a **Collision report:** — which papers, where problem, "
                                         "method and contribution coincide, and why the differences can't carry a novelty claim")
            else:
                ids = extract_ids(report_text)
                if not ids:
                    rep.fail("scores", tag + "Collision report names no paper id")
                for pid in ids:
                    meta = read_digest_meta(digest_path(run, pid))
                    if (meta["access"] or "").lower().startswith("abstract"):
                        rep.fail("scores", tag + f"collision claimed against [{pid}], but its digest is abstract-only — "
                                                 "read the full text before concluding a collision")
        check_citations(run, "scores", body, rep, tag)
    return verdicts


def _field(body: str, name: str) -> str:
    """Text of a '- **Name:** ...' field (to the next top-level field), stripped; '' if absent or empty."""
    m = re.search(rf"\*\*{re.escape(name)}:\*\*(.*?)(?=\n\s*-\s*\*\*[A-Z][^*]*:\*\*|\Z)", body, re.S)
    return m.group(1).strip() if m else ""


# ------------------------------------------------------------------ report

def _walk_schema(schema, value, path: str, rep: Report) -> None:
    key = path.rsplit(".", 1)[-1].split("[")[0]
    if isinstance(schema, dict):
        if not isinstance(value, dict):
            rep.fail("report", f"{path}: expected an object")
            return
        free_form = all(k.startswith("<") for k in schema)
        if free_form:
            if not value:
                (rep.warn if key in SOFT_EMPTY else rep.fail)("report", f"{path}: empty")
            return
        for k, sub in schema.items():
            if k not in value:
                rep.fail("report", f"{path}.{k}: missing")
            else:
                _walk_schema(sub, value[k], f"{path}.{k}", rep)
    elif isinstance(schema, list):
        if not isinstance(value, list):
            rep.fail("report", f"{path}: expected a list")
            return
        if not value:
            (rep.warn if key in SOFT_EMPTY else rep.fail)("report", f"{path}: empty list")
            return
        if schema and isinstance(schema[0], dict):
            for i, item in enumerate(value):
                _walk_schema(schema[0], item, f"{path}[{i}]", rep)
    elif isinstance(schema, bool):
        if not isinstance(value, bool):
            rep.warn("report", f"{path}: expected true/false")
    else:
        if value is None or (isinstance(value, str) and not value.strip()):
            (rep.warn if key in SOFT_EMPTY else rep.fail)("report", f"{path}: empty")


def _strings(obj, path: str = "$"):
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from _strings(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _strings(v, f"{path}[{i}]")


def check_report(run: Path, rep: Report, verdicts: dict[str, str], strict: bool) -> None:
    p = run / "report.json"
    if not p.exists():
        (rep.fail if strict else rep.warn)("report", "report.json does not exist yet")
        return
    raw = _read(p).strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        hint = " (remove the ``` code fence)" if raw.startswith("```") else ""
        rep.fail("report", f"report.json is not valid JSON: {exc}{hint}")
        return
    if not isinstance(data, dict):
        rep.fail("report", "report.json must be a single JSON object")
        return
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    _walk_schema(schema, data, "$", rep)
    extra = set(data) - set(schema) - {"references"}
    if extra:
        rep.warn("report", f"unexpected top-level fields: {sorted(extra)}")

    all_text = []
    for path, s in _strings(data):
        all_text.append(s)
        if PLACEHOLDER_RE.search(s):
            rep.fail("report", f"{path}: placeholder text left in ({PLACEHOLDER_RE.search(s).group(0)!r})")
        in_pred = ".falsifiable_predictions" in path or ".key_hyperparameters" in path
        if not in_pred and RESULT_RE.search(s):
            rep.warn("report", f"{path}: reads like a measured result ({RESULT_RE.search(s).group(0)!r}) — "
                               "the experiments have not been run; phrase as a prediction or remove")
        if PAST_RESULT_RE.search(s):
            rep.warn("report", f"{path}: past-tense result language ({PAST_RESULT_RE.search(s).group(0)!r})")
        if CHECK_REF_RE.search(s):
            if not (path.startswith("$.falsifiable_predictions") or path.startswith("$.limitations")):
                rep.fail("report", f"{path}: refers to sanity check {CHECK_REF_RE.search(s).group(1)} — toy checks may "
                                   "only motivate falsifiable_predictions or limitations, never serve as results or evidence")

    thesis = data.get("one_sentence_thesis") or ""
    if isinstance(thesis, str) and thesis:
        ascii_ratio = sum(c.isascii() for c in thesis) / len(thesis)
        if ascii_ratio > 0.8 and len(thesis.split()) > 30:
            rep.warn("report", f"one_sentence_thesis has {len(thesis.split())} words (aim for under 30)")
        elif ascii_ratio <= 0.8 and len(thesis) > 90:
            rep.warn("report", f"one_sentence_thesis has {len(thesis)} characters — keep it to one short sentence")
    if isinstance(thesis, str) and ANALYSIS_THESIS_RE.search(thesis):
        rep.warn("report", "one_sentence_thesis reads like an analysis paper (\"we analyze / investigate …\") — "
                           "the contribution must be a method; lead with what it builds (thinking_traps.md, T1)")
    preds = data.get("falsifiable_predictions")
    if isinstance(preds, list) and preds:
        kinds = []
        for i, p_ in enumerate(preds):
            k = (p_.get("kind") if isinstance(p_, dict) else None) or ""
            k = k.strip().lower() if isinstance(k, str) else ""
            if k and k not in PRED_KINDS:
                rep.warn("report", f"$.falsifiable_predictions[{i}].kind: {k!r} is not one of {', '.join(PRED_KINDS)}")
            kinds.append(k)
        if "upside" not in kinds:
            rep.fail("report", "no falsifiable prediction of kind 'upside' — state what the core bet buys on the "
                               "problem's standard metric, with the expected size (report_writer.md)")
        defensive = sum(k in ("safety", "cost") for k in kinds)
        if defensive * 2 > len(kinds):
            rep.warn("report", f"{defensive} of {len(kinds)} predictions are safety/cost — a proposal that mostly "
                               "promises 'no worse than the baseline' promises little (thinking_traps.md, T2)")
    kn = data.get("key_novelty")
    lever_text = kn.get("lever") if isinstance(kn, dict) else None
    if isinstance(lever_text, str) and lever_text.strip() and not re.search(
            r"\b(" + "|".join(LEVERS) + r")\b", lever_text, re.I):
        rep.warn("report", "key_novelty.lever names none of " + ", ".join(LEVERS) + " — fine if none fits, "
                           "but say plainly what the method changes")
    lim = data.get("limitations")
    if isinstance(lim, list) and not 3 <= len(lim) <= 5:
        rep.warn("report", f"limitations has {len(lim)} items (aim for 3-5)")

    for i, rw in enumerate(data.get("related_work") or []):
        for c in (rw.get("citations") or []) if isinstance(rw, dict) else []:
            if not isinstance(c, str) or not canonical(c):
                rep.fail("report", f"$.related_work[{i}].citations: {c!r} is not a bare paper id like 'arXiv:1706.02093'")
            else:
                all_text.append(f"[{c}]")

    ids = check_citations(run, "report", "\n".join(all_text), rep, "report.json ")
    if len(ids) < 3:
        rep.warn("report", f"report cites only {len(ids)} paper(s); related work, the mechanism source and "
                           "the closest competitor should all be cited")
    if verdicts is not None and "survive" not in verdicts.values():
        rep.warn("report", "report.json exists but no candidate has a `survive` verdict — "
                           "say so explicitly when delivering, with the reviewer's strongest objection")


# ------------------------------------------------------------------ checks

CHECK_FIELDS = ["**Question:**", "**Decision impact:**", "**Prediction and kill criterion:**", "**Setup:**",
                "**Result:**", "**Runtime:**", "**Conclusion:**", "**Script:**"]
CHECK_LIMITS = {"quick": 1, "standard": 3, "deep": 6}


def check_checks(run: Path, rep: Report, report_exists: bool) -> set[str]:
    text = _read(run / "checks.md")
    blocks = re.findall(r"^###\s+(K\d+)\b(.*?)(?=^###\s+K\d+\b|\Z)", text, re.M | re.S)
    ids = [k for k, _ in blocks]
    dupes = {k for k in ids if ids.count(k) > 1}
    if dupes:
        rep.fail("checks", f"duplicate check ids: {sorted(dupes)}")
    m = re.search(r"Depth:\s*(quick|standard|deep)", _read(run / "problem.md"), re.I)
    limit = CHECK_LIMITS[(m.group(1).lower() if m else "standard")]
    if len(set(ids)) > limit:
        rep.warn("checks", f"{len(set(ids))} sanity checks run; the limit for this depth is {limit}")
    for kid, body in blocks:
        tag = f"{kid}: "
        for field in CHECK_FIELDS:
            if field not in body:
                rep.fail("checks", tag + f"missing {field}")
        crit = re.search(r"\*\*Prediction and kill criterion:\*\*[ \t]*(.*)", body)
        if crit and len(crit.group(1).strip()) < 10:
            rep.fail("checks", tag + "kill criterion is empty — it must be written before the check runs")
        res = re.search(r"\*\*Result:\*\*[ \t]*(.*)", body)
        if res and res.group(1).strip().lower().startswith("pending"):
            (rep.fail if report_exists else rep.warn)("checks", tag + "result still 'pending' — record the outcome "
                                                      "(or 'timed out' / 'error')")
        concl = re.search(r"\*\*Conclusion:\*\*[ \t]*(\w+)", body)
        if concl and concl.group(1).lower() not in ("supports", "refutes", "inconclusive", "pending"):
            rep.warn("checks", tag + f"Conclusion should start with supports | refutes | inconclusive (got {concl.group(1)!r})")
        script = re.search(r"\*\*Script:\*\*\s*`?([^\s`]+)", body)
        if script and not (run / script.group(1)).exists():
            rep.warn("checks", tag + f"script {script.group(1)} not found in the run directory")
    known = set(ids)
    for fname in ("candidates.md", "scores.md", "report.json"):
        for ref in set(CHECK_REF_RE.findall(_read(run / fname))):
            if ref not in known:
                rep.fail("checks", f"{fname} refers to [check {ref}], which is not in checks.md")
    return known


# ------------------------------------------------------------------ main

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_dir")
    ap.add_argument("--stage", choices=["all", "papers", "gaps", "candidates", "scores", "checks", "report"], default="all")
    ap.add_argument("--cutoff", help="YYYY-MM-DD; defaults to 'Literature cutoff' in problem.md")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    run = Path(args.run_dir)
    if not run.is_dir():
        print(f"error: {run} is not a directory", file=sys.stderr)
        return 2
    cutoff = args.cutoff or _cutoff_from_problem(run)
    rep = Report()
    st = args.stage
    strict = st != "all"

    if st in ("all", "papers"):
        check_papers(run, rep, cutoff)
    if st in ("all", "gaps"):
        check_gaps(run, rep, strict or (run / "report.json").exists())
    cands: set[str] = set()
    if st in ("all", "candidates", "scores"):
        sub = Report()
        cands = check_candidates(run, rep if st != "scores" else sub, st == "candidates" or (run / "report.json").exists())
    verdicts: dict[str, str] = {}
    if st in ("all", "scores", "report"):
        sub = Report()
        verdicts = check_scores(run, rep if st != "report" else sub, cands, st == "scores" or (run / "report.json").exists())
    if st in ("all", "checks"):
        check_checks(run, rep, (run / "report.json").exists())
    if st in ("all", "report"):
        check_report(run, rep, verdicts, st == "report")

    if args.json:
        print(json.dumps({"fails": rep.n_fail, "items": [
            {"level": lvl, "stage": s, "message": m} for lvl, s, m in rep.items]}, ensure_ascii=False, indent=1))
    else:
        if not rep.items:
            scope = "all checks" if st == "all" else f"all {st} checks"
            print(f"PASS — {scope} passed" + (f" (cutoff {cutoff})" if cutoff else ""))
        for lvl, s, m in rep.items:
            print(f"{lvl:4}  [{s}] {m}")
        if rep.items:
            n_warn = len(rep.items) - rep.n_fail
            print(f"\n{rep.n_fail} FAIL, {n_warn} WARN" + (f" (cutoff {cutoff})" if cutoff else ""))
    return 1 if rep.n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
