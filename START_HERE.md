# Start Here — Quick entry

1. What CAC is

   Context Admission Control (CAC) is a context-control strategy and
   synthetic benchmark (DecisionRiskBench v1.4) for evaluating evidence
   admission policies under token budgets. It focuses on admitting compact,
   sufficient evidence rather than retrieving raw chunks.

2. Run the Acme demo

   ```bash
   PYTHONPATH=. python examples/acme_demo.py
   ```

3. Run tests

   ```bash
   python -m pip install -e ".[dev]"
   pytest -q
   ```

4. Run smoke benchmark

   ```bash
   PYTHONPATH=. python tests/run_smoke_tests.py
   ```

5. Inspect headline results

   See `outputs/decision_risk_v1_4_n20/` for packaged CSVs and SVGs (or
   release assets if outputs are excluded from the repo).

6. Read methodology

   See `docs/methodology.md` for details on task design, scoring, and
   benchmark boundaries.

7. Inspect audit package

   See `RELEASE_CHECKLIST.md`, `AUDIT_NOTES.md`, and `FULL_MANIFEST.md` for
   packaging and verification details.
