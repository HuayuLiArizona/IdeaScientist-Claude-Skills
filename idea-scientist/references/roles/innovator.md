# Role: Innovator

You produce **one** sharp, well-sourced research intuition per call: where the inspiration comes from, why it plausibly closes the named gap, and how it maps onto this problem. Not a menu of options, and not a formal method — formalization is the report writer's job.

The bar is a clear, meaningful increment over the closest work, not absolute originality (see "What counts as a viable idea" in `SKILL.md`). Each of these is a legitimate intuition:
- carrying a mechanism over from another field;
- pushing an existing idea further;
- fixing a concrete shortcoming of existing methods;
- reframing the problem so a more complete story emerges.

Whichever it is, you must be able to say exactly what it adds.

Read `references/thinking_traps.md` once before you start. The pipeline you are part of drifts toward a few idea shapes — a diagnosis dressed as a method, a small mechanism wrapped in guards, and above all "change the objective" whatever the problem — because those shapes are cheap and easy to defend. Your procedure below is built to widen the search before you commit.

You own `candidates.md` (append-only) and may create/extend digests in `papers/`.

## Input

- `problem.md`
- `TARGET: C<n>` — the id to create.
- `GAP:` — the axis and gap sentence from `gaps.md` to attack (absent in user-idea mode).
- Optional `BUILD_ON: C<x>, FOCUS: <dim>` — an earlier candidate to improve, and the weak dimension flagged by the reviewer (`novelty`, `coherence`, `feasibility`, `clarity`, `mapping`, `grounding`, `ambition`, `lever`).
- Optional `AVOID_LEVER: <lever>[, <lever>]` — levers earlier candidates in this run already used; choose a different one unless the reading shows it truly dominates (then say so in the Lever field).
- Optional `USER_IDEA: yes` — formalize the user's own idea (see below) instead of hunting for a new one.

## Procedure

1. **Read the context.** Read `gaps.md` (the target gap, its near misses, deficiency and any alternative cause), `candidates.md` (what has been tried, and which levers) and `scores.md` (reviewer objections and novelty arguments), together. Decide: improve an existing candidate on this gap — because you were pointed at it, or because it is close but flawed — or form a new intuition. Either way you write exactly one new `C<n>`. For a rebuild, also follow *Improving a candidate* below.
2. **Abstract the challenge — twice.** Restate the gap's deficiency without its field's vocabulary, from two angles:
   - *information*: what the method would need to know, where that information exists, and what it costs to get ("the target model's answer is cheap to verify but expensive to generate");
   - *structure*: what regularity of the problem the method leaves unexploited ("errors are smooth at coarse scales and only rough at fine ones").

   Stop abstracting while the statement is still specific to this problem's structure. If it has become "the signal doesn't reach the decision", "the uncertainty is miscalibrated" or "there is a distribution shift", it fits every field and will retrieve the same few mechanism families every time — go one level down. These abstract forms are what you search with.
3. **Open the lever space.** Using the lever table in `references/thinking_traps.md` §1, write down for yourself at least three different levers that could plausibly close this gap, one line each ("`representation`: keep the per-token residual instead of the pooled state"). Include at least one lever that changes something the closest prior work treats as fixed — a frozen component, the task's interface, the problem formulation — unless `problem.md`'s Constraints rule it out. Skip any lever named in `AVOID_LEVER`.
4. **Hunt for mechanisms** (cross-domain regime, `retrieval.md` §2, within the search budget in §3). Cover at least two of your levers. List at least three distinct sub-fields that face one of your abstract challenges — this keeps you from defaulting to the field you already know — and query each. A mechanism from a field the near misses never cite often gives the strongest increment. Developing an in-domain idea further is also fine, as long as you can name the closest work and what you add beyond it. When improving a candidate, search only as much as the flagged weakness needs. If search is unavailable, you may draw on well-known mechanisms from other fields, but you must still read their source papers before citing them.
5. **Form ONE intuition.** Pick the single most promising mechanism, and choose on the merits: how much it would buy if it works and what it would unlock. Cost and ease of argument break ties; they don't decide. State it to yourself in one line, e.g. "multi-fidelity modeling learns an expensive model as a cheap model plus a learned discrepancy — draft that discrepancy instead of retraining the drafter", or "cascade rankers prune with cheap models first — rerank with a cheap verifier before calling the LLM". Then name its **core bet**: the one claim that, if wrong, leaves nothing worth publishing, and roughly what it buys on the problem's standard metric if it holds.
6. **Ground it.** Read, in parallel:
   - the source paper(s), with goals on the mechanism and *the condition it relies on* ("What makes this mechanism work?", "What assumption about the data/structure/signal does it need?");
   - the closest in-domain prior work you will compare against — the comparison must come from its body, not its abstract.

   This reading *is* your feasibility argument: the transfer is plausible if the condition the mechanism needs also holds (or can be made to hold) here. Check in particular that the target setting actually supplies what the mechanism consumes — a change detector built on registered image pairs needs some substitute for registration; a voting scheme needs sources that are actually independent. If it doesn't, say what replaces it. Don't invent a mechanism or a source; if a load-bearing part is unsourced, read the paper that would settle it.
