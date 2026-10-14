#!/usr/bin/env python3
"""Render report.json into a readable report.md with a numbered, linked reference list.

Usage:
    python render_report.py <run_dir> [--out report.md] [--language en|zh] [--keep-ids]

Inline citations like [arXiv:1706.02093] become [1], [2], … in order of first
appearance; the reference list is built from the digests in papers/ (title, date,
link). --keep-ids leaves the raw IDs inline. Section headings follow the run's
output language (from problem.md) unless --language is given.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _ids import canonical, digest_path, extract_ids, read_digest_meta, url_for  # noqa: E402

H = {
    "en": {
        "topic": "Topic", "focus": "Focus", "problem": "Core problem", "why": "Why it matters",
        "example": "Concrete failing example", "novelty": "Key novelty", "definition": "Problem definition",
        "setting": "Formal setting", "inputs": "Inputs", "outputs": "Outputs", "terms": "Key terms",
        "related": "Related work", "gap": "Open gap", "method": "Method", "flow": "High-level flow",
        "modules": "Modules", "role": "Role", "model": "Model", "in": "Inputs", "out": "Outputs", "notes": "Notes",
        "elements": "Novel architectural elements", "choices": "Design choices", "theory": "Theoretical grounding",
        "pseudo": "Core algorithm", "training": "Model and training", "base": "Base model",
        "tmethod": "Training method", "objectives": "Objectives", "adaptation": "Adaptation",
        "hyper": "Key hyperparameters", "sota": "Comparison to the state of the art", "evaluation": "Proposed evaluation",
        "esetting": "Setting", "benchmarks": "Benchmarks", "new": "newly constructed", "baselines": "Baselines",
        "metrics": "Metrics", "ablations": "Ablations", "predictions": "Falsifiable predictions",
        "pillar": "Pillar", "prediction": "Prediction", "kill": "Falsified if", "limitations": "Limitations",
        "refs": "References", "abstract_only": "abstract only",
        "footer": "Generated with the idea-scientist skill. "
                  "Intermediate artifacts — gaps.md, candidates.md, scores.md, papers/ — are in the run directory. "
                  "This is an unexecuted research proposal: every prediction is untested.",
    },
    "zh": {
        "topic": "方向", "focus": "关注点", "problem": "核心问题", "why": "为什么重要",
        "example": "具体失败案例", "novelty": "核心创新", "definition": "问题定义",
        "setting": "形式化设定", "inputs": "输入", "outputs": "输出", "terms": "关键术语",
        "related": "相关工作", "gap": "未解决的缺口", "method": "方法", "flow": "整体流程",
        "modules": "模块", "role": "作用", "model": "模型", "in": "输入", "out": "输出", "notes": "说明",
        "elements": "新的结构设计", "choices": "关键设计选择", "theory": "理论依据",
        "pseudo": "核心算法", "training": "模型与训练", "base": "基座模型",
        "tmethod": "训练方式", "objectives": "目标函数", "adaptation": "适配方式",
        "hyper": "关键超参数", "sota": "与现有方法的比较", "evaluation": "评估计划",
        "esetting": "评估设定", "benchmarks": "基准", "new": "新构建", "baselines": "基线方法",
        "metrics": "指标", "ablations": "消融实验", "predictions": "可证伪的预测",
        "pillar": "检验对象", "prediction": "预测", "kill": "证伪条件", "limitations": "局限性",
        "refs": "参考文献", "abstract_only": "仅摘要",
        "footer": "由 idea-scientist skill 生成。"
                  "中间产物 gaps.md、candidates.md、scores.md、papers/ 均在运行目录中。"
                  "本文是尚未执行的研究提案，所有预测均未经实验验证。",
    },
}


def _lang_from_problem(run: Path) -> str:
    p = run / "problem.md"
    if p.exists():
        m = re.search(r"Output language:\s*([A-Za-z\-]+)", p.read_text(encoding="utf-8"))
        if m and m.group(1).lower().startswith("zh"):
            return "zh"
    return "en"


class Cite:
    def __init__(self, keep_ids: bool):
        self.order: list[str] = []
        self.keep = keep_ids

    def sub(self, text) -> str:
        if not isinstance(text, str):
            text = "" if text is None else str(text)

        def repl(m: re.Match) -> str:
            ids = extract_ids(m.group(0))
            if not ids:
                return m.group(0)
            nums = []
            for pid in ids:
                if pid not in self.order:
                    self.order.append(pid)
                nums.append(str(self.order.index(pid) + 1))
            return "[" + ", ".join(ids) + "]" if self.keep else "[" + ", ".join(nums) + "]"

        return re.sub(r"\[[^\[\]\n]{3,400}\]", repl, text)


def _lst(x) -> list:
    if x is None:
        return []
    return x if isinstance(x, list) else [x]


def render(data: dict, run: Path, lang: str, keep_ids: bool) -> str:
    h = H[lang]
    c = Cite(keep_ids)
    out: list[str] = []
    w = out.append

    w(f"# {c.sub(data.get('title', ''))}\n")
    if data.get("one_sentence_thesis"):
        w(f"> {c.sub(data['one_sentence_thesis'])}\n")
    tr = data.get("topic_relevance") or {}
    if tr:
        w(f"**{h['topic']}:** {' · '.join(map(c.sub, _lst(tr.get('sub_topic'))))}  ")
        w(f"**{h['focus']}:** {' · '.join(map(c.sub, _lst(tr.get('primary_focus'))))}\n")

    cp = data.get("core_problem") or {}
    w(f"## 1. {h['problem']}\n")
    w(c.sub(cp.get("problem_statement")) + "\n")
    if cp.get("why_it_matters"):
        w(f"**{h['why']}**\n")
        w("\n".join(f"- {c.sub(x)}" for x in _lst(cp["why_it_matters"])) + "\n")
    if cp.get("concrete_example"):
        w(f"**{h['example']}:** {c.sub(cp['concrete_example'])}\n")

    kn = data.get("key_novelty") or {}
    w(f"## 2. {h['novelty']}: {c.sub(kn.get('main_idea'))}\n")
    w("\n".join(f"- {c.sub(x)}" for x in _lst(kn.get("explanation"))) + "\n")

    pd = data.get("problem_definition") or {}
    w(f"## 3. {h['definition']}\n")
    w(f"- **{h['setting']}:** {c.sub(pd.get('formal_setting'))}")
    w(f"- **{h['inputs']}:** {c.sub(pd.get('inputs'))}")
    w(f"- **{h['outputs']}:** {c.sub(pd.get('outputs'))}\n")

    kt = data.get("key_terms") or {}
    if kt:
        w(f"## 4. {h['terms']}\n")
        w("\n".join(f"- **{k}** — {c.sub(v)}" for k, v in kt.items()) + "\n")

    w(f"## 5. {h['related']}\n")
    for rw in _lst(data.get("related_work")):
        if not isinstance(rw, dict):
            continue
        body = rw.get("what_it_does") or ""
        inline = set(extract_ids(body if isinstance(body, str) else ""))
        extra = [canonical(x) for x in _lst(rw.get("citations")) if isinstance(x, str) and canonical(x)]
        cites = "".join(f"[{x}]" for x in dict.fromkeys(extra) if x not in inline)
        w(f"### {c.sub(rw.get('sub_area'))}\n")
        w(c.sub(body) + (f" {c.sub(cites)}" if cites else "") + "\n")
        w(f"*{h['gap']}:* {c.sub(rw.get('open_gap'))}\n")

    m = data.get("method") or {}
    w(f"## 6. {h['method']}\n")
    if m.get("high_level_flow"):
        w(f"**{h['flow']}**\n")
        w("\n".join(f"- {c.sub(x)}" for x in _lst(m["high_level_flow"])) + "\n")
    if m.get("modules"):
        w(f"### {h['modules']}\n")
        for mod in _lst(m["modules"]):
            if not isinstance(mod, dict):
                continue
            w(f"**{c.sub(mod.get('module'))}** — {c.sub(mod.get('role'))}  ")
            if mod.get("model"):
                w(f"{h['model']}: {c.sub(mod['model'])}  ")
            if mod.get("inputs") or mod.get("outputs"):
                w(f"{h['in']}: {', '.join(map(c.sub, _lst(mod.get('inputs'))))} → "
                  f"{h['out']}: {', '.join(map(c.sub, _lst(mod.get('outputs'))))}  ")
            if mod.get("notes"):
                w(f"{h['notes']}: {c.sub(mod['notes'])}")
            w("")
    for key, label in (("novel_architectural_elements", "elements"), ("design_choices", "choices")):
        if m.get(key):
            w(f"### {h[label]}\n")
            w("\n".join(f"- {c.sub(x)}" for x in _lst(m[key])) + "\n")
    if m.get("theoretical_grounding"):
        w(f"### {h['theory']}\n")
        w(c.sub(m["theoretical_grounding"]) + "\n")
    if m.get("pseudocode"):
        code = str(m["pseudocode"]).strip().strip("`")
        w(f"### {h['pseudo']}\n")
        w("```\n" + code + "\n```\n")

    md = data.get("model_details") or {}
    tr_ = md.get("training") or {}
    w(f"## 7. {h['training']}\n")
    w(f"- **{h['base']}:** {c.sub(md.get('base_model'))}")
    w(f"- **{h['tmethod']}:** {c.sub(tr_.get('method'))}")
    w(f"- **{h['adaptation']}:** {c.sub(tr_.get('adaptation'))}")
    if tr_.get("objective_functions"):
        w(f"- **{h['objectives']}:**")
        w("\n".join(f"  - {c.sub(x)}" for x in _lst(tr_["objective_functions"])))
    hp = tr_.get("key_hyperparameters") or {}
    if hp:
        w(f"- **{h['hyper']}:** " + "; ".join(f"{k} = {c.sub(v)}" for k, v in hp.items()))
    w("")

    cs = data.get("comparison_to_sota") or {}
    w(f"## 8. {h['sota']}\n")
    w("\n".join(f"- {c.sub(x)}" for x in _lst(cs.get("key_differences"))) + "\n")
    if cs.get("related_methods"):
        w("\n".join(f"  - {c.sub(x)}" for x in _lst(cs.get("related_methods"))) + "\n")

    ev = data.get("proposed_evaluation") or {}
    w(f"## 9. {h['evaluation']}\n")
    w(f"**{h['esetting']}:** {c.sub(ev.get('evaluation_setting'))}\n")
    if ev.get("benchmarks"):
        w(f"**{h['benchmarks']}**\n")
        for b in _lst(ev["benchmarks"]):
            if isinstance(b, dict):
                tag = f" ({h['new']})" if b.get("newly_constructed") else ""
                w(f"- {c.sub(b.get('name'))} — {c.sub(b.get('task_type'))}{tag}")
            else:
                w(f"- {c.sub(b)}")
        w("")
    for key, label in (("baselines", "baselines"), ("main_metrics", "metrics"), ("ablations", "ablations")):
        if ev.get(key):
            w(f"**{h[label]}**\n")
            w("\n".join(f"- {c.sub(x)}" for x in _lst(ev[key])) + "\n")

    fp = _lst(data.get("falsifiable_predictions"))
    if fp:
        w(f"## 10. {h['predictions']}\n")
        w(f"| {h['pillar']} | {h['prediction']} | {h['kill']} |\n|---|---|---|")
        for p in fp:
            if isinstance(p, dict):
                cells = [c.sub(p.get(k)).replace("|", "\\|").replace("\n", " ")
                         for k in ("pillar", "prediction", "kill_condition")]
                w("| " + " | ".join(cells) + " |")
        w("")

    w(f"## 11. {h['limitations']}\n")
    w("\n".join(f"- {c.sub(x)}" for x in _lst(data.get("limitations"))) + "\n")

    if c.order:
        w(f"## {h['refs']}\n")
        for i, pid in enumerate(c.order, 1):
            meta = read_digest_meta(digest_path(run, pid))
            title = meta["title"] or pid
            date = f" ({meta['date_clean']})" if meta["date_clean"] else ""
            if meta["note"]:
                date += f". {meta['note']}"
            url = url_for(pid) or meta["source"] or ""
            access = f" — {h['abstract_only']}" if (meta["access"] or "").lower().startswith("abstract") else ""
            link = f" <{url}>" if url else ""
            missing = "" if digest_path(run, pid).exists() else " ⚠ no digest"
            w(f"{i}. {title}{date}. `{pid}`.{link}{access}{missing}")
        w("")

    w("---\n")
    w(f"*{h['footer']}*")
    return "\n".join(out).rstrip() + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_dir")
    ap.add_argument("--out", default=None, help="output path (default <run_dir>/report.md)")
    ap.add_argument("--language", choices=["en", "zh"], default=None)
    ap.add_argument("--keep-ids", action="store_true")
    args = ap.parse_args()

    run = Path(args.run_dir)
    src = run / "report.json"
    if not src.exists():
        print(f"error: {src} not found", file=sys.stderr)
        return 2
    try:
        data = json.loads(src.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"error: report.json is not valid JSON: {exc}", file=sys.stderr)
        return 2
    lang = args.language or _lang_from_problem(run)
    md = render(data, run, lang, args.keep_ids)
    out = Path(args.out) if args.out else run / "report.md"
    out.write_text(md, encoding="utf-8")
    print(f"wrote {out} ({len(md):,} chars)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
