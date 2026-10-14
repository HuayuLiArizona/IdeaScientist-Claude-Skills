---
name: idea-scientist
description: Turn an open research problem into ONE grounded, novel research proposal using the IdeaScientist method — a gap finder reads close prior work to pin down a methodological gap, an innovator borrows a mechanism from a different field that solved an analogous challenge, an adversarial reviewer tries to kill it, and a report writer develops the survivor into a full proposal where every citation was actually read. Use this whenever someone wants a research idea, a novel method for a technical challenge, a research proposal or 开题 direction, help finding a research gap, cross-domain inspiration, "what could I try for X", or AI-scientist / IdeaScientist-style ideation — even if they never say "proposal". Also for 科研idea、研究想法、创新点、找gap、研究提案. Not for plain literature surveys, summarizing a given paper, running experiments, or writing up results already obtained.
---

# IdeaScientist

Generate one grounded research proposal for an open problem. Adapted from *IdeaScientist: Orchestrating Agents for Grounded Scientific Ideation* (Liu et al., 2026, arXiv:2610.04074); see `NOTICE.md`.

## The idea behind the method

Good research ideas often come from noticing that a challenge in one field has the same underlying structure as a challenge another field already solved (two-stage retrieval → cascade ranking in recommendation; control variates in Monte Carlo → baselines in policy gradients). Left to itself, a model asked for "a novel idea" tends to recombine the most obvious in-domain techniques. In the paper, general-purpose agents produced ideas with genuine cross-setting transfer under 20% of the time; the decomposed pipeline did so 55–70% of the time, and restricting the innovator to same-domain retrieval roughly halved that rate.

So the method forces three separate moves, each with its own artifact:

1. **Gap finder** — reads the closest same-problem prior work and states *one precise methodological reason* it falls short (not "nobody did X").
2. **Innovator** — deliberately searches *other* fields for a mechanism that beat an analogous challenge, reads it, and argues why it transfers.
3. **Report writer** — turns the surviving intuition into a complete, falsifiable proposal.

A **reviewer** sits between innovator and writer and tries to refute novelty and transfer plausibility. A **paper reader** turns full text into short goal-focused digests, so no role reasons from titles or abstracts. You, the main agent, are the **orchestrator**: you keep `plan.md`, decide which role runs next, and judge the files they produce.

Two disciplines make the output trustworthy:

- **Artifacts are the interface.** Roles communicate only through files with fixed schemas (`references/schemas.md`). That keeps every stage inspectable and lets you send a single stage back for rework.
- **Read before cite.** A paper may be cited only if a digest for it exists in `papers/`. Fabricated near-miss papers are the easiest way for ideation to look good while being wrong, so `scripts/validate.py` checks this mechanically.

## Step 1 — Intake: pin down the problem and the challenge

The method needs two inputs: a **problem definition** (setting, inputs, outputs, what may change) and a **challenge** (what current solutions fail at, why it matters, a concrete failing case). Write them to `problem.md` (template created by `init_run.py`).

- **Concrete problem given** → formalize it directly.
- **A paper given** ("improve on this") → read it (WebFetch with goals) and extract its problem and the limitation the user cares about.
- **Only a topic** ("something about LLM agents memory") → propose 2–3 concrete (problem, challenge) framings in one short message and let the user pick. If the user isn't around to answer, pick the framing with the clearest failure mode and say which one you chose.

Keep the challenge solution-free: describe *what fails*, never *how to fix it*. A challenge that hints at the fix ("lacks a retrieval step") pre-decides the idea and defeats the gap and innovation stages.

Also list 1–3 **challenge axes** — distinct facets or suspected causes of the failure, in the field's own terminology (e.g. for speculative decoding failing on code: "draft–target distribution shift on rare identifiers", "drafter degradation at long context"). Each axis becomes one gap-finder task.

Record settings in `problem.md`:

| Setting | Default | Notes |
|---|---|---|
| Depth | `standard` | `quick` / `standard` / `deep` — see budgets below |
| Literature cutoff | none | Set a date only for retrospective tests ("would it have found X before X was published?"). When set, no paper dated on/after it may be read or cited. |
| Output language | the user's language | JSON keys stay English; search queries stay English since most literature is. |
| Retrieval backend | `web` | `web` (WebSearch + WebFetch) works everywhere. `api` / `vault` only if `scripts/lit_search.py check` says so. |

## Step 2 — Set up the run

```bash
python <skill_dir>/scripts/init_run.py ideation-<short-slug> --depth standard [--cutoff YYYY-MM-DD] [--language zh]
```