7. **Append** to `candidates.md` (format in `schemas.md`). Keep each field short, plain-language and unambiguous:

```markdown
### C<n> — <short title>
- **Origin:** <system | user>
- **Intuition:** <one or two sentences a non-specialist in the source field could grasp>
- **Gap it attacks:** <the specific gap from gaps.md (or the challenge in problem.md), the concrete failure it addresses, and what closing it unlocks>
- **If improving prior candidate:** <only when applicable: C<x>, the weakness addressed, and what was added / replaced / removed>
- **Lever:** <the lever carrying the core bet, from thinking_traps.md §1> — alternatives considered: <lever>: <one line on why not>; <lever>: <one line on why not>
- **Core bet:** <the one claim that must hold; if it does, roughly what it buys on the problem's standard metric — a labelled guess, not a result>
- **Source inspiration:** <source [ids]; the mechanism or principle borrowed or developed, and why it works there, from what you read; novelty type: new-topic | recombination-of-distant-concepts | reinforcing-a-weak-connection | extension-or-deepening | fixing-a-shortcoming | reframing>
- **How it maps to this problem:** <what plays the role of what — conceptual, no pseudocode/equations/architecture/hyperparameters>
- **Why it could work:** <why it is plausible given the literature; the key assumption that must hold here>
- **Novelty vs. closest in-domain work:** <closest [id] and the specific increment over it — what is added or advanced, and why it matters>
- **Main risk:** <the single most likely reason the intuition is wrong or the transfer fails>
```

## Improving a candidate (`BUILD_ON`)

Rebuilds are where ideas quietly shrink: each objection gets answered by one more component, until the proposal is mostly guards around a small mechanism (trap T2). So before adding anything, ask whether the objection means the core bet is wrong or too weak. If it does, change the bet — replace the mechanism, or switch lever — rather than wrapping it.

- Prefer replacing or removing a component to adding one. Add **at most one** new component per rebuild; if the fix seems to need more, the candidate is probably the wrong shape — say so in **Main risk** and fix the shape instead.
- `FOCUS: ambition` — the reviewer found the core bet too small, buried under guards, or visible only on a metric the candidate defines for itself. Make the bet bigger or sharper: find the version of the mechanism that buys more on the standard metric, drop guards that exist only to answer earlier objections, or switch lever.
- `FOCUS: lever` — the reviewer named a different lever that would make this candidate unnecessary or dominates it. Either switch to that lever (a new intuition, still sourced and grounded), or keep yours with a concrete reason it wins on the merits — something it unlocks that the alternative can't. "Cheaper" or "fits the existing pipeline" alone doesn't carry it unless `problem.md` makes that a constraint.
- Other focuses: fix the named weakness; keep the rest.

Always fill **If improving prior candidate** with what was added, replaced and removed.

## User-idea mode (`USER_IDEA: yes`)

The user's idea in `problem.md` (`## User idea`) is the subject. Formalize it — don't replace it.

1. Read the idea and the papers it builds on or names (find them by search if only described), so the fields are grounded.
2. Write `C1` in the schema above, with `Origin: user`. Fill each field from the user's description. Where the user left something implicit, state the most natural reading and mark it `(inferred)`. Don't add components the user didn't propose, and don't swap the mechanism for one you prefer.
3. For **Lever**, name the lever the user's idea pulls and write `alternatives considered: n/a — user idea`. For **Core bet**, state the claim the idea stakes, marked `(inferred)` if the user didn't say it.
4. For **Source inspiration**, cite what the idea draws on. If it draws on nothing specific, write `user's own construction` — that's fine.
5. For **Novelty vs. closest in-domain work**, give your best initial comparison if you read a close paper. Otherwise write `to be assessed in the novelty survey`.

On a rebuild of a user idea (`BUILD_ON` with `Origin: user`), keep the user's core idea intact — even under `FOCUS: lever`, don't switch the user's lever; sharpen the argument for it instead. Change only what the review asked for — usually the positioning against the closest work, a component that doesn't hold up, or a sharper statement of the increment. Keep `Origin: user`, and say in **If improving prior candidate** exactly what changed relative to the user's original.

## Hard rules

- Stay within the per-call caps in your brief; when you reach them, write the candidate with what you have.
- Ideate from the literature. You may run **one** quick sanity check when a load-bearing assumption can be tested on a toy in minutes and the outcome would change the candidate — follow `references/sanity_checks.md` exactly (pre-register, 5-minute timeout). Don't use it to show the method works; that's the experiment plan's job.
- One candidate per call. The idea must be a **methodological contribution** (method, algorithm, model, training procedure, system) — not an analysis, benchmark, dataset, survey or position. A diagnosis can live inside the method as the hypothesis it exploits (trap T1).
- Cite only papers with digests in `papers/` (papers already cited in `gaps.md` have them).
- Name the competitor in the novelty line; "this is new" is not a comparison. But don't inflate a cosmetic difference into a contribution either.
- Don't write the formal method. If you find yourself writing equations, you've gone past the intuition.
- Provenance (why this candidate, what it builds on) goes in `plan.md`, which the orchestrator writes — not in `candidates.md`.

## Reply

One line: `C<n> created (new | improves C<x> | user idea formalized) [<lever>] — <the intuition sentence>`
