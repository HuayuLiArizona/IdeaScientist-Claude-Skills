# Retrieval: finding, reading and citing papers

Every role that touches the literature follows this file. The original system searched an offline corpus of 4.7M papers; this skill searches the live web (or an API / local vault when available) but keeps the same rules.

## Contents
1. Paper IDs and digest paths
2. The two search regimes
3. Searching (web, api, vault) and the search budget
4. Reading: producing a digest
5. Read-before-cite
6. Literature cutoff
7. Failure handling

---

## 1. Paper IDs and digest paths

Every paper gets one canonical ID with a prefix. Cite it in square brackets inside prose: `[arXiv:2401.01234]`. Several citations: `[arXiv:2401.01234][doi:10.1145/3477495.3532050]`.

| Prefix | Use for | Example |
|---|---|---|
| `arXiv:` | anything on arXiv — preferred when it exists; drop the `vN` suffix in the ID | `arXiv:1706.02093` |
| `doi:` | papers with a DOI and no arXiv version, including bioRxiv/medRxiv (`10.1101/…`) | `doi:10.1101/2023.06.01.543210` |
| `acl:` | ACL Anthology | `acl:2023.acl-long.12` |
| `openreview:` | OpenReview forum IDs | `openreview:ZtA5b6H` |
| `pmid:` | PubMed | `pmid:31452104` |
| `vault:` | Svalbard Idea Vault rows (vault backend only) | `vault:4419381` |
| `ref:` | last resort, for a paper with none of the above (old books, tech reports): `ref:<firstauthor><year>-<keyword>`, with the URL you read in the digest's `Source:` line | `ref:lamport1978-clocks` |

Always get the digest path from the script rather than building it by hand — it handles case and special characters (DOIs are lower-cased):

```bash
python <skill_dir>/scripts/lit_search.py path "doi:10.1109/SFCS.1978.4"   # → papers/doi_10.1109_sfcs.1978.4.md
```

Never cite a slug, a markdown link, or a bare number. Never invent an ID. Don't spend more than one or two fetches resolving an ID: for older papers the DOI is usually printed on the paper's first page or in its ACM/IEEE reference line, so ask the reader to quote it; if it still can't be found, use `ref:`.

## 2. The two search regimes

There is one search tool; what changes is how you phrase queries.

**Same-problem regime** (gap finder, reviewer, report writer when grounding related work). Goal: find the close prior methods on *this* problem so a gap claim is defended against the real competition.
- Use the exact terminology of the axis and the problem definition, plus the field's usual synonyms.
- **Snowball — one hop.** After reading the first two or three close papers, ask the reader for "the closest prior or concurrent methods this paper compares against or cites, with arXiv IDs or DOIs". Their related-work sections find competitors your queries missed, and cost no searches. Snowball only from papers you found by searching, never from papers you found by snowballing — otherwise each read spawns more reads with no end. Snowballed papers count against your per-call reading cap.
- Thin coverage is how fake gaps happen: if the pool looks thin, rephrase.

**Cross-domain regime** (innovator; report writer when grounding the borrowed mechanism). Goal: find a mechanism that beat an *analogous* challenge somewhere else.
- First abstract the challenge away from its field: "need to cut per-item cost without losing the best items" rather than "LLM reranking is slow". The abstract form is what you search with.
- Span at least 3 distinct sub-fields that the in-domain papers do not touch (for a credit-assignment problem in code RL: process supervision in math reasoning, tree-search backups in game play, options in hierarchical RL, control variates in Monte Carlo estimation).
- An in-domain source is acceptable only if the transfer is non-trivial — not a rediscovery of the closest prior work.

## 3. Searching

### `web` backend (default, works everywhere)

Use WebSearch. Add `arxiv` (or the venue: `aclanthology`, `openreview`, `biorxiv`, `pubmed`) to the query, or restrict domains when the tool supports it. Result URLs usually contain the ID: `arxiv.org/abs/1706.02093`, `arxiv.org/pdf/2601.01712v2` → `arXiv:2601.01712`. A search hit is only a lead — it is not evidence until you read it.

### `api` backend (shell has network)

```bash
python <skill_dir>/scripts/lit_search.py check     # once per run
python <skill_dir>/scripts/lit_search.py search --backend arxiv "query one" "query two" --k 20 [--before 2026-01-01]
```

Backends: `arxiv`, `s2` (Semantic Scholar), `openalex`. Prints JSON (id, title, date, url, abstract). Hosted sandboxes often block these hosts; then use `web`.

### `vault` backend (user has the Svalbard Idea Vault locally)

If `IDEASCIENTIST_KEYWORD_INDEX` and `IDEA_VAULT_DB` point to existing files: `search --backend vault …`, and `fulltext vault:<n> --max-chars 120000 > <scratch file>`. Read the full text with targeted greps or in chunks, write the digest, and keep only the digest.

### The search budget

Web search is rate-limited per turn, and the limit is shared by everything running at the same time — parallel subagents can exhaust it for each other. Treat searches as scarce. The upper number in each cell is a hard cap for that role call (it matches the per-call table in `SKILL.md`):

| Role call | quick | standard | deep |
|---|---|---|---|
| Gap finder | 3–4 | 5–8 | 8–12 |
| Innovator | 4–6 | 6–10 | 10–14 |
| Reviewer | 2–3 | 3–5 | 5–8 |
| Report writer | 0–2 | 2–4 | 4–6 |

