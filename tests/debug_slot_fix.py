"""Diagnostic: trace contract_termination safe-rate failure modes with v1.5 code."""
from __future__ import annotations

from benchmarks.decision_risk.generate import generate_decision_dossiers
from benchmarks.decision_risk.profiles import build_task_profile
from benchmarks.decision_risk.score import score_packet_generic
from cac.core.retrieval import candidate_pool
from cac.core.valuation import value_candidates
from cac.core.packet import assemble_packet
from cac.core.expansion import expansion_loop
from cac.baselines.naive_rag import oracle_candidate_rag


def run_diagnostic(n: int = 20, distractors: int = 5, noise: float = 0.0) -> None:
    dossiers = generate_decision_dossiers(
        n=n, distractors=distractors, seed=42,
        task_types=["contract_termination"],
        missing_rate=0.25, metadata_noise=noise,
    )
    print(f"\n=== d={distractors} noise={noise} n={n} ===")
    cac_safe_count = oracle_safe_count = 0
    for d in dossiers:
        profile = build_task_profile("contract_termination", d.entity, budget=160)
        candidates = candidate_pool(profile, d.sources, max_candidates=20)
        vals = value_candidates(profile, candidates)
        packet, admitted = assemble_packet(profile, vals, method="cac")
        packet = expansion_loop(profile, candidates, packet, admitted)
        cs = score_packet_generic(d, packet)
        op = oracle_candidate_rag(profile, candidates, k=8)
        os_ = score_packet_generic(d, op)
        if cs["answer_readiness_safe"]:
            cac_safe_count += 1
        if os_["answer_readiness_safe"]:
            oracle_safe_count += 1
        diff = " <<< DIVERGES" if cs["answer_readiness_safe"] != os_["answer_readiness_safe"] else ""
        print(
            f"  {d.account_id} missing={d.missing_case_type:20s} "
            f"CAC safe={cs['answer_readiness_safe']} score={cs['answer_readiness_score']:.3f} "
            f"contra={cs['contradiction_recall']:.1f} slots={cs['slot_fill_rate']:.2f} "
            f"| Oracle safe={os_['answer_readiness_safe']} score={os_['answer_readiness_score']:.3f} "
            f"contra={os_['contradiction_recall']:.1f}{diff}"
        )
        if not cs["answer_readiness_safe"]:
            pos_docs = [ev.item.source_id for ev in packet.admitted if ev.item.gold_positive]
            print(f"    gold_positive admitted: {pos_docs}  conflicts: {[c['issue'] for c in packet.conflicts]}")
    print(f"  SUMMARY  CAC {cac_safe_count}/{n}={cac_safe_count/n*100:.0f}%  Oracle {oracle_safe_count}/{n}={oracle_safe_count/n*100:.0f}%")


if __name__ == "__main__":
    run_diagnostic(n=20, distractors=5, noise=0.0)
    run_diagnostic(n=20, distractors=25, noise=0.3)
