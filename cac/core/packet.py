
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .schemas import EvidencePacket, AdmittedEvidence, Representation, TaskProfile, CandidateValuation, SourceType
from .valuation import admission_cost, metadata_distractor_signal
from .slots import representation_satisfies_slot, slot_requires_exact


def summarize(text: str, max_words: int = 36) -> str:
    words = text.strip().split()
    return text.strip() if len(words) <= max_words else " ".join(words[:max_words]) + " ..."


def excerpt(text: str, max_words: int = 110) -> str:
    words = text.strip().split()
    return " ".join(words[:max_words]) + (" ..." if len(words) > max_words else "")


def compact_fact(text: str) -> Dict[str, str]:
    return {"statement": summarize(text, 24)}


def audit_entry(v: CandidateValuation, decision: str, cost: int, reason_override: str | None = None) -> Dict[str, Any]:
    return {
        "candidate": v.item.source_id,
        "source_type": v.item.source_type.value,
        "admission_decision": decision,
        "representation": v.representation.value,
        "admission_reason": reason_override or v.admission_reason,
        "representation_reason": v.representation_reason,
        "fills_slots": v.slot_matches,
        "token_cost": cost,
        "scores": {
            "admission_score": v.admission_score,
            "relevance": v.relevance,
            "authority": v.authority,
            "freshness": v.freshness,
            "novelty": v.novelty,
            "contradiction_potential": v.contradiction_potential,
            "task_criticality": v.task_criticality,
        },
    }


def _is_exact_slot_candidate(profile: TaskProfile, v: CandidateValuation) -> bool:
    return any(slot_requires_exact(profile, s) and representation_satisfies_slot(profile, s, v.representation) for s in v.slot_matches)


def _signal_side(text: str) -> str | None:
    t = text.lower()
    positive = any(x in t for x in ["healthy", "green", "on track", "low risk", "likely renew", "approve", "approved", "minor", "optimistic", "strategic", "business justification"])
    negative = any(x in t for x in ["overdue", "p1", "escalation", "late", "unresolved", "breach", "terminate", "cannot recommend", "blocked", "gap", "missing", "lost export", "root cause", "dispute", "uncured", "downtime", "failed", "risk"])
    if positive and not negative:
        return "positive"
    if negative and not positive:
        return "negative"
    if positive and negative:
        return "mixed"
    return None


def _is_conflict_pair_candidate(v: CandidateValuation) -> bool:
    item = v.item
    if metadata_distractor_signal(item) or item.authority < 0.50:
        return False
    if item.source_type not in {SourceType.CRM, SourceType.BILLING, SourceType.SUPPORT, SourceType.CONTRACT, SourceType.EMAIL, SourceType.SECURITY, SourceType.INTERNAL_NOTE}:
        return False
    text = " ".join([item.text, item.title, " ".join(item.topics), " ".join(item.risk_tags)])
    return _signal_side(text) is not None


def _reservation_rank(profile: TaskProfile, v: CandidateValuation) -> tuple[int, float]:
    # Lower primary rank is admitted earlier. Exact wording is first, then
    # trusted conflict-pair evidence, then normal score order.
    if _is_exact_slot_candidate(profile, v):
        return (0, -v.admission_score)
    if _is_conflict_pair_candidate(v):
        return (1, -v.admission_score)
    return (2, -v.admission_score)


