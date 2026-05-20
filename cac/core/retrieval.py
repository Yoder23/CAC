
from __future__ import annotations

from typing import List

from .schemas import SourceItem, TaskProfile, Candidate, normalize

# Task-specific retrieval queries.  Each query is tuned to the slot vocabulary of
# the corresponding task profile so that candidates carrying task-critical evidence
# (e.g. the counterparty dispute email in contract_termination) receive a higher
# keyword-overlap score even when they share few words with a generic renewal-risk query.
_TASK_QUERIES = {
    "contract_termination": (
        "contract termination clause breach cure period written notice counterparty dispute "
        "position payment default obligation uncured material breach exactly"
    ),
    "security_exception": (
        "security exception control gap compensating control business justification "
        "approval authority expiration review date saml audit log"
    ),
    "incident_postmortem": (
        "incident timeline customer impact root cause remediation commitment "
        "conflicting status crm minor escalation postmortem"
    ),
    "renewal_risk": (
        "renewal risk billing support CRM contract termination payment overdue "
        "escalation executive sponsor discount health"
    ),
}
_DEFAULT_QUERY = (
    "renewal risk billing support CRM contract termination payment overdue "
    "escalation executive sponsor discount health"
)


def keyword_overlap_score(query: str, item: SourceItem) -> float:
    q = set(normalize(query))
    d = set(normalize(" ".join([item.title, item.text, " ".join(item.topics), " ".join(item.risk_tags)])))
    if not q:
        return 0.0
    overlap = len(q & d) / len(q)
    entity_boost = 0.15 if item.entity.lower() in query.lower() else 0.0
    return min(1.0, overlap + entity_boost)


def candidate_pool(profile: TaskProfile, sources: List[SourceItem], max_candidates: int = 20) -> List[Candidate]:
    task_key = getattr(profile, "risk_profile", None) or getattr(profile, "answer_target", None) or ""
    base_query = _TASK_QUERIES.get(task_key, _DEFAULT_QUERY)
    query = f"{profile.task} {profile.entity} {base_query}"
    candidates: list[Candidate] = []
    for item in sources:
        if item.entity.lower() != profile.entity.lower():
            continue
        score = keyword_overlap_score(query, item)
        # Include weak near-matches too; this is important for distractor pressure.
        if score > 0.02:
            candidates.append(Candidate(item=item, candidate_score=round(score, 4)))
    candidates.sort(key=lambda c: c.candidate_score, reverse=True)
    return candidates[:max_candidates]
