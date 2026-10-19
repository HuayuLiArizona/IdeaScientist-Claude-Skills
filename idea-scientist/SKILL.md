---
name: idea-scientist
description: IdeaScientist research ideation — run ONLY when explicitly requested, i.e. the user types /idea-scientist or asks by name to use the idea-scientist skill. Do not start it on your own for ordinary questions about research ideas, gaps, novelty or proposals; answer those normally, and at most mention that /idea-scientist can do a full run. When invoked, it turns an open research problem into ONE grounded research proposal (gap finder → cross-domain innovator → reviewer who reads the closest work in full and argues novelty → report writer; every citation actually read), or checks the novelty of the user's own idea (查新/撞车) and develops it.
disable-model-invocation: true
---

# IdeaScientist

Generate one grounded research proposal for an open problem. Adapted from *IdeaScientist: Orchestrating Agents for Grounded Scientific Ideation* (Liu et al., 2026, arXiv:2610.04074); see `NOTICE.md`.

## The idea behind the method

Good research ideas often come from noticing that a challenge in one field has the same underlying structure as a challenge another field already solved (two-stage retrieval → cascade ranking in recommendation; nonequilibrium thermodynamics → diffusion generative models). Left to itself, a model asked for "a novel idea" tends to recombine the most obvious in-domain techniques. In the paper, general-purpose agents produced ideas with genuine cross-setting transfer under 20% of the time; the decomposed pipeline did so 55–70% of the time, and restricting the innovator to same-domain retrieval roughly halved that rate.

So the method forces three separate moves, each with its own artifact:

1. **Gap finder** — reads the closest same-problem prior work and states *one precise methodological reason* it falls short (not "nobody did X").
2. **Innovator** — deliberately searches *other* fields for a mechanism that beat an analogous challenge, reads it, and argues why it transfers.
3. **Report writer** — turns the surviving intuition into a complete, falsifiable proposal.

A **reviewer** sits between innovator and writer and tries to refute novelty and transfer plausibility. A **paper reader** turns full text into short goal-focused digests, so no role reasons from titles or abstracts. You, the main agent, are the **orchestrator**: you keep `plan.md`, decide which role runs next, and judge the files they produce.

### What counts as a viable idea

Don't chase absolute originality, and don't drop a direction just because related work exists. Prior attempts on a nearby problem don't make an idea worthless. An idea is viable when it has a **clear, meaningful increment** over the closest work and room to explore further. For example, it may:

- push an existing idea further, deepen it, or complete it;
- fix a concrete shortcoming of existing methods;
- reorganize the problem from a new angle and tell a more complete, more convincing story.

The question every role asks is *what exactly is added, and why does it matter*, not *has anything like this ever been done*. Cross-domain transfer is still the preferred way to find ideas, because it tends to produce larger increments, but it's a means, not a requirement.

The bar also cuts the other way: never manufacture novelty. An idea is a **collision** only when, after reading the closest papers in full, it overlaps with existing work on all three of the core problem, the key method and the main contribution, so that no substantive distinction remains. Then say so plainly: name the papers and the exact overlap.

### Idea shapes the pipeline drifts toward

Agents reviewing agents reward defensibility, so a run left alone converges on a few safe shapes whatever the problem: a diagnosis dressed as a method; a small mechanism wrapped in gates and fallbacks that "reduces to the baseline by construction"; and, most of all, "change the objective" — reshape the reward, reweight, add a credit term — because it's the cheapest change that still counts as a method. `references/thinking_traps.md` names five such traps and defines the **lever space** (objective, representation, architecture, data, inference, interface, formulation, systems) that every role uses to widen the search: the innovator compares levers before committing, the reviewer asks whether another lever would make the candidate unnecessary and whether its core bet has been buried under guards, and you steer away from levers the run has already used. None of these shapes is banned; the point is to reach them by comparison, not by default.

Two disciplines make the output trustworthy:

- **Artifacts are the interface.** Roles communicate only through files with fixed schemas (`references/schemas.md`). That keeps every stage inspectable and lets you send a single stage back for rework.
- **Read before cite.** A paper may be cited only if a digest for it exists in `papers/`. Fabricated near-miss papers are the easiest way for ideation to look good while being wrong, so `scripts/validate.py` checks this mechanically.

## Step 1 — Intake: pin down the problem and the challenge