def assemble_packet(profile: TaskProfile, valuations: List[CandidateValuation], method: str = "cac") -> Tuple[EvidencePacket, List[AdmittedEvidence]]:
    packet = EvidencePacket(
        answer_target=profile.answer_target, entity=profile.entity, method=method,
        budget_used={"context_tokens": 0, "candidate_sources_scanned": len(valuations), "sources_admitted": 0},
    )
    admitted: list[AdmittedEvidence] = []
    used = 0
    satisfied_slots: set[str] = set()

    # v1.2 reservation pass: exact-wording and conflict-pair evidence are
    # processed before ordinary high-score evidence. This makes CAC less likely
    # to spend the budget on merely useful summaries before satisfying hard
    # decision-safety requirements.
    valuations = sorted(valuations, key=lambda v: _reservation_rank(profile, v))

    for v in valuations:
        item = v.item
        rep = v.representation
        cost = admission_cost(item, rep)
        if rep == Representation.IGNORE:
            exclude(packet, v, cost, "representation policy excluded candidate")
            continue
        if v.admission_score < 1.15:
            exclude(packet, v, cost, "admission score below threshold")
            continue
        # Do not admit evidence if it neither satisfies a remaining slot nor helps complete a trusted conflict pair.
        # This prevents CAC from chasing stale call notes, Slack speculation, or noisy distractors simply
        # because they contain superficially contradictory language.
        new_satisfying_slots = [s for s in v.slot_matches if s not in satisfied_slots and representation_satisfies_slot(profile, s, rep)]
        trusted_conflict_source = (
            v.item.source_type in {SourceType.CRM, SourceType.BILLING, SourceType.SUPPORT, SourceType.CONTRACT, SourceType.EMAIL, SourceType.SECURITY, SourceType.INTERNAL_NOTE}
            and not metadata_distractor_signal(v.item)
            and v.item.authority >= 0.55
        )
        # Metadata-detected distractors must not fill evidence slots: noise may have injected
        # task-relevant tags into their metadata.  They are still considered for the trusted-conflict
        # path so genuine polarity signals are not blocked, but they do not satisfy slot requirements.
        effective_slot_fill = [] if metadata_distractor_signal(v.item) else new_satisfying_slots
        if not effective_slot_fill and not (trusted_conflict_source and v.contradiction_potential >= 0.45):
            exclude(packet, v, cost, "redundant or does not satisfy a remaining evidence slot or trusted conflict pair")
            continue
        if used + cost > profile.token_budget:
            exclude(packet, v, cost, "token budget exhausted")
            continue
        used += cost
        ev = AdmittedEvidence(item=item, representation=rep, slot_matches=v.slot_matches, token_cost=cost)
        admitted.append(ev)
        for s in effective_slot_fill:
            satisfied_slots.add(s)
        packet.audit_trace.append(audit_entry(v, "admitted", cost))
        if rep == Representation.STRUCTURED_FACT:
            packet.structured_facts.append({"source": item.source_id, "source_type": item.source_type.value, "fact": item.structured or compact_fact(item.text), "fills_slots": v.slot_matches})
        elif rep == Representation.SUMMARY:
            packet.summaries.append({"source": item.source_id, "source_type": item.source_type.value, "summary": summarize(item.text), "fills_slots": v.slot_matches})
        elif rep == Representation.EXACT_EXCERPT:
            packet.exact_evidence.append({"source": item.source_id, "source_type": item.source_type.value, "reason_included": v.representation_reason, "text": excerpt(item.text), "fills_slots": v.slot_matches})
        elif rep == Representation.METADATA_ONLY:
            packet.summaries.append({"source": item.source_id, "source_type": item.source_type.value, "summary": f"Metadata only: {item.title}", "fills_slots": v.slot_matches})

    packet.admitted = admitted
    packet.budget_used["context_tokens"] = used
    packet.budget_used["sources_admitted"] = len(admitted)
    update_packet_status(profile, packet)
    return packet, admitted


def exclude(packet: EvidencePacket, v: CandidateValuation, cost: int, reason: str) -> None:
    packet.excluded_evidence.append({"source": v.item.source_id, "title": v.item.title, "reason": reason, "token_cost_saved": cost})
    packet.audit_trace.append(audit_entry(v, "excluded", cost, reason_override=reason))


def update_packet_status(profile: TaskProfile, packet: EvidencePacket) -> None:
    filled = set()
    for slot in profile.required_slots:
        for ev in packet.admitted:
            if slot.name not in ev.slot_matches:
                continue
            if representation_satisfies_slot(profile, slot.name, ev.representation):
                filled.add(slot.name)
    packet.filled_slots = sorted(filled)
    packet.missing_slots = [slot.name for slot in profile.required_slots if slot.name not in filled]
    detect_conflicts(packet)
    detect_uncertainties(profile, packet)


def detect_conflicts(packet: EvidencePacket) -> None:
    packet.conflicts = []
    text = " ".join([ev.item.text.lower() for ev in packet.admitted])
    crm_positive = any(x in text for x in ["healthy", "green", "on track", "low risk", "likely renew", "approve", "approved", "minor", "optimistic", "strategic"])
    negative = any(x in text for x in ["overdue", "p1", "escalation", "unresolved", "cannot recommend", "breach", "terminate", "blocked", "gap", "missing", "lost export", "root cause", "dispute", "uncured", "downtime", "failed", "risk"])
    if crm_positive and negative:
        packet.conflicts.append({"issue": "CRM optimism conflicts with operational risk signals", "higher_authority_signal": "billing/support/contract/executive evidence should outweigh subjective CRM status"})
    # Counterparty dispute conflict: counterparty asserts good standing against established breach evidence.
    # "We dispute" / "no valid notice" is a positive claim from the counterparty's perspective; when
    # combined with breach/overdue evidence it constitutes a legally material conflict that must be
    # surfaced even though neither keyword alone looks like a CRM-vs-operational conflict.
    counterparty_positive = any(x in text for x in ["we dispute", "no valid notice", "customer counsel", "deny breach", "good standing"])
    breach_evidence = any(x in text for x in ["overdue", "breach", "uncured", "material breach", "payment default", "notice was sent", "cure notice"])
    if counterparty_positive and breach_evidence:
        packet.conflicts.append({"issue": "Counterparty disputes breach or notice validity", "higher_authority_signal": "verify notice was validly delivered per contractual requirements; termination may not be supportable until notice delivery is confirmed or counterparty claim is rebutted"})


def detect_uncertainties(profile: TaskProfile, packet: EvidencePacket) -> None:
    packet.uncertainties = []
    for slot_name in packet.missing_slots:
        slot = next((s for s in profile.required_slots if s.name == slot_name), None)
        if slot:
            packet.uncertainties.append(f"Required evidence slot not filled: {slot.name}. {slot.description}")
