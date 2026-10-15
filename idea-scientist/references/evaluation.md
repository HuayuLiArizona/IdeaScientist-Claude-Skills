# Self-evaluation of a finished proposal

Which parts to run depends on depth: none for `quick`, §1 and §3 for `standard`, all four for `deep` — or all four whenever the user asks how good the idea is or wants to compare runs. Write results to `evaluation.md` in the run directory.

These rubrics follow the evaluation in the IdeaScientist paper (six proposal-quality dimensions, novelty against the closest work, structural cross-setting transfer, and mechanism non-obviousness). Treat the scores as diagnostics. In the paper, two human experts agreed with each other only at r≈0.56 on proposal quality, and the best LLM judges matched the human average about as well — useful signal, not ground truth. Judges also reward length and confident phrasing; score what is stated, not how it is said.

## 1. Proposal quality (1–10 each)

Shared anchors: 1–2 seriously deficient · 3–4 major gaps · 5–6 partly adequate, consequential gaps · 7–8 strong, limited gaps · 9–10 exceptionally strong and well supported by the text.

Score from the proposal alone (except relevance), and give one sentence of reasoning per dimension.

| Dimension | Question |
|---|---|
| Relevance | Judged against `problem.md`: does the proposal squarely target *this* problem and challenge, or drift to an easier neighbour? |
| Clarity | Is it organized and unambiguous; are claims and contributions stated cleanly? |
| Specificity | Concrete mechanisms, objectives, named datasets/baselines/metrics — or generic? |
| Actionability | Could a competent researcher start implementing and running the evaluation from this? |
| Soundness | Is the reasoning internally consistent; are assumptions explicit and failure modes acknowledged, with no over-claiming? |
| Impact | If it works, how much does it matter to the field? |

## 2. Novelty against the closest work (1–10)

Gather the closest prior work: the near misses in `gaps.md`, the closest in-domain paper named by the innovator, close hits from the reviewer, plus a fresh same-problem search for the proposal's *central mechanism applied to this problem* (read anything close). Then ask what the proposal adds beyond them.

Anchors: 1–2 essentially the same central mechanism as an existing paper · 3–4 minor adaptation or obvious combination · 5–6 a distinct step with substantial overlap · 7–8 materially different · 9–10 strongly distinct. List the overlapping prior work by ID. Novelty by renaming or jargon doesn't count.

Score the size and clarity of the *increment*, not the absence of precedent. An extension, a deepening, a fix for a concrete shortcoming, or a reframing that produces a more complete story can score 7+ if what it adds is clear and matters. Reserve 1–2 for genuine collisions: same problem, same key method, same main contribution.

If a literature cutoff was set, you can score twice: against pre-cutoff work only, and against everything including later work — the second tells you whether the field later went this way.

## 3. Structural cross-setting transfer (0 or 1)

Score 1 only if the proposal does all four:
1. names a source setting different from the target setting;
2. imports a concrete mechanism, abstraction or analysis technique from it (citing a paper or using a generic tool doesn't count);
3. identifies the shared underlying structure that explains why the mechanism should transfer;
4. specifies how the mechanism is adapted to exploit that structure in the target.

Support a 1 with one short quote from the proposal. Otherwise 0 — including superficial analogies that name another field without the shared structure and adaptation. Record source setting, target setting, mechanism, shared structure, adaptation.

## 4. Mechanism non-obviousness (two separate passes)

Could a competent researcher have derived the central mechanism from the nearest prior work and standard techniques? This must be done **blind**: whoever derives the baseline candidates must never see the proposal, or they will reverse-engineer a derivation from the answer.

**Pass A — blind derivation (a fresh subagent that has not seen `report.json`, `candidates.md` or `scores.md`).** Give it only `problem.md` and the digests of the three nearest prior papers on the mechanism side. Ask for up to three concrete candidate mechanisms that address the challenge, each with: its central technical operation, step-by-step derivation from the supplied papers and standard techniques, which paper supplies each non-standard step, and the key assumption. No broad research directions; an empty list is allowed. Save its output verbatim to `evaluation_blind_candidates.json`.

**Pass B — comparison against the frozen list.** Now read the proposal. State its central technical operation in one sentence, compare it against every frozen candidate (no inventing, repairing or merging candidates after seeing the proposal), list shared steps and consequential missing steps, and assign one level:

| Level | Meaning | Score |
|---|---|---|
| trivial_combination | a candidate already contains the central mechanism | 0 |
| routine_extension | a candidate reaches it with only ordinary implementation steps | 1/3 |
| non_obvious_step | every candidate misses a consequential step or structural observation the proposal supplies | 2/3 |
| surprising | the missing step also runs against an expectation the supplied papers establish | 1 |

Use the upper levels only if you can name the missing step. If Pass A produced nothing usable, mark it unscored.

Without subagents you cannot run Pass A blind — skip this metric and say why, rather than reporting a contaminated score.

## evaluation.md format

```markdown
# Evaluation of <title>

## Proposal quality
| Dimension | Score | Reason |
|---|---|---|
| Relevance | 8 | … |
…
| **Average** | 7.3 | |

## Novelty vs. closest work
Score: 7 — <reason>. Overlaps: [id], [id].

## Cross-setting transfer
Score: 1 — source: …; target: …; mechanism: …; shared structure: …; adaptation: …
Quote: "…"

## Mechanism non-obviousness
Level: non_obvious_step (0.67) — closest blind candidate C2; missing step: …

## Caveats
<self-judged; single judge; what would change the scores>
```
