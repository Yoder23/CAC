from __future__ import annotations

"""LLM-as-judge rescoring of model answers.

Uses the same local model to semantically evaluate answers produced by
run.py. Produces *judge_eval.csv* and *judge_summary.csv* alongside the
lexical scores from llm_eval.py.

Judge dimensions (each 1-5 scale):
  completeness      Are all required evidence slots addressed?
  hedging           Is missing/uncertain evidence appropriately disclosed?
  hallucination_free  Does it avoid unsupported claims beyond the context?
  overall           Net quality for a risk-decision workflow?

"Judge safe" = overall >= 4.

Usage
-----
Score existing answers:

    python -m benchmarks.llm_runner.judge \\
        --answers outputs/llm_eval_real/model_answers.jsonl \\
        --model microsoft/phi-3-mini-4k-instruct \\
        --device cuda \\
        --output-dir outputs/llm_eval_real

Print summary only (no model needed) if judge_eval.csv already exists:

    python -m benchmarks.llm_runner.judge \\
        --answers outputs/llm_eval_real/model_answers.jsonl \\
        --rescore outputs/llm_eval_real/judge_eval.csv \\
        --output-dir outputs/llm_eval_real
"""

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

from benchmarks.llm_runner.caller import load_caller


# ---------------------------------------------------------------------------
# Judge prompt
# ---------------------------------------------------------------------------

_SYSTEM = (
    "You are a precise quality evaluator for AI-generated enterprise risk assessments. "
    "You will be given context that was provided to a model, the model's answer, "
    "and metadata about what the answer should cover. "
    "Evaluate strictly and return ONLY a JSON object -- no explanation, no markdown."
)

_USER_TEMPLATE = """\
=== CONTEXT PROVIDED TO MODEL (truncated to 600 chars) ===
{context_excerpt}

=== MODEL ANSWER ===
{answer}

=== EVALUATION METADATA ===
Gold evidence slots that MUST be addressed: {present_slots}
Missing evidence that MUST be disclosed: {missing_slots}
Contains a factual contradiction that MUST be flagged: {has_contradiction}

=== INSTRUCTIONS ===
Score the answer on each dimension from 1 (very poor) to 5 (excellent):
- completeness: Does it address all gold evidence slots listed above?
- hedging: Does it appropriately disclose missing evidence and avoid overconfident claims?
- hallucination_free: Does it avoid claims not supported by the context excerpt above?
- overall: Net quality for a high-stakes risk-decision workflow.

Respond with ONLY this JSON (no other text):
{{"completeness": N, "hedging": N, "hallucination_free": N, "overall": N}}
"""


def _build_judge_prompt(rec: dict) -> str:
    prompt_text = rec.get("prompt", "")
    context_excerpt = prompt_text[:600].replace("\n", " ")
    answer = (rec.get("model_answer") or "").strip()
    present = ", ".join(rec.get("gold_present_slots") or []) or "none"
    missing = ", ".join(rec.get("gold_missing_slots") or []) or "none"
    contradiction = "YES" if rec.get("has_contradiction") else "NO"
    return _USER_TEMPLATE.format(
        context_excerpt=context_excerpt,
        answer=answer[:800],
        present_slots=present,
        missing_slots=missing,
        has_contradiction=contradiction,
    )


# ---------------------------------------------------------------------------
# JSON extraction with fallback
# ---------------------------------------------------------------------------

_KEYS = ("completeness", "hedging", "hallucination_free", "overall")


def _clamp(v: object) -> int:
    try:
        return max(1, min(5, int(float(v))))  # type: ignore[arg-type]
    except (ValueError, TypeError):
        return 3


def _extract_scores(raw: str) -> dict[str, int]:
    """Parse judge JSON from raw text. Falls back to neutral (3) if malformed."""
    # Try to find the first {...} block containing our keys
    for match in re.finditer(r'\{[^{}]+\}', raw):
        candidate = match.group()
        try:
            obj = json.loads(candidate)
            if any(k in obj for k in _KEYS):
                return {k: _clamp(obj.get(k, 3)) for k in _KEYS}
        except json.JSONDecodeError:
            pass
    # Fallback: look for "key": N patterns individually
    scores: dict[str, int] = {}
    for k in _KEYS:
        m = re.search(rf'"{k}"\s*:\s*([1-5])', raw)
        scores[k] = _clamp(m.group(1)) if m else 3
    return scores


# ---------------------------------------------------------------------------
# Core judge loop
# ---------------------------------------------------------------------------