This creates `problem.md`, `plan.md`, `gaps.md`, `candidates.md`, `scores.md` and `papers/`. Fill in `problem.md`, then run `python <skill_dir>/scripts/lit_search.py check` once to learn whether the shell can reach literature APIs (often it cannot in hosted sandboxes; that is fine — `web` is the default).

Before running any role, read `references/retrieval.md` yourself once if you will be running roles inline; subagents read it themselves.

## Step 3 — Run the roles

### How a role runs

**If you can spawn subagents** (an Agent/Task tool): run each role as a subagent with this brief, filling the brackets:

```
You are the <ROLE> in an IdeaScientist ideation run.
1. Read <skill_dir>/references/roles/<role>.md and follow it exactly.
2. Read <skill_dir>/references/retrieval.md for how to search, read papers, and write digests.
3. Run directory: <run_dir>. The problem is in <run_dir>/problem.md — read it first.
4. TASK — <the structured fields for this role, below>
Write only the files your role owns. Reply with the one-line status your role file specifies.
```

In this mode, stay **blind to the literature**: do not search or read papers yourself; reason only over the run files. If you catch yourself wanting to look something up, that is a signal to spawn a role. This keeps your context free for the whole run and stops you from slipping your own (usually in-domain, obvious) idea into the pipeline. Run at most two subagents at once (e.g. two gap finders on different axes): web search is rate-limited per turn and parallel roles drain it for each other.

**If you cannot spawn subagents** (e.g. claude.ai, or when this skill is itself running inside a subagent): play each role yourself, one at a time. Before each role, re-read its role file and the current run files (do not rely on memory of earlier stages), write that role's artifact completely, then switch back to orchestrating. Record `Execution: inline` in `plan.md`.

Inline runs lose two protections, so compensate deliberately:
- *Independence between stages.* Having read the near misses, you will already have a favourite fix, usually the obvious in-domain one. Don't let it leak into `gaps.md`. When you reach the innovator, still list three outside sub-fields and search them before settling — if your favourite survives that comparison, fine. For the reviewer, genuinely switch stance: your job is to find why the candidate should *not* survive.
- *Blind evaluation.* The non-obviousness check in `references/evaluation.md` §4 can't run; skip it rather than reporting a contaminated score.

Say in the delivery that the run was inline.

### Structured task fields (the role's entire input besides problem.md)

| Role | Owns | Task fields |
|---|---|---|
| gap_finder | `gaps.md` | `AXIS:` one axis phrase, copied exactly |
| innovator | `candidates.md` | `TARGET: C<n>` · `GAP: <axis> — <gap sentence>` · optional `BUILD_ON: C<x>, FOCUS: <dim>` |
| reviewer | `scores.md` | `TARGET: C<n>` |
| report_writer | `report.json` | `TARGET: C<n>` |
| (all) | `papers/<id>.md` | digests, written by whoever reads the paper |

You own `problem.md` and `plan.md` only. If another file is wrong or thin, re-run its owning role with feedback in the task ("AXIS: … — previous pass cited only one paper; find more near misses"), rather than editing it yourself — the owner has the reading context to fix it properly.

Keep tasks narrow. One axis per gap finder, one candidate per innovator call, one candidate per review. If you are about to write "and also consider…", split it into separate tasks.

## Step 4 — The orchestration loop

Keep `plan.md` current: the active direction, its status (`forming` → `drilling` → `under_review` → `survived` / `dead` → `complete`), and an append-only history line for every decision (`under_review @ step 5: C2 sent to reviewer — builds on C1, fixes mapping`).

The usual forward path:

1. **Map the landscape.** Spawn a gap finder on the most central axis. Other axes can run in parallel (they are independent). Read the `## Axis:` sections in `gaps.md`. You don't need every axis mapped before committing — go depth-first.
2. **Choose a direction.** Pick ONE gap: grounded in near-miss papers that were actually read, methodological (not "no benchmark exists"), important, and plausibly attackable. Record it as the active direction.
3. **Ideate.** Spawn one innovator with `TARGET` and `GAP`. It searches other fields, forms ONE intuition, grounds it, and appends `C<n>`. Log what it builds on in `plan.md`.
4. **Review.** Spawn the reviewer on `C<n>`.
5. **Act on the verdict.**
   - `survive` → go to 6.
   - `revise(focus=<dim>)` → new innovator call with `BUILD_ON: C<n>, FOCUS: <dim>`, then review the new candidate. After 2–3 revise rounds without a survive, treat it as a reject.
   - `reject(reason=…)` → the direction is dead; don't rescue it. Pick a different gap (or map a new axis) and return to 3.