This skill runs only on explicit request (`/idea-scientist`). Treat any text that came with the command as the request: a problem, a paper, a topic or the user's own idea, plus options such as depth, a cutoff date or "novelty check only". In Claude Code that text is appended at the end of this file as `ARGUMENTS:`. If the command came with no text and the conversation doesn't already make the request clear, ask in one short message for the problem or idea, and optionally depth and output language.

The method needs two inputs: a **problem definition** (setting, inputs, outputs, what may change) and a **challenge** (what current solutions fail at, why it matters, a concrete failing case). Write them to `problem.md` (template created by `init_run.py`).

- **Concrete problem given** → formalize it directly.
- **A paper given** ("improve on this") → read it (WebFetch with goals) and extract its problem and the limitation the user cares about. State the challenge at the level of the problem ("acceptance rate collapses on code"), not as the paper's missing feature, and don't copy the paper's design choices (a frozen model, its reward, its pipeline) into Constraints — see the rule below.
- **Only a topic** ("something about LLM agents memory") → propose 2–3 concrete (problem, challenge) framings in one short message and let the user pick. If the user isn't around to answer, pick the framing with the clearest failure mode and say which one you chose.
- **The user's own idea** ("I want to do X with Y — has anyone done this?", "check the novelty of my idea") → **user-idea mode** (see *Mode B* below). Extract the problem and challenge the idea targets into `problem.md`, copy the idea verbatim under `## User idea`, and set `Idea source: user`. Also note what the user wants back: a novelty check only, or a developed proposal. If they don't say, deliver the novelty assessment and offer to develop it into a proposal.

Keep the challenge solution-free: describe *what fails*, never *how to fix it*. A challenge that hints at the fix ("lacks a retrieval step") pre-decides the idea and defeats the gap and innovation stages.

Keep the Constraints honest too: list only what the user stated or what is genuinely fixed (physics, compute budget, deployment requirements). A base paper's design choices are not constraints unless the user makes them so. Every invented constraint ("the backbone stays frozen", "only the reward may change") removes levers before anyone has looked at them, and pushes every candidate toward "that paper plus a module". If the user does want a drop-in improvement, record it as a constraint and note it in `## User notes`.

Also list 1–3 **challenge axes** — distinct facets or suspected causes of the failure, in the field's own terminology (e.g. for speculative decoding failing on code: "draft–target distribution shift on rare identifiers", "drafter degradation at long context"). Each axis becomes one gap-finder task.

Record settings in `problem.md`:

| Setting | Default | Notes |
|---|---|---|
| Depth | `standard` | `quick` / `standard` / `deep` — see budgets below |
| Literature cutoff | none | Set a date only for retrospective tests ("would it have found X before X was published?"). When set, no paper dated on/after it may be read or cited. |
| Output language | the user's language | JSON keys stay English; search queries stay English since most literature is. |
| Retrieval backend | `web` | `web` (WebSearch + WebFetch) works everywhere. `api` / `vault` only if `scripts/lit_search.py check` says so. |
| Idea source | `problem` | `user` when the user brought their own idea (Mode B) |

## Step 2 — Set up the run

```bash
python <skill_dir>/scripts/init_run.py ideation-<short-slug> --depth standard [--cutoff YYYY-MM-DD] [--language zh] [--user-idea]
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
   [innovator, reviewer] Also read <skill_dir>/references/thinking_traps.md.
3. Run directory: <run_dir>. The problem is in <run_dir>/problem.md — read it first.
4. TASK — <the structured fields for this role, below>
5. HARD CAPS for this call: at most <P> papers read and <S> web searches (see the per-call
   table in SKILL.md). When you reach either cap, stop gathering and write your artifact
   with what you have. Do not spawn subagents. Do not wait and retry a refused request.
   [innovator, reviewer] You may run at most ONE quick numerical sanity check, following
   <skill_dir>/references/sanity_checks.md (pre-register in checks.md, 5-minute timeout).
   [gap finder, report writer] Work from the literature only; run no experiments.
Write only the files your role owns. Reply with the one-line status your role file specifies.
```

In this mode, stay **blind to the literature**: do not search or read papers yourself; reason only over the run files. If you catch yourself wanting to look something up, that is a signal to spawn a role. This keeps your context free for the whole run and stops you from slipping your own (usually in-domain, obvious) idea into the pipeline. Run at most two subagents at once (e.g. two gap finders on different axes): web search is rate-limited per turn and parallel roles drain it for each other.

