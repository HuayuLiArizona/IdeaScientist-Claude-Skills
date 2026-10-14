# Attribution and license

This skill adapts the IdeaScientist ideation harness to Claude's skill format:

> Jiarui Liu, Renjie Tao, Yiwei Liao, et al. **IdeaScientist: Orchestrating Agents for Grounded Scientific Ideation.** arXiv:2610.04074, 2026.
> Code: https://github.com/jiarui-liu/IdeaScientist · Data: https://huggingface.co/datasets/Jerry999/SvalbardIdeaVault

The role instructions, artifact schemas, orchestration loop, validity gates and evaluation rubrics here are rewritten and adapted from that work's harness and paper appendix. The original repository is released under **CC BY-NC 4.0**, so this adaptation is shared under the same terms: attribution required, non-commercial use only.

## What changed from the original system

| Original | This skill |
|---|---|
| Orchestrator is a fixed LLM prompt in a Python runner | The orchestrator is Claude following `SKILL.md` |
| Roles run as separate model calls with tool allow-lists | Roles run as subagents with a role brief, or inline when subagents are unavailable |
| Offline Svalbard Idea Vault (4.7M papers, BM25 + embeddings) | Live web search by default; arXiv / Semantic Scholar / OpenAlex APIs or a local vault via `scripts/lit_search.py` when reachable |
| Paper reader as a single-turn model call over ≤30k tokens of full text | WebFetch with a reader prompt over the paper's full text, written to the same digest format |
| Gap finder, innovator and report writer trained with per-role GRPO LoRA adapters | No training; the same role contracts are followed by prompting |
| Reward validity gates computed in the training environment | `scripts/validate.py` applies the same structural and read-before-cite checks |
| Integer vault IDs | Prefixed IDs (`arXiv:`, `doi:`, `acl:`, …) |
