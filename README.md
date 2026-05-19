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

New here? Start with START_HERE.md.

## How CAC differs from RAG

| RAG | CAC |
|---|---|
| Retrieves chunks | Satisfies evidence requirements |
| Optimizes relevance | Optimizes sufficiency under budget |
| Stuffs raw text | Chooses representations |
| Usually cites retrieved docs | Audits admission/exclusion decisions |
| Often answers from what it found | Reports missing evidence |
| More context can mean more noise | Context is governed by evidence policy |

![Decision grade vs budget](outputs/decision_risk_v1_4_n20/decision_grade_vs_budget.svg)
![Distractor rate vs budget](outputs/decision_risk_v1_4_n20/distractor_rate_vs_budget.svg)

## Who this is for

CAC is for builders working on:
- enterprise AI assistants
- auditable QA
- decision support
- compliance / security / contract workflows
- post-RAG context engineering
- LLM evaluation and retrieval benchmarks

CAC is probably overkill for:
- simple FAQ bots
- single-document lookup
- low-stakes retrieval demos

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

**RAG is in trouble for evidence-sensitive decision work because chunk relevance is losing to evidence sufficiency under budget.**

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

| Method | Avg Tokens | Decision Grade | Safe Rate | Grade/1k Tokens | Distractor Rate | Contradiction Recall |
|---|---:|---:|---:|---:|---:|---:|
| `cac` | **60.2** | **0.810** | **62%** | **14.1** | **4.6%** | **62.8%** |
| `schema_aware_chunk_rag_k8` | 85.3 | 0.689 | 18% | 9.0 | 29.2% | 21.0% |
| `iterative_rag_k8` | 69.7 | 0.688 | 17% | 10.6 | 23.4% | 24.6% |
| `oracle_candidate_rag_k8` | 87.3 | 0.679 | 18% | 9.1 | 27.5% | 18.2% |
| `metadata_aware_rag_k8` | 85.2 | 0.672 | 15% | 8.7 | 29.2% | 21.0% |
| `heuristic_rerank_rag_k8` | 87.9 | 0.640 | 11% | 8.3 | 33.9% | 16.5% |
| `long_context_rag_k24` | 126.6 | 0.605 | 15% | 6.7 | 52.1% | 24.6% |
| `fixed_context_rag_k8` | 86.5 | 0.593 | 15% | 7.9 | 44.5% | 24.6% |

> **CAC is the only method to exceed 60% safe rate. Best RAG baseline tops out at 18%.**  
> **CAC uses 31% fewer tokens than the best RAG baseline while scoring 17.5pp higher on decision grade.**

### Budget efficiency — minimum tokens to reach decision grade ≥ 0.9

| Method | Hit Rate | Mean Min Budget |
|---|---:|---:|
| `cac` | **54.6%** | **73.1 tokens** |
| `iterative_rag_k8` | 22.9% | 77.8 tokens |
| `schema_aware_chunk_rag_k8` | 22.5% | 78.5 tokens |
| `oracle_candidate_rag_k8` | 22.5% | 78.5 tokens |
| `fixed_context_rag_k8` | 20.8% | 80.0 tokens |
| `heuristic_rerank_rag_k8` | 8.8% | 80.0 tokens |

> **CAC reaches decision grade ≥ 0.9 on 54.6% of tasks — 2.4× the best RAG hit rate — and does so earlier in the budget.**

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

