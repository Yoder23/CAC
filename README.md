# Context Admission Control (CAC)

> **RAG retrieves chunks. CAC satisfies evidence requirements.**

Context Admission Control (CAC) is a research prototype for **evidence admission under budget**. It is designed for evidence-sensitive AI workflows where the model should not simply read the most relevant chunks — it should reason from the **right evidence**, in the **right representation**, with an **audit trail**.

CAC changes the unit of context from:

```text
retrieved chunk
```

to:

```text
satisfied evidence requirement
```

This repository includes:

- the CAC packet-building prototype,
- DecisionRiskBench v1.4,
- RAG-style baselines,
- packaged benchmark outputs,
- rewrite and stress suites,
- no-gold-admission tests,
- and an external LLM prompt/export harness for future answer evaluation.

---

## Why CAC?

Classic RAG usually follows this pattern:

```text
query → retrieve chunks → stuff context → answer
```

That works for many lookup tasks. But evidence-sensitive decisions often require more than chunk relevance:

- Which source is authoritative?
- Is the evidence current?
- Is exact wording required?
- What evidence is missing?
- Which sources contradict each other?
- What should be excluded as stale, low-authority, or distracting?
- How much model context should this evidence cost?

CAC adds a context-control layer:

```text
task → evidence requirements → candidate pool → evidence valuation
     → representation selection → evidence packet → answer
```

The core claim:

> **RAG optimizes chunk relevance. CAC optimizes evidence sufficiency under budget.**

---

## What CAC Builds

CAC outputs an **evidence packet**, not a bag of chunks.

An evidence packet can contain:

```text
structured facts
summaries
exact excerpts
conflicts
uncertainties
excluded evidence
audit trace
filled evidence requirements
missing evidence requirements
```

Example:

```json
{
  "structured_facts": [
    {
      "source": "billing_row_044",
      "fact": {
        "invoice_status": "47_days_overdue",
        "outstanding_balance": 184000
      }
    }
  ],
  "exact_evidence": [
    {
      "source": "contract_184_section_12_2",
      "text": "Non-payment of undisputed fees for more than forty-five days constitutes material breach after notice."
    }
  ],
  "conflicts": [
    {
      "issue": "CRM says the account is healthy; billing and support indicate risk."
    }
  ],
  "uncertainties": [
    "No executive sponsor signal found."
  ],
  "excluded_evidence": [
    {
      "source": "slack_thread_332",
      "reason": "Low-authority speculation without attached source."
    }
  ]
}
```

Design rule:

> **Compress facts. Preserve language when wording carries obligation, ambiguity, or risk.**

---

## Project Status

This is a **research prototype and synthetic benchmark artifact**.

It is suitable for:

- studying post-RAG context-control architectures,
- comparing evidence packets against chunk-stuffing baselines,
- experimenting with auditable evidence admission,
- and reproducing DecisionRiskBench v1.4 results.

It is **not** production proof.

### Supported by this repository

On synthetic DecisionRiskBench v1.4, CAC achieves stronger aggregate decision-grade and deterministic answer-readiness proxy outcomes than the included chunk-stuffing RAG baselines under same-candidate-pool conditions.

### Not claimed

This repository does **not** prove that:

```text
RAG is dead in production.
CAC beats every possible RAG stack.
Human users prefer CAC.
Real LLM answers have been shown to improve from CAC packets.
Synthetic benchmark results guarantee production performance.
```

The current public line is:

> **RAG is in trouble for evidence-sensitive decision work because chunk relevance is losing to evidence sufficiency under budget.**

---

## Headline Reference Result

Packaged main run:

```bash
PYTHONPATH=. python -m benchmarks.decision_risk.run \
  --n 20 \
  --budgets 40,60,80,120,160,240,500 \
  --distractors 5,25,50 \
  --output-dir outputs/decision_risk_v1_4_n20
```

Shape:

```text
20 accounts × 4 tasks × 7 budgets × 3 distractor levels × 8 methods = 13,440 rows
```

Aggregate results from the packaged output:

