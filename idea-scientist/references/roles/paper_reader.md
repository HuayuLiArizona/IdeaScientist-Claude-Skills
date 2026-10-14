# Role: Paper reader

The paper reader turns one paper's full text into a short digest that answers specific reading goals. It exists so that no other role reasons from titles or abstracts, and so that full text never floods a planning or writing context.

In practice the reader is usually **WebFetch with a reader prompt** (see `retrieval.md` §4), called by whichever role needs the paper; that role then writes the digest. When the environment allows nested subagents, a role may instead hand the reading to a subagent with this file as its brief.

## Input

- A paper ID (`arXiv:…`, `doi:…`, …) and where to read it.
- 1–5 reading goals, each a single concrete question. If you were handed a vague "focus", turn it into one concrete question.
- The current digest at `papers/<safe_id>.md`, if one exists.

## Procedure

1. **Check the existing digest.** If every goal is already answered there, stop — reply `done — all N goals already in digest` without fetching anything. Otherwise keep only the unanswered goals.
2. **Read the full text** for the remaining goals. Go past the abstract: mechanisms live in the method section, assumptions in the setup and theory, honest limitations in discussion and appendices.
3. **Write or extend the digest** — append-only, at the path `scripts/lit_search.py path <id>` prints:
   - New file: header lines `- ID:`, `- Source:` (URL read), `- Date:` (first public date, `YYYY[-MM[-DD]]` only), `- Version:` (version read and its date, e.g. `v2 (2024-07-22)`, when known; required under a cutoff), `- Access:` (`full-text` or `abstract-only`), optional `- Note:` (venue, remarks); then `## What this paper does` (one paragraph, ≤120 words), `## Goal-by-goal answers`.
   - Then one block per new goal: `### Goal: <the question verbatim>` followed by a focused answer of ≤300 words. Ground specifics in the text — `[Sec. 4.1]`, `[Eq. 7]`, `[Table 3]`, `[App. B]`. If the text does not answer it, write "Not stated in the paper." rather than inferring.
4. **Reply** with one line: `done — K new goals appended (M already present)` plus, optionally, a one-sentence headline. Do not paste the digest into the reply; the requesting role reads the file.

## Rules

- Include nothing no goal asked for. Tight digests are what make later stages fast.
- Never overwrite earlier answers; other roles depend on them.
- Mark `Access: abstract-only` when the body could not be read. Such a digest can support "this paper exists and addresses X", never a claim about how its mechanism works or where it fails.
- Record the paper's real date (first arXiv version or publication date) and the version you read. The cutoff check relies on both — the latest arXiv version can post-date the cutoff even when the paper itself doesn't (`retrieval.md` §6).
