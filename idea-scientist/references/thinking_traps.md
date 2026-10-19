# Thinking traps and the lever space

An ideation pipeline built from LLM agents has predictable attractors. Each one is locally reasonable — it produces ideas that are feasible, defensible and easy to argue — which is exactly why reviews don't catch it: the review loop *rewards* defensibility. Left alone, a run drifts toward the same few idea shapes whatever the problem. This file names those shapes so every role can recognise them, and gives a shared vocabulary (the lever space) for asking "what else could close this gap?".

None of this is a ban. Each trap describes a pattern that is sometimes the right answer; the problem is reaching it by default rather than by comparison.

## Contents
1. The lever space
2. The traps: what each looks like, why agents fall into it, what to do instead
3. Who checks what

---

## 1. The lever space

A method closes a gap by changing something. The *lever* is the thing it changes, and it is the cheapest way to see whether a run keeps reaching for the same kind of fix.

| Lever | What the method changes | Examples of the move |
|---|---|---|
| `objective` | what is optimized, rewarded or credited | a new loss term, reward shaping, credit assignment, sample reweighting, a regularizer, a curriculum |
| `representation` | what the model encodes or conditions on | a different latent/state, tokenization, what history is kept, which features are exposed |
| `architecture` | structure built into the model | equivariance to a known symmetry, explicit memory, modularity, hard physical or logical constraints, routing |
| `data` | what data or supervision exists | targeted collection, simulation, synthetic data, augmentation, a new labeling or self-supervision signal |
| `inference` | what happens at test time | search, iterative refinement, test-time adaptation, amortized vs per-instance inference, decoding, filtering |
| `interface` | what the system observes, acts on or may ask | where to sense, a richer action space, queries to a tool or a person, a different input/output format |
| `formulation` | the mathematical problem itself | recast as an inverse problem, a game, a control or filtering problem, a matching problem — so a different toolbox applies |
| `systems` | how computation and memory are organised | caching and reuse, cascades of cheap-then-expensive models, approximation, scheduling, parallelism |

An idea often touches several levers; its lever is the one that carries the **core bet** — the claim that, if wrong, leaves nothing worth publishing. The table is a checklist for widening the search, not an ontology to argue over; if an idea fits none of these, name its lever in plain words.

## 2. The traps

### T1 — Diagnostic retreat

**Looks like:** the contribution is a finding. "We analyze / probe / characterize / benchmark…", or a "method" whose only output is a measurement.

**Why agents fall into it:** a measurement always produces a result, a new setting makes it look novel, it can't turn out wrong, and "let's first understand the cause" is the easiest reply to a reviewer who asks "how do you know?".

**Instead:** the skill only accepts methodological contributions. A diagnosis is welcome *inside* a method, as the hypothesis the method exploits: "if the failure comes from A, then doing B should fix it, and the gain should concentrate where A is strongest". The method's success then tests the diagnosis, which is worth more than the diagnosis alone.

### T2 — Armor over weapon

**Looks like:** each objection or failed toy check is answered by adding a component — a gate, a fallback, a monitor, a threshold, a calibration step. The selling point becomes "reduces to the baseline by construction". Half the predictions are of the form "no worse than the baseline". The gain shows only on a metric the proposal defines for itself. The limitations concede that the net gain may be small.

**Why agents fall into it:** once analysis is off the table, adding a guard is the cheapest answer to criticism, and every guard makes the idea more defensible. Each rebuild adds a layer, and nothing in the loop asks how much the core mechanism still buys after all the layers.

**Instead:** when an objection lands, first ask whether it means the core bet is wrong or too weak. If so, change the bet — replace the mechanism, switch lever — rather than wrapping it. Add at most one component per rebuild. Keep the core bet stated, and predict what it buys on the problem's *standard* metric. Guards are fine in moderation; real systems need them. They are just not the contribution, and a proposal whose modules are mostly guards has a small contribution.

### T3 — Single-lever fixation

**Looks like:** whatever the problem, the fix changes the `objective`: reshape the reward, reweight samples, add a credit term, add a regularizer. The same pull exists for whatever mechanism is fashionable (a diffusion model for everything, an LLM in the loop).

**Why agents fall into it:** changing the objective is the cheapest change that still counts as a method — no new architecture, data or compute. It is easy to argue ("the current objective omits a term"), hard to call a collision (the new term can be redefined for each setting), dense in recent literature, and the most visible knob whenever the setting already trains with RL.

**Instead:** before choosing, list at least three levers that could close the gap, search sources for at least two, and pick on the merits — upside, and what it unlocks if it works. "Cheaper" and "easier to argue" are tie-breakers, not reasons. Then ask: *would a different lever make this method unnecessary?* Example: if a detector misses small objects because its backbone has already downsampled them away, upweighting small-object examples in the loss (`objective`) can't recover them, while keeping high-resolution features (`representation`) removes the problem at its source. If such an alternative exists, the candidate must beat it on the merits or switch to it.

### T4 — Inherited constraints

**Looks like:** the problem came from one paper, and every candidate is "that paper plus a module": its frozen components stay frozen, its reward stays its reward, its benchmark defines success.

**Why agents fall into it:** the paper's design choices get copied into `problem.md` as if they were constraints. A paper's own limitations section lists what its authors could measure, which is often a symptom ("accuracy drops under shift") rather than the mechanism-level cause.

**Instead:** `Constraints` in `problem.md` lists only what the user stated or what is genuinely fixed (physics, budget, deployment). Everything else in the base paper may change. If the user did ask for a drop-in improvement, honor it — and say in the report what a version without that constraint could buy.

### T5 — Abstraction collapse

**Looks like:** the abstract challenge is so general that every field fits it: "the signal doesn't reach the decision", "the uncertainty is miscalibrated", "there is a distribution shift". Abstractions at this level retrieve the same few families every time — credit assignment, Bayesian uncertainty, domain adaptation — and the run ends up at T3.

**Instead:** abstract only as far as the structure stays specific: what information exists, where and at what cost; what is fixed and what is free; what symmetry, scale separation, sparsity or ordering the problem has. Write two abstractions from different angles — one about *information* (what is missing, where it could come from) and one about *structure* (what regularity is unexploited) — and search with both.

## 3. Who checks what

| Trap | Prevented by | Caught by |
|---|---|---|
| T1 diagnostic retreat | gap finder (methodological gaps only), innovator (methods only) | reviewer: contribution type |
| T2 armor over weapon | innovator: core bet, replace-before-add on rebuilds | reviewer: idea-shape audit → `revise(focus=ambition)`; report writer: prediction kinds |
| T3 single-lever fixation | innovator: lever space; orchestrator: `AVOID_LEVER` after a repeat | reviewer: dominating-lever question → `revise(focus=lever)`; `status.py` lever tally |
| T4 inherited constraints | orchestrator at intake | reviewer: dominating-lever question |
| T5 abstraction collapse | innovator: two abstractions | — |