| Method | Avg Tokens | Decision Grade | Answer-Readiness Proxy | Distractor Rate | Exact Clause | Contradiction Recall |
|---|---:|---:|---:|---:|---:|---:|
| `cac` | 60.1583 | **0.8101** | **0.8556** | **0.0464** | **0.9750** | **0.6280** |
| `schema_aware_chunk_rag_k8` | 85.2643 | 0.6892 | 0.7366 | 0.2923 | 0.8923 | 0.2101 |
| `iterative_rag_k8` | 69.6815 | 0.6876 | 0.7374 | 0.2344 | 0.8083 | 0.2458 |
| `oracle_candidate_rag_k8` | 87.2554 | 0.6794 | 0.7455 | 0.2750 | 0.9524 | 0.1815 |
| `metadata_aware_rag_k8` | 85.1798 | 0.6717 | 0.7106 | 0.2923 | 0.8869 | 0.2101 |
| `heuristic_rerank_rag_k8` | 87.8994 | 0.6403 | 0.6892 | 0.3393 | 0.8652 | 0.1649 |
| `long_context_rag_k24` | 126.6375 | 0.6046 | 0.6270 | 0.5209 | 0.7438 | 0.2458 |
| `fixed_context_rag_k8` | 86.4607 | 0.5934 | 0.6310 | 0.4445 | 0.6997 | 0.2458 |

CAC also wins every included task family by decision-grade score in the packaged main run:

```text
contract termination
incident postmortem
renewal risk
security exception
```

---

## Benchmark Boundary

DecisionRiskBench v1.4 tests **context-control strategy**, not retriever quality.

All compared methods use the same candidate pool. The difference is how they assemble context:

- RAG baselines admit raw chunks.
- CAC can admit compact evidence representations such as structured facts, summaries, and exact excerpts.

That distinction is intentional. CAC is being evaluated as **evidence admission**, not as another retriever.

This is also a methodological boundary. Stronger future baselines should include compression-aware and answer-aware RAG variants.

---

## Deterministic Answer-Readiness Proxy

The generated-answer metric in this repository is a **deterministic answer-readiness proxy**.

It is not an LLM answer study and it is not a human preference study.

The next empirical milestone is:

```text
RAG chunks → same LLM → answer
CAC evidence packet → same LLM → answer
human or LLM judge → score
```

This repository includes prompt export and answer-scoring scaffolding for that next step, but it does not include real model outputs.

When using the external LLM prompt export, send only the `prompt` field to the model. Do not send gold metadata fields used later for scoring.

---

## No-Gold-Admission Boundary

`SourceItem` carries benchmark gold fields for scoring and for the explicit oracle baseline. Tests assert that CAC core and non-oracle RAG baselines do **not** read these scorer-only fields:

```text
gold_slots
gold_negative
gold_positive
gold_exact_required
is_distractor
```

The explicit `oracle_candidate_rag_k8` baseline is allowed to use these fields by design.

---

## Quickstart

Use Python 3.10 or newer.

```bash
python -m pip install -e ".[dev]"
pytest -q
PYTHONPATH=. python tests/run_smoke_tests.py
PYTHONPATH=. python examples/acme_demo.py
```

On Windows PowerShell:

```powershell
$env:PYTHONPATH='.'
python -m pytest -q
python examples/acme_demo.py
```

---

## Start Here

If you are new to the project:

1. Run the Acme demo.
2. Read the evidence packet output.
3. Inspect the benchmark summary.
4. Run the smoke benchmark.
5. Read the methodology notes.

```bash
PYTHONPATH=. python examples/acme_demo.py
```

Then inspect:

```text
outputs/decision_risk_v1_4_n20/summary.csv
outputs/decision_risk_v1_4_n20/benchmark_report.md
```

---

## Reproduce the Main Suites

### Main DecisionRiskBench suite

```bash
PYTHONPATH=. python -m benchmarks.decision_risk.run \
  --n 20 \
  --budgets 40,60,80,120,160,240,500 \
  --distractors 5,25,50 \
  --output-dir outputs/decision_risk_v1_4_n20
```

### Semi-synthetic rewrite suite

The rewrite suite perturbs source wording and observable metadata to reduce reliance on templated phrase matching.

```bash
PYTHONPATH=. python -m benchmarks.decision_risk_human_rewrite.run \
  --n 8 \
  --budgets 40,60,80,120,160,240 \
  --distractors 25,50 \
  --metadata-noise 0.18 \
  --output-dir outputs/decision_risk_v1_4_rewrite
```