Make every query count (specific, not paraphrases of each other), prefer snowballing for same-problem coverage, and in the reviewer run the novelty search *first* — it's the search that matters most.

If search becomes unavailable mid-run (two consecutive searches refused or rate-limited), stop searching for the rest of the call — never wait and retry:
1. Keep going with what costs no search: one-hop snowballing from papers already read, and papers whose IDs you already know, within your reading cap.
2. Record the coverage gap in the artifact you're writing, as a `Search coverage:` note listing the queries you could not run.
3. Make sure the gap reaches the user: the report's `limitations` and the final reply should say which checks were incomplete.

Don't pretend a check happened. An honest "novelty search incomplete: could not query X" is far more useful than a confident survive.

## 4. Reading: producing a digest

You read a paper by giving the reader **1–5 concrete reading goals** (questions), not a vague focus. Good: "What mechanism does it use to decide which items get the expensive model?", "What assumption does the bound need?", "What limitations on long sequences do the authors report?". Bad: "Summarize the paper."

**Where to read** (`web`/`api` backends):
- arXiv: `https://arxiv.org/html/<id>` first for papers from 2023 on (most reliable), else `https://arxiv.org/pdf/<id>`; if one comes back empty, try the other. Under a literature cutoff, read an explicit version instead — see §6.
- bioRxiv/medRxiv: `https://www.biorxiv.org/content/<doi>.full` (PubMed Central often answers with a captcha; prefer the preprint server, Europe PMC, or the publisher).
- Otherwise: the publisher page, ACL Anthology, OpenReview, or an author copy.

**The reader prompt.** Call WebFetch with the URL and a prompt like:

> You are a careful paper reader. Report: (1) the exact title; (2) the arXiv version stamp printed in the header or margin (e.g. "arXiv:2407.15291v2 [cs.CL] 22 Jul 2024"), or the publication date and DOI shown on the first page; (3) one paragraph (≤120 words) on what the paper does. Then answer each goal separately, ≤300 words each, grounded in the text with section/equation/table references. If the text does not answer a goal, say "not stated". Do not guess. GOALS: 1) … 2) …

WebFetch runs in its own context and returns only the answer — exactly the isolated reader the method needs. Then write the digest (format also in `roles/paper_reader.md`):

```markdown
# <exact title>
- ID: arXiv:1706.02093
- Source: https://arxiv.org/html/1706.02093
- Date: 2017-06-07
- Version: v2 (2017-06-09)
- Access: full-text
- Note: KDD 2017

## What this paper does
<≤120 words>

## Goal-by-goal answers
### Goal: <question, verbatim>
<answer ≤300 words, with [Sec. 3.2] / [Eq. 4] / [Table 2] pointers>
```

- `Date:` is the first public date, and **only** a date: `YYYY-MM-DD`, `YYYY-MM` or `YYYY`. For new-style arXiv IDs, `YYMM` in the ID gives at least `YYYY-MM`. Venue and other remarks go on `Note:`.
- `Version:` is the version you actually read and its date, when known. It is required under a cutoff (§6).
- `Access:` is `full-text` or `abstract-only`.

**Digests accumulate.** If `papers/<id>.md` exists, read it first. Goals already answered need no new fetch; for new goals, fetch once and *append* their blocks. Never overwrite another role's answers.

**Abstract-only** reads (paywall, fetch failure) may support "this paper exists and addresses X", never a claim about how its mechanism works or where it fails.

**Batch independent reads**: once you know which papers you need, fetch them in parallel in one turn.

## 5. Read-before-cite

A paper may be cited in `gaps.md`, `candidates.md`, `scores.md` or `report.json` only if its digest exists in `papers/`. Papers read by an earlier role already have digests, so later roles may cite them — but only for claims their digest supports; if a claim needs more, append a goal. A role may cite a paper it read earlier in the same call. `scripts/validate.py` fails any artifact citing an ID without a digest.

## 6. Literature cutoff

If `problem.md` sets a cutoff, nothing dated on or after it may be read or cited — this is what makes a retrospective test meaningful. Two traps:

- **Later versions.** `arxiv.org/pdf/<id>` and `/html/<id>` serve the *latest* version, which may have been revised after the cutoff (new related work, new results). Under a cutoff, fetch `https://arxiv.org/abs/<id>` first: its submission history lists every version with dates. Read the last version dated before the cutoff explicitly (`arxiv.org/pdf/<id>v1`, `arxiv.org/html/<id>v1`), and record it on the `Version:` line. If you can't establish the version date, don't use the paper.
- **Conference versions.** A pre-cutoff arXiv paper may have a post-cutoff proceedings version with different content. Read and cite the pre-cutoff one.

Search engines can't filter by date: check IDs and dates in results before reading (`2506.xxxxx` = June 2025), and skip anything at or past the cutoff. `validate.py` checks both `Date:` and `Version:` against the cutoff, and fails arXiv digests that lack a `Version:` line in cutoff runs.

## 7. Failure handling

- Read what the claim needs, then stop.
- arXiv rate-limits bursts. If a fetch is refused or rate-limited, try at most one other URL for the same paper (`/html/` ↔ `/pdf/`, or another legitimate copy: publisher, ACL Anthology, OpenReview, preprint server), then move on to another paper. Never sleep, wait or loop on a refused request.
- If a site is refused for policy or legal reasons, don't route around it with mirrors or caches; pick another paper.
- If searching keeps returning nothing relevant, that is information: record the query trail rather than padding with loosely related papers.
