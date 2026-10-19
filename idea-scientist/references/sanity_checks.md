# Sanity checks: quick numerical tests during ideation

The innovator and the reviewer may run a small numerical experiment when it can quickly settle a question the literature can't. Example: "Does this transferred mechanism's key assumption actually hold on a toy instance of the target problem?" A two-minute toy that refutes an assumption can save a whole rebuild cycle.

Checks are a scalpel, not a lab. Unbounded checks are one of the ways a run turns into hours, so the limits below are firm.

## When to run one

Run a check only when all three hold:

1. **A crisp question.** Yes/no or a sign/threshold question about one load-bearing claim — the transfer assumption, a failure mode the reviewer suspects, whether an effect exists at all at toy scale. Not "does the method work?" (that's the experiment plan) and not tuning.
2. **Answerable in minutes.** A small, self-contained toy: synthetic data, a tiny model, a few hundred lines at most, CPU only.
3. **It would change a decision.** You can say beforehand which outcome would make you write the candidate differently (innovator) or change the verdict (reviewer). If both outcomes lead to the same decision, don't run it.

Toys are asymmetric evidence. A toy that breaks an assumption is fairly convincing; a toy that "works" only shows the idea isn't obviously broken. Prefer checks designed to *falsify*.

## Limits

| | quick | standard | deep |
|---|---|---|---|
| Checks per role call (innovator, reviewer) | 1 | 1 | 1 |
| Checks per run | 1 | 3 | 6 |

- Each check runs under a hard timeout: `timeout 300 python checks/K<n>.py`. If it times out, record it as inconclusive — don't enlarge the toy and retry.
- No dataset downloads, no GPU, no package installs beyond what's present. If numpy/scipy are missing, skip the check.
- One script, one run. Fixing an outright bug and re-running once is fine; iterating on the setup until it gives the answer you hoped for is not.
- `status.py` counts checks against the per-run limit. Once it's reached, no more checks.

## Protocol

1. **Pre-register.** *Before* writing code, append the entry to `checks.md` with the Question, Decision impact, and Prediction and kill criterion filled in, and Result left as `pending`. This keeps the reading honest: the criterion can't drift to fit the outcome.
2. **Write** the script to `checks/K<n>.py`: self-contained, fixed random seed, prints the numbers the criterion needs.
3. **Run** it with the timeout.
4. **Record** the outcome in the same entry, then use it: the innovator states the outcome in the candidate's *Why it could work* or *Main risk*; the reviewer cites it as `[check K<n>]` in Evidence.

```markdown
### K<n> — C<m> — <innovator | reviewer>
- **Question:** <the one claim being tested>
- **Decision impact:** <what you'd do differently under each outcome>
- **Prediction and kill criterion:** <expected outcome; the observation that would refute the claim>
- **Setup:** <toy problem, sizes, seed>
- **Result:** <the numbers, or "timed out" / "error">
- **Runtime:** <seconds>
- **Conclusion:** supports | refutes | inconclusive — <one sentence>
- **Script:** checks/K<n>.py
```

Number checks K1, K2, … across the whole run (look at `checks.md` for the next free number).

## How checks may be used later

- In `candidates.md` and `scores.md`: freely, as `[check K<n>]`, always described as a toy check.
- In `report.json`: never as a result or as evidence that the method works. The proposal stays results-masked. A check may motivate a falsifiable prediction ("the toy in K2 suggests the fold appears only when …; we predict …"), or a limitation. `render_report.py` adds an appendix that lists every check, labelled as toy checks run during ideation.
- In the final reply: mention checks that changed the direction.

When a check refutes a load-bearing claim, the natural reflex is to add a component that stops the failure from happening — a gate, a fallback, a margin. Sometimes that is right. But first ask what the refutation says about the core bet: if the toy shows the mechanism only helps when everything else is propped up around it, the bet is weaker than claimed, and the better next candidate changes the bet rather than adding the prop (`thinking_traps.md`, T2).