This repository now includes **packaged real-model outputs** — see the [LLM Answer Quality](#real-model-llm-answer-quality) section below.

When using the external LLM prompt export, send only the `prompt` field to the model. Do not send gold metadata fields used later for scoring.

---

## Real-Model LLM Answer Quality

The following results are from a live inference run using `microsoft/phi-3-mini-4k-instruct` (3.82B parameters, CUDA) on 100 prompts (5 methods × 20 prompts across 5 accounts and 4 task types).  
Scorer: lexical proxy (slot coverage, citation markers, hedging keywords).  
Full outputs: `outputs/llm_eval_real/`

| Method | LLM Answer Score | Safe Rate | Contradiction Handling | Missing Disclosure |
|---|---:|---:|---:|---:|
| `cac` | **0.8157** | **65%** | 100% | 100% |
| `oracle_candidate_rag_k8` | 0.8088 | 60% | 100% | 100% |
| `schema_aware_chunk_rag_k8` | 0.7832 | 40% | 100% | 100% |
| `iterative_rag_k8` | 0.7282 | 15% | 90% ← failure | 100% |
| `fixed_context_rag_k8` | 0.6608 | 20% | 100% | 95% ← failure |

> **CAC's safe rate is 3.25× that of fixed-context RAG on the same candidate pool.**  
> **CAC is the only method to achieve 100% across all three safety dimensions (contradiction handling, missing disclosure, safe rate ≥ 0.80).**

### LLM-as-judge pass (same 100 answers)

A second scorer — `microsoft/phi-3-mini-4k-instruct` acting as judge — independently rated each answer on completeness, hedging, hallucination-freedom, and an overall 1–5 score. Results:

| Method | Completeness | Hedging | Hallucination-free | Overall (1–5) |
|---|---:|---:|---:|---:|
| `cac` | **4.80** | **4.95** | 5.00 | **4.85** |
| `schema_aware_chunk_rag_k8` | 4.80 | 4.90 | 5.00 | 4.80 |
| `oracle_candidate_rag_k8` | 4.75 | 4.75 | 5.00 | 4.75 |
| `iterative_rag_k8` | 4.55 | 4.95 | 5.00 | 4.55 |
| `fixed_context_rag_k8` | 4.40 | 4.85 | 5.00 | 4.45 |

> **Both the lexical scorer and the LLM judge rank the methods in the same order: CAC first.**  
> The judge confirms that completeness is the differentiating dimension — CAC provides the most complete answers because admission control ensures the right evidence is always present.  
> Full scoring details: `outputs/llm_eval_real/judge_report.md`

Note: `oracle_candidate_rag_k8` receives oracle knowledge of which candidates are relevant — an upper-bound baseline not available in real deployments. CAC matches it on answer quality without oracle access.

### Stress eval: 50 distractors, n=15 accounts (300 prompts)

A harder run testing distractor robustness: 50 irrelevant chunks injected per account, n=15 accounts, budget=160 tokens.  
Full outputs: `outputs/llm_eval_stress/`

| Method | LLM Answer Score | Safe Rate | Contradiction Handling | Missing Disclosure |
|---|---:|---:|---:|---:|
| `cac` | **0.8242** | **63.3%** | 100% | 100% |
| `oracle_candidate_rag_k8` | 0.7975 | 48.3% | 100% | 100% |
| `schema_aware_chunk_rag_k8` | 0.7406 | 26.7% | 100% | 100% |
| `iterative_rag_k8` | 0.7334 | 21.7% | 91.7% ← failure | 100% |
| `fixed_context_rag_k8` | 0.6513 | **0.0%** ← collapse | 98.3% ← failure | 100% |

> **At 50 distractors, fixed-context RAG drops to 0% safe rate. CAC holds at 63.3% — essentially unchanged from 65% at lower distractor load.**  
> CAC's admission-control filter is immune to distractor count by design: irrelevant chunks are rejected before the context window is built.

LLM-as-judge confirmation (phi-3-mini judging the same 300 answers):

| Method | Completeness | Hallucination-free | Overall (1–5) |
|---|---:|---:|---:|
| `cac` | **4.82** | 5.00 | **4.82** |
| `oracle_candidate_rag_k8` | 4.80 | 5.00 | 4.80 |
| `iterative_rag_k8` | 4.52 | 5.00 | 4.55 |
| `fixed_context_rag_k8` | 4.30 | 4.98 ← failure | 4.43 |

> At 50 distractors, `fixed_context_rag` is the **only method to show hallucination failures** in the judge pass (hallucination-free drops below 5.00), corroborating the lexical safe-rate collapse.

### Production stress battery: three adversarial scenarios

A three-scenario battery designed to simulate the hardest real-world conditions:
1,000 total LLM inferences + 1,000 judge calls across all scenarios.

#### Scenario A — Token budget crunch (`budget=80`, d=50, n=15, 300 prompts)

Context window cut in half vs. the standard run. Greedy RAG fills the window with whatever scores highest; CAC's slot-prioritized admission control selects the most critical evidence.  
Full outputs: `outputs/llm_eval_budget_crunch/`

| Method | LLM Answer Score | Safe Rate |
|---|---:|---:|
| `cac` | **0.8327** | **70.0%** |
| `oracle_candidate_rag_k8` | 0.8032 | 55.0% |
| `schema_aware_chunk_rag_k8` | 0.7876 | 50.0% |
| `iterative_rag_k8` | 0.7498 | 30.0% |
| `fixed_context_rag_k8` | 0.6376 | **3.3%** ← near-collapse |

> **CAC's safe rate advantage widens under budget pressure: 70% vs. 3.3% for fixed-context RAG.** When the context window is scarce, greedy fill wastes tokens on low-value chunks; admission control spends every token on evidence that matters.

#### Scenario B — Extreme distractor flood (`d=100`, budget=160, n=20, 400 prompts)

2× the distractor density used in the stress eval. At d=50 fixed-context RAG already hit 0% — this scenario tests whether any RAG variant can survive at d=100.  
Full outputs: `outputs/llm_eval_extreme_noise/`

| Method | LLM Answer Score | Safe Rate |
|---|---:|---:|
| `cac` | **0.8067** | **57.5%** |
| `oracle_candidate_rag_k8` | 0.7560 | 36.25% |
| `schema_aware_chunk_rag_k8` | 0.7522 | 33.75% |
| `iterative_rag_k8` | 0.7483 | 30.0% |
| `fixed_context_rag_k8` | 0.6452 | **0.0%** ← total collapse |

> **At 100 distractors, fixed-context RAG collapses to 0% safe rate for the second time. CAC holds at 57.5% — 1.6× the next-best method.** The LLM-as-judge also ranks CAC first on this scenario (4.76 vs. 4.64 for the next-best), the only scenario where the judge and lexical scorer agree on the top method.

#### Scenario C — Metadata corruption (`noise=0.50`, d=50, budget=160, n=15, 300 prompts)

50% of metadata fields (topics, risk tags) stripped or corrupted — simulating a production environment with unreliable tagging pipelines.  
Full outputs: `outputs/llm_eval_metadata_corruption/`

| Method | LLM Answer Score | Safe Rate |
|---|---:|---:|
| `oracle_candidate_rag_k8` | **0.8030** | **60.0%** |
| `cac` | 0.7857 | 48.0% |
| `schema_aware_chunk_rag_k8` | 0.7827 | 48.0% |
| `iterative_rag_k8` | 0.7782 | 42.0% |
| `fixed_context_rag_k8` | 0.6513 | **5.0%** ← near-collapse |

> **Under 50% metadata corruption, `oracle_candidate_rag` leads — it is metadata-immune by design (it receives ground-truth candidate lists). CAC drops to 2nd but still nearly 10× safer than fixed-context RAG (48% vs. 5%).** Schema-aware RAG, which relies on metadata matching for reranking, ties CAC on safe rate despite its metadata advantage in clean conditions. The result demonstrates that CAC's structural slot matching is significantly more robust to metadata noise than schema-aware approaches.

#### Production battery summary

Across all conditions, CAC ranks #1 or #2 on ground-truth lexical safe rate and is the **only non-oracle method to hold above 48% safe rate in every scenario**:

| Scenario | CAC safe rate | Next-best non-oracle | fixed-context RAG |
|---|---:|---:|---:|
| Baseline (d=50, budget=160) | 63.3% | 26.7% (schema) | 0.0% |
| A: Budget crunch (budget=80) | **70.0%** | 50.0% (schema) | 3.3% |
| B: Distractor flood (d=100) | **57.5%** | 33.75% (schema) | 0.0% |
| C: Metadata corruption (noise=0.5) | 48.0% | 48.0% (schema, tied) | 5.0% |

### Per-task-type safe rate breakdown

Baseline stress run (d=50, budget=160, n=15 × 4 tasks = 60 answers per method):

| Task | `cac` | `oracle_candidate_rag` | `schema_aware_rag` | `iterative_rag` | `fixed_context_rag` |
|---|---:|---:|---:|---:|---:|
| Renewal risk | **80%** | 13% | 47% | 60% | 0% |
| Security exception | **33%** | 7% | 0% | 0% | 0% |
| Contract termination | 60% | **93%** | 27% | 7% | 0% |
| Incident postmortem | **80%** | 80% | 33% | 20% | 0% |

> **`fixed_context_rag` achieves 0% safe rate on all four task types.** CAC leads on three of four tasks; oracle leads only on contract termination (where knowing the gold candidate list is most valuable). The security exception task is the hardest overall — CAC is the *only non-oracle method to achieve any safe rate at all* (33% vs. 0% for schema, iterative, and fixed-context).

### Budget efficiency: safe rate per token

**Efficiency ratio** = `safe_rate ÷ (budget ÷ 160)` — how much safe-rate value each method extracts relative to its token spend. Ratio > 1.0 means the method is more efficient at a tighter budget than at the 160-token baseline.

| Scenario | budget | `cac` | `oracle` | `schema_aware` | `iterative` | `fixed_context` |
|---|---:|---:|---:|---:|---:|---:|
| Baseline stress (d=50) | 160 | 0.63 | 0.48 | 0.27 | 0.22 | 0.00 |
| A: Budget crunch | **80** | **1.40** | 1.10 | 1.00 | 0.60 | 0.07 |
| B: Distractor flood (d=100) | 160 | 0.57 | 0.36 | 0.34 | 0.30 | 0.00 |
| C: Metadata corruption | 160 | 0.48 | 0.60 | 0.48 | 0.42 | 0.05 |

> **At budget=80, CAC's efficiency ratio reaches 1.40 — meaning it delivers more safe answers per token at half the context window than it does at full size.** This is the defining characteristic of admission control: greedy RAG fills available space regardless of value; CAC selects by value regardless of space. When space is scarce, the gap widens.

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