6. **Commit.** Spawn the report writer on the surviving candidate.
7. **Validate** — `python <skill_dir>/scripts/validate.py <run_dir>`. Failures go back to the owning role with the validator's message as feedback.
8. **Deliver** (Step 5).

The loop is a graph, not a line. Move backward whenever the files say so: a thin gap survey → another gap finder on the same axis; an innovator that can't find a fillable gap → more landscape; a report writer that can't ground a load-bearing claim → back to the innovator, or to the gap finder if related-work coverage is too thin to defend novelty. Run innovators one at a time per direction — five parallel innovators produce five shallow ideas, while one reviewed-and-revised idea gets sharper.

**One invariant:** never spawn the report writer until a candidate has a `survive` verdict. If the budget runs out first, you may commit to the best candidate, but say so plainly in the delivery and include the reviewer's strongest objection.

### Budgets by depth

| | quick | standard | deep |
|---|---|---|---|
| Axes mapped | 1 | 1–2 | 2–3 |
| Papers read per gap-finder call | 4–6 | 6–10 | up to 14 |
| Papers read per innovator call | 2–3 | 3–6 | up to 10 |
| Papers read per reviewer call | 1–3 | 2–5 | up to 8 |
| Rebuilds after `revise` (each rebuild is re-reviewed) | 1 | 2 | 3 |
| Directions tried before forced commit | 1 | 2 | 3 |
| Report length (`report_writer.md`) | ~1–2k words | ~2.5–4k words | as needed |
| Self-evaluation (`references/evaluation.md`) | none | §1 quality + §3 transfer | all four, §4 with a blind subagent |

Search budgets per call are in `references/retrieval.md` §3. All of these are per role call and soft: exceed a reading budget when honest coverage needs it (a close near miss often turns up late), and note it under `Deviations` in `plan.md`. When a rebuild budget is spent without a `survive`, pivot to another direction if one is left; otherwise force-commit to the best candidate and flag it (see the invariant above).

Reading and searching are the main expense. A quick run should feel quick: one axis, one candidate, at most one rebuild, a short report.

### Keeping the user informed

Runs take a while. If the user is present and you have a way to message them mid-task, send one line at each meaningful transition — which gap you chose, the candidate's one-sentence intuition, the reviewer's verdict, a pivot — so they can redirect early ("not that gap, we already tried it"). When running unattended or as a subagent, keep that record in `plan.md`'s history instead.

## Step 5 — Deliver

1. `python <skill_dir>/scripts/render_report.py <run_dir>` → `report.md` (readable proposal with a linked reference list built from the digests).
2. Run the self-evaluation that the depth calls for (`references/evaluation.md`; none for quick) and write `evaluation.md`. Present scores as diagnostics, not verdicts — LLM judges and human experts agree only moderately on proposal quality.
3. In your reply, give a short summary rather than the whole proposal (about 150–250 words for quick, longer only as needed):
   - the one-sentence thesis;
   - the gap (and the near-miss papers that define it);
   - the borrowed mechanism, where it comes from, and why it should transfer;
   - the single closest prior work and how this differs;
   - the reviewer's verdict and the main risk;
   - anything that didn't run as designed: inline execution, novelty searches that couldn't run, a forced commit without `survive`;
   - where the files are (`report.md`, `report.json`, and the run directory with every intermediate artifact).

   Hand over `report.md` in whatever way the environment prefers for documents. Offer one natural next step: explore the runner-up direction, deepen the evaluation, or draft an experiment plan.

## Files in this skill

| File | Read when |
|---|---|
| `references/roles/gap_finder.md`, `innovator.md`, `reviewer.md`, `report_writer.md`, `paper_reader.md` | Running (or briefing) that role |
| `references/schemas.md` | Checking what a run file must contain |
| `references/retrieval.md` | Before any searching or reading — IDs, the two search regimes, digests, cutoff |
| `references/evaluation.md` | Self-evaluating a finished proposal |
| `scripts/init_run.py` | Creating a run directory |
| `scripts/lit_search.py` | `check`, then `search` / `fulltext` when the shell has network or a local vault |
| `scripts/validate.py` | After each role (optional) and always before delivery |
| `scripts/render_report.py` | Turning `report.json` into `report.md` |
| `assets/report_schema.json` | The proposal skeleton the report writer fills |
