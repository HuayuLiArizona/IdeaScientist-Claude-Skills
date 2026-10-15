# Run files and their schemas

Every run lives in one directory. Each file has exactly one owner; everyone else only reads it. The schemas are fixed because `scripts/validate.py` parses them and because each stage's file is the whole interface to the next stage.

```
<run_dir>/
├── .run_meta.json   init_run.py   — start time and depth, read by status.py
├── problem.md       orchestrator  — problem definition, challenge, axes, settings
├── plan.md          orchestrator  — active direction, status, history
├── gaps.md          gap finder    — one "## Axis:" section per axis
├── candidates.md    innovator     — one "### C<n>" block per call
├── scores.md        reviewer      — one "### C<n> verdict" block per review
├── checks.md        innovator / reviewer — pre-registered sanity checks K1, K2, … (format in sanity_checks.md)
├── checks/K<n>.py   the check scripts
├── papers/<id>.md   any reader    — cumulative goal-by-goal digests
├── report.json      report writer — the proposal (assets/report_schema.json)
├── report.md        render_report.py
└── evaluation.md    optional self-evaluation
```

## problem.md

```markdown
# Problem

## Problem definition
- Formal setting: …
- Inputs: …
- Outputs: …
- Constraints: what may change and what is fixed (e.g. "model weights frozen", "single GPU")

## Challenge
- What fails and why: …
- Why it matters: …
- Concrete failing example: …

## Challenge axes
- <axis 1, in the field's own terminology>
- <axis 2>

## Settings
- Depth: standard
- Literature cutoff: none
- Output language: en
- Retrieval backend: web
- Idea source: problem          ← "user" in Mode B
- Deliverable: proposal          ← Mode B: "novelty check" or "proposal"

## User idea
<Mode B only: the user's idea, verbatim>

## User notes
- <preferences, things already tried, directions to avoid>
```

The challenge describes what fails, never how to fix it.

## plan.md

```markdown
# Plan

Goal: ONE focused, well-grounded methodological intuition, developed into a full proposal.

Started: 2026-10-14T15:03:00+0000      ← written by init_run.py; status.py measures elapsed time from it

## Axes
- [x] <axis 1> — mapped (2 gaps)
- [ ] <axis 2>

## Mode
- Execution: subagents | inline
- Deviations: <caps hit, checks that could not run (e.g. search exhausted), forced commits>

## Active direction
- Gap: <axis> — <gap sentence>
- Candidate: C2
- Status: under_review

## History
- `forming` @1: mapped axis 1; gap 1.2 has the best-grounded near misses
- `drilling` @2: C1 created, new intuition from <source field>
- `under_review` @3: C1 → reviewer
- `drilling` @4: C1 revise(focus=mapping) → C2 builds on C1
```

Status is one of `forming`, `drilling`, `under_review`, `survived`, `dead`, `complete`. History is append-only.

## gaps.md

One section per axis:

```markdown
## Axis: <axis, verbatim from the task>

### What has been done
<mechanism-level summary with [ids]>

### Open gaps on this axis
- **Gap:** …
- **Near-miss methods and coverage:** …
- **Methodological deficiency:** …
- **Why it matters:** …
- **Evidence route:** …
```

At most 2 gaps per axis; each gap starts with a `- **Gap:**` line and has all five fields. Zero gaps is valid ("No methodological gap found; searched: …").

## candidates.md

```markdown
### C<n> — <short title>
- **Origin:** system | user
- **Intuition:** …
- **Gap it attacks:** …
- **If improving prior candidate:** …        (optional)
- **Source inspiration:** … novelty type: new-topic | recombination-of-distant-concepts | reinforcing-a-weak-connection | extension-or-deepening | fixing-a-shortcoming | reframing
- **How it maps to this problem:** …
- **Why it could work:** …
- **Novelty vs. closest in-domain work:** …
- **Main risk:** …
```

For `Origin: user`, Source inspiration may be `user's own construction`, and the novelty line may read `to be assessed in the novelty survey`.

## scores.md

```markdown
### C<n> verdict
- **Verdict:** survive | revise(focus=<novelty|coherence|feasibility|clarity|mapping|grounding>) | reject(reason=<…; "collision: …" for a collision>)
- **Search trail:** <novelty queries run; anything left unchecked>
- **Closest work:**
  - [id] — problem: … · method: … · contribution: …
- **Novelty argument:** <one paragraph: what is added or advanced over the closest work, and why it matters; "n/a — collision" when rejecting for collision>
- **Collision report:** <only for a collision: papers, where problem/method/contribution coincide, why the differences can't carry a novelty claim>
- **Evidence:**
  - [id] — …
- **Strongest objection:** …
```

A collision (`reject(reason=collision…)`) requires overlap on core problem, key method *and* main contribution, and every paper in the collision report must have a full-text digest. `validate.py` enforces the latter.

## papers/<safe_id>.md

```markdown
# <exact title>
- ID: arXiv:1706.02093
- Source: <url read>
- Date: YYYY-MM-DD            ← first public date; YYYY-MM or YYYY if that's all you know; nothing else on this line
- Version: v2 (YYYY-MM-DD)    ← version read; required for arXiv papers in cutoff runs
- Access: full-text | abstract-only
- Note: <optional: venue, remarks>

## What this paper does
<≤120 words>

## Goal-by-goal answers
### Goal: <question>
<≤300 words>
```

`safe_id` = the ID with every character outside `[A-Za-z0-9._-]` replaced by `_` (DOIs lower-cased). Use `scripts/lit_search.py path <id>` to get it.

## report.json

A single JSON object following `assets/report_schema.json`. Every top-level field is required:

| Field | What it holds |
|---|---|
| `title` | Proposal title |
| `topic_relevance` | `sub_topic[]`, `primary_focus[]` |
| `one_sentence_thesis` | <30 words, no numbers |
| `core_problem` | `problem_statement`, `why_it_matters[]` (motivation only), `concrete_example` |
| `key_novelty` | `main_idea`, `explanation[]` (intuition level) |
| `problem_definition` | `formal_setting`, `inputs`, `outputs` |
| `key_terms` | term → plain-language definition |
| `related_work[]` | `sub_area`, `what_it_does`, `open_gap`, `citations[]` |
| `method` | `high_level_flow[]`, `modules[]`, `novel_architectural_elements[]`, `pseudocode`, `design_choices[]`, `theoretical_grounding` |
| `model_details` | `base_model`, `training{method, objective_functions[], adaptation, key_hyperparameters{}}` |
| `comparison_to_sota` | `related_methods[]`, `key_differences[]` |
| `proposed_evaluation` | `evaluation_setting`, `benchmarks[]`, `baselines[]`, `main_metrics[]`, `ablations[]` |
| `falsifiable_predictions[]` | `pillar`, `prediction`, `kill_condition` |
| `limitations[]` | 3–5 items |

Citations are bracketed IDs inside strings; `related_work[].citations` holds bare ID strings. No measured results anywhere.