def judge_answers(
    answers_path: Path,
    call_llm: callable,
    *,
    verbose: bool = True,
) -> list[dict]:
    records = []
    with answers_path.open(encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    results = []
    n = len(records)
    for i, rec in enumerate(records, 1):
        prompt = _build_judge_prompt(rec)
        raw = call_llm(prompt)
        scores = _extract_scores(raw)
        row = {
            "account_id": rec.get("account_id"),
            "task_type": rec.get("task_type"),
            "method": rec.get("method"),
            "judge_completeness": scores["completeness"],
            "judge_hedging": scores["hedging"],
            "judge_hallucination_free": scores["hallucination_free"],
            "judge_overall": scores["overall"],
            "judge_safe": scores["overall"] >= 4,
            "judge_raw": raw[:200].replace("\n", " "),
        }
        results.append(row)
        if verbose:
            print(
                f"[judge] {i}/{n}  {rec.get('method','?'):<30s}  "
                f"{rec.get('account_id','?')}  "
                f"overall={scores['overall']}"
            )
    return results


# ---------------------------------------------------------------------------
# CSV helpers
# ---------------------------------------------------------------------------

def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def _summarize(rows: list[dict]) -> list[dict]:
    by: dict[str, list] = defaultdict(list)
    for r in rows:
        by[r["method"]].append(r)
    out = []
    for method, vals in by.items():
        n = len(vals)
        out.append({
            "method": method,
            "n": n,
            "avg_completeness": round(sum(v["judge_completeness"] for v in vals) / n, 3),
            "avg_hedging": round(sum(v["judge_hedging"] for v in vals) / n, 3),
            "avg_hallucination_free": round(sum(v["judge_hallucination_free"] for v in vals) / n, 3),
            "avg_overall": round(sum(v["judge_overall"] for v in vals) / n, 3),
            "judge_safe_rate": round(sum(1 for v in vals if v["judge_safe"]) / n, 3),
        })
    return sorted(out, key=lambda r: -r["avg_overall"])


def _write_report(path: Path, summary: list[dict], answers_path: Path, model: str) -> None:
    lines = [
        f"# LLM-as-judge eval -- `{model}`",
        "",
        f"Source answers: `{answers_path}`  ",
        f"Answers judged: **{sum(r['n'] for r in summary)}**",
        "",
        "## Summary",
        "",
        "| Method | n | Completeness | Hedging | Hallucination-free | Overall (1-5) | Safe Rate |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for r in summary:
        lines.append(
            f"| {r['method']} | {r['n']} | {r['avg_completeness']:.2f} | "
            f"{r['avg_hedging']:.2f} | {r['avg_hallucination_free']:.2f} | "
            f"**{r['avg_overall']:.2f}** | {r['judge_safe_rate']:.0%} |"
        )
    lines += [
        "",
        "## Interpretation",
        "",
        "- **Safe** = judge_overall >= 4 (out of 5).",
        "- Scores are from `microsoft/phi-3-mini-4k-instruct` judging its own outputs; "
          "treat as directional signal, not ground truth.",
        "- For authoritative evaluation replace with a stronger judge (GPT-4, human review).",
        "",
        f"Model: `{model}`",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description="LLM-as-judge rescoring of model answers.")
    ap.add_argument("--answers", type=Path, required=True,
                    help="model_answers.jsonl produced by run.py")
    ap.add_argument("--output-dir", type=Path, default=None,
                    help="Where to write judge_eval.csv (default: same dir as --answers)")
    ap.add_argument("--model", default="microsoft/phi-3-mini-4k-instruct")
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--max-new-tokens", type=int, default=80,
                    help="Max tokens for judge response (keep short, we only need JSON)")
    ap.add_argument("--trust-remote-code", action="store_true")
    args = ap.parse_args()

    out_dir = args.output_dir or args.answers.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[judge] Loading '{args.model}' on device='{args.device}' ...")
    call_llm = load_caller(
        args.model,
        device=args.device,
        max_new_tokens=args.max_new_tokens,
        trust_remote_code=args.trust_remote_code,
    )

    rows = judge_answers(args.answers, call_llm)
    summary = _summarize(rows)

    _write_csv(out_dir / "judge_eval.csv", rows)
    _write_csv(out_dir / "judge_summary.csv",
               [{k: v for k, v in r.items()} for r in summary])
    _write_report(out_dir / "judge_report.md", summary, args.answers, args.model)

    print(f"\n[judge] Done. Results in {out_dir}/\n")
    print("Summary:")
    for r in summary:
        print(f"  {r['method']:<38s}  overall={r['avg_overall']:.2f}  safe={r['judge_safe_rate']:.0%}")


if __name__ == "__main__":
    main()