**If you cannot spawn subagents** (e.g. claude.ai, or when this skill is itself running inside a subagent): play each role yourself, one at a time. Before each role, re-read its role file and the current run files (do not rely on memory of earlier stages), write that role's artifact completely, then switch back to orchestrating. Record `Execution: inline` in `plan.md`.

The caps and the sanity-check rules in line 5 of the brief apply to you too. Inline runs lose two protections, so compensate deliberately:
- *Independence between stages.* Having read the near misses, you will already have a favourite fix, usually the obvious in-domain one. Don't let it leak into `gaps.md`. When you reach the innovator, still write out the lever space and list three outside sub-fields, and search them before settling — if your favourite survives that comparison, fine. (It is most often an objective tweak; that's trap T3.) For the reviewer, genuinely switch stance: your job is to find why the candidate should *not* survive.
- *Blind evaluation.* The non-obviousness check in `references/evaluation.md` §4 can't run; skip it rather than reporting a contaminated score.

Say in the delivery that the run was inline.

### Structured task fields (the role's entire input besides problem.md)

| Role | Owns | Task fields |
|---|---|---|
| gap_finder | `gaps.md` | `AXIS:` one axis phrase, copied exactly |
| innovator | `candidates.md` | `TARGET: C<n>` · `GAP: <axis> — <gap sentence>` · optional `BUILD_ON: C<x>, FOCUS: <dim>` · optional `AVOID_LEVER: <lever>[, …]` · Mode B: `USER_IDEA: yes` (formalize the idea in `problem.md`; don't replace it) |
| reviewer | `scores.md` | `TARGET: C<n>` · `FINAL: yes` when no rebuilds remain for this direction (verdict must then be survive or reject) · Mode B, first review: `MODE: novelty-survey` |
| report_writer | `report.json` | `TARGET: C<n>` |
| (all) | `papers/<id>.md` | digests, written by whoever reads the paper |

You own `problem.md` and `plan.md` only. If another file is wrong or thin, re-run its owning role with feedback in the task ("AXIS: … — previous pass cited only one paper; find more near misses"), rather than editing it yourself — the owner has the reading context to fix it properly.

Keep tasks narrow. One axis per gap finder, one candidate per innovator call, one candidate per review. If you are about to write "and also consider…", split it into separate tasks.

## Step 4 — The orchestration loop

Keep `plan.md` current: the active direction, its status (`forming` → `drilling` → `under_review` → `survived` / `dead` → `complete`), and an append-only history line for every decision (`under_review @ step 5: C2 sent to reviewer — builds on C1, fixes mapping`).

**After every role call, run `python <skill_dir>/scripts/status.py <run_dir>` and obey its last line** (details under *Hard limits* below). This is not optional: it is what keeps a run from going on for hours.

The usual forward path:

1. **Map the landscape.** Spawn a gap finder on the most central axis. Other axes can run in parallel (they are independent). Read the `## Axis:` sections in `gaps.md`. You don't need every axis mapped before committing — go depth-first.
2. **Choose a direction.** Pick ONE gap: grounded in near-miss papers that were actually read, methodological (not "no benchmark exists"), important, and plausibly attackable. Other things equal, prefer a gap whose cause leaves room for more than one lever (an **Alternative cause** is a good sign); a gap that admits only "add a term to the objective" tends to yield a small increment. Record it as the active direction.
3. **Ideate.** Spawn one innovator with `TARGET` and `GAP`. It compares levers, searches other fields, forms ONE intuition, grounds it, and appends `C<n>`. Log what it builds on and its lever in `plan.md`. Whenever the call is a *fresh* intuition rather than a rebuild — a new direction, or a new attempt on the same gap — pass the levers this run has already used as `AVOID_LEVER` (`status.py` lists them). That is the one place where you, not the roles, keep the run from circling one kind of fix.
4. **Review.** Spawn the reviewer on `C<n>`.
5. **Act on the verdict.**
   - `survive` → go to 6.
   - `revise(focus=<dim>)` → new innovator call with `BUILD_ON: C<n>, FOCUS: <dim>`, then review the new candidate. When that rebuild is the last one the depth allows, pass `FINAL: yes` to its review, so the verdict is survive or reject and the direction can't loop. `focus=ambition` (the core bet is too small or buried under guards) and `focus=lever` (another lever would make this unnecessary) are rebuilds like any other; don't add `AVOID_LEVER` to them except to exclude the old lever on a `focus=lever` rebuild that the review says should switch.
   - `reject(reason=…)` → the direction is dead (a fatal flaw, or a collision on problem, method and contribution); don't rescue it. Pick a different gap (or map a new axis) and return to 3.
6. **Commit.** Spawn the report writer on the surviving candidate.
7. **Validate** — `python <skill_dir>/scripts/validate.py <run_dir>`. FAILs go back to the owning role with the validator's message as feedback; WARNs are advisory and never block delivery. **At most two validate–fix rounds.** If FAILs remain after that, fix them yourself in the cheapest way (drop the offending citation or claim — no new reading) and list what was dropped in the delivery.
8. **Deliver** (Step 5).

The loop is a graph, not a line. Move backward whenever the files say so: a thin gap survey → another gap finder on the same axis; an innovator that can't find a fillable gap → more landscape; a report writer that can't ground a load-bearing claim → back to the innovator, or to the gap finder if related-work coverage is too thin to defend novelty. Every backward move still counts against the hard limits, and `status.py` has the final word. Run innovators one at a time per direction — five parallel innovators produce five shallow ideas, while one reviewed-and-revised idea gets sharper.

**One invariant:** never spawn the report writer until a candidate has a `survive` verdict — unless `status.py` says WRAP UP or STOP, in which case commit to the best candidate, say plainly in the delivery that it is a forced commit, and include the reviewer's strongest objection.

### Mode B — the user brings an idea

The user's idea is the subject of the run, not a seed to replace. Default to keeping and developing it.

1. **Formalize.** Spawn the innovator with `TARGET: C1` and `USER_IDEA: yes`. It writes the user's idea into the candidate schema faithfully, marked `Origin: user`, and reads the papers the idea builds on. It does not swap in a different mechanism.
2. **Novelty survey.** Spawn the reviewer with `TARGET: C1, MODE: novelty-survey`. It searches for the works closest to the idea, reads them in full (setting, core method, technical details, contribution boundary), and writes the closest-work comparison and either a novelty argument or a collision report (`roles/reviewer.md`). It gets the larger per-call budget below. A gap finder is optional: run one only if the user wants a full proposal and the related-work picture is thin.
3. **Act on the verdict.**
   - `survive` → if the user wants a proposal, run the report writer. Otherwise deliver the novelty assessment and offer to develop it.
   - `revise(focus=…)` → the idea is viable but its positioning or a component needs sharpening. Rebuild with `BUILD_ON: C1, FOCUS: <dim>`: the innovator keeps the user's core idea and changes only what the review asked for. Re-review, with `FINAL: yes` on the last allowed rebuild.
   - `reject(reason=collision …)` → stop. Deliver the collision report: which papers, where exactly they overlap, and why the remaining differences can't support a credible novelty claim. Don't pivot to a different idea on your own. In the delivery, offer to look for a differentiated variant, or to switch to problem mode on the same problem.

### Hard limits

Two kinds of limit, both firm.

**Per role call.** These go into each subagent's brief (line 5), or you apply them to yourself when running inline. On reaching either cap, stop gathering and write the artifact with what you have.

| Per call: papers read / web searches | quick | standard | deep |
|---|---|---|---|
| Gap finder (snowballed papers count too) | 6 / 4 | 10 / 8 | 14 / 12 |
| Innovator | 3 / 6 | 6 / 10 | 10 / 14 |
| Reviewer | 3 / 3 | 5 / 5 | 8 / 8 |
| Reviewer, `MODE: novelty-survey` (Mode B) | 6 / 4 | 10 / 8 | 14 / 12 |
| Report writer | 3 / 2 | 5 / 4 | 8 / 6 |

**Per run.** `status.py` checks these after every role call:

| Per run | quick | standard | deep |
|---|---|---|---|
| Papers read (total) | 20 | 45 | 80 |
| Axes mapped | 1 | 2 | 3 |
| Candidates (C1, C2, …) | 2 | 4 | 6 |
| Wrap-up after | 30 min | 75 min | 150 min |
| Hard stop after | 45 min | 120 min | 240 min |

What its verdict means:
- **CONTINUE** — carry on.
- **WRAP UP** — no new gap-finder or innovator calls. Follow its `Next:` line: at most one more review, then the report writer, validation and delivery.
- **STOP** — no more reading or searching by anyone. Deliver now with what exists: report writer from existing digests if there's a candidate, otherwise the gap analysis. Never start another loop after STOP.

Other depth settings:

| | quick | standard | deep |
|---|---|---|---|
| Rebuilds after `revise` (each rebuild is re-reviewed) | 1 | 2 | 3 |
| Directions tried before forced commit | 1 | 2 | 3 |
| Report length (`report_writer.md`) | ~1–2k words | ~2.5–4k words | as needed |
| Self-evaluation (`references/evaluation.md`) | none | §1 quality + §3 transfer + §5 idea shape | all five, §4 with a blind subagent |

Search budgets are per call (`references/retrieval.md` §3). A quick run should feel quick: one axis, one candidate, at most one rebuild, a short report.

### Resuming after an interruption or context reset

Long runs can be interrupted, or have their context compacted. When that happens, don't reconstruct the run from memory. Re-read `plan.md` (state and history) and run `status.py`. Treat every role call the history marks as done as done: never re-run a stage just because you don't remember its details — read its file instead. If `plan.md` and the artifacts disagree, trust the artifacts.

### Keeping the user informed

Runs take a while. If the user is present and you have a way to message them mid-task, send one line at each meaningful transition — which gap you chose, the candidate's one-sentence intuition, the reviewer's verdict, a pivot — so they can redirect early ("not that gap, we already tried it"). When running unattended or as a subagent, keep that record in `plan.md`'s history instead.

## Step 5 — Deliver

1. `python <skill_dir>/scripts/render_report.py <run_dir>` → `report.md` (readable proposal with a linked reference list built from the digests).
2. Run the self-evaluation that the depth calls for (`references/evaluation.md`; none for quick) and write `evaluation.md`. Present scores as diagnostics, not verdicts — LLM judges and human experts agree only moderately on proposal quality.
3. **Mode B novelty check only** (no proposal requested): skip steps 1–2. Reply with the verdict; the closest works and how each relates; the reviewer's novelty argument paragraph (or the collision report); and the suggested positioning or next step. Point to `scores.md` and `papers/` for the evidence.
4. Otherwise, in your reply give a short summary rather than the whole proposal (about 150–250 words for quick, longer only as needed):
   - the one-sentence thesis;
   - the gap (and the near-miss papers that define it);
   - the borrowed mechanism, where it comes from, and why it should transfer;
   - its lever, and the strongest alternative lever it was chosen over;
   - the single closest prior work and how this differs;
   - the reviewer's verdict and the main risk;
   - anything that didn't run as designed: inline execution, novelty searches that couldn't run, a forced commit without `survive`;
   - where the files are (`report.md`, `report.json`, and the run directory with every intermediate artifact).

   Hand over `report.md` in whatever way the environment prefers for documents. Offer one natural next step: explore the runner-up direction, deepen the evaluation, or draft an experiment plan.

## Files in this skill

| File | Read when |
|---|---|
| `references/roles/gap_finder.md`, `innovator.md`, `reviewer.md`, `report_writer.md`, `paper_reader.md` | Running (or briefing) that role |
| `references/thinking_traps.md` | Innovator and reviewer, once per call; you, when choosing directions and reading verdicts — the five traps and the lever space |
| `references/schemas.md` | Checking what a run file must contain |
| `references/retrieval.md` | Before any searching or reading — IDs, the two search regimes, digests, cutoff |
| `references/sanity_checks.md` | Innovator or reviewer considering a quick numerical check |
| `references/evaluation.md` | Self-evaluating a finished proposal |
| `scripts/init_run.py` | Creating a run directory |
| `scripts/status.py` | After every role call — CONTINUE / WRAP UP / STOP |
| `scripts/lit_search.py` | `check`, then `search` / `fulltext` when the shell has network or a local vault |
| `scripts/validate.py` | After each role (optional) and always before delivery |
| `scripts/render_report.py` | Turning `report.json` into `report.md` |
| `assets/report_schema.json` | The proposal skeleton the report writer fills |