### Failure-stress suite

The stress suite targets contradiction misses, slot underfill, exact-representation failure, and high distractor pressure.

```bash
PYTHONPATH=. python -m benchmarks.decision_risk_stress.run \
  --n 8 \
  --budgets 40,60,80,120,160 \
  --distractors 50,100 \
  --metadata-noise 0.30 \
  --output-dir outputs/decision_risk_v1_4_stress
```

### External LLM prompt export

```bash
PYTHONPATH=. python -m benchmarks.decision_risk.export_llm_eval_prompts \
  --n 5 \
  --budget 160 \
  --distractors 25 \
  --output outputs/llm_eval_v1_4/prompts.jsonl
```

After filling a JSONL file with model answers:

```bash
PYTHONPATH=. python -m benchmarks.decision_risk.llm_eval \
  --answers outputs/llm_eval_v1_4/model_answers.jsonl \
  --output-dir outputs/llm_eval_v1_4_eval
```

---

## Repository Layout

```text
cac/
  core/                 CAC schemas, slot matching, valuation, packet assembly
  baselines/            RAG-style baselines

benchmarks/
  decision_risk/        Main DecisionRiskBench generator, runner, scorer, plots
  decision_risk_human_rewrite/
                        Semi-synthetic rewrite suite
  decision_risk_stress/
                        Failure-stress suite

examples/
  acme_demo.py          Small guided CAC demo

tests/
  no-gold-admission, smoke, plot, prompt-export, and row-count tests

outputs/
  packaged reference outputs and plots
```

---

## Key Concepts

### Evidence requirement

A task-specific requirement that must be satisfied for a decision to be well supported.

Examples:

```text
current billing status
contract termination language
security exception approval
incident root cause
missing executive sponsor signal
```

### Evidence packet

The final CAC context artifact. It can contain structured facts, exact excerpts, summaries, conflicts, uncertainties, exclusions, and an audit trace.

### Representation-aware admission

CAC chooses whether evidence should be represented as a structured fact, summary, exact excerpt, metadata, or excluded entirely.

### Missing-evidence calibration

CAC can explicitly state that a required evidence slot was not found or not sufficiently satisfied.

### Same-candidate-pool evaluation

All compared methods receive the same candidate evidence pool. The benchmark tests context assembly, not retriever quality.

---

## Baselines

Included baselines:

```text
fixed_context_rag_k8
metadata_aware_rag_k8
schema_aware_chunk_rag_k8
heuristic_rerank_rag_k8
iterative_rag_k8
long_context_rag_k24
oracle_candidate_rag_k8
```

The oracle baseline is intentionally synthetic and uses gold labels for candidate ordering. It is included to test whether better candidate ordering alone closes the gap.

---

## Limitations

This repository is intentionally transparent about what it does not prove.

Current limitations:

```text
Synthetic benchmark.
Semi-synthetic rewrite suite is not human-audited real data.
Generated-answer metric is deterministic, not real LLM/human evaluation.
No production deployment results.
No human preference study.
No real enterprise dataset.
```

The strongest current conclusion is:

> CAC is a promising post-RAG control-plane candidate for evidence-sensitive decisions.

Not:

> CAC is production-proven.

---

## Roadmap

Planned next steps:

```text
same-model LLM answer evaluation
human or LLM-judge scoring
human-audited mini-set
real or semi-real dataset
compression-aware RAG baselines
answer-aware RAG baselines
more task profiles
```

The next decisive test:

```text
Do the same LLMs make better decisions from CAC packets than from RAG chunks?
```

---

## Citation / Working Note

If you reference this project, use the core claim:

> RAG made retrieved chunks the unit of context. CAC makes satisfied evidence requirements the unit of context.

Suggested title for discussion:

```text
RAG Optimizes Relevance. Evidence Work Needs Sufficiency.
```

---

## Contributing

Issues and pull requests are welcome, especially around:

```text
stronger baselines
additional task profiles
realistic datasets
LLM answer evaluation
human-audited scoring
benchmark critiques
failure analysis
```

Please keep benchmark claims tied to reproducible outputs.

---

## License

MIT. See [`LICENSE`](LICENSE).
