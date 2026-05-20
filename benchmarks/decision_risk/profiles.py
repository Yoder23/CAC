from __future__ import annotations
from typing import Tuple
from cac.core.schemas import RequiredEvidenceSlot, SourceType, TaskProfile
TASKS = ("renewal_risk", "security_exception", "contract_termination", "incident_postmortem")

def task_slots(task_type: str) -> Tuple[RequiredEvidenceSlot, ...]:
    if task_type == "renewal_risk":
        return (RequiredEvidenceSlot("billing_status",(SourceType.BILLING,),all_topics=("billing",),any_topics=("payment","overdue")),RequiredEvidenceSlot("support_trend",(SourceType.SUPPORT,),all_topics=("support",),any_topics=("escalation","p1","outage")),RequiredEvidenceSlot("crm_health_status",(SourceType.CRM,),all_topics=("crm",),any_topics=("health","renewal")),RequiredEvidenceSlot("contract_terms",(SourceType.CONTRACT,),any_risk_tags=("termination","payment_default","obligation","cure"),exact_wording_required=True),RequiredEvidenceSlot("executive_signal",(SourceType.EMAIL,SourceType.CALL_NOTE),all_topics=("executive","renewal")))
    if task_type == "security_exception":
        return (RequiredEvidenceSlot("control_gap",(SourceType.SECURITY,),all_topics=("security",),any_topics=("gap","control")),RequiredEvidenceSlot("business_justification",(SourceType.EMAIL,SourceType.INTERNAL_NOTE),any_topics=("business","justification")),RequiredEvidenceSlot("compensating_control",(SourceType.SECURITY,SourceType.INTERNAL_NOTE),any_topics=("compensating","control")),RequiredEvidenceSlot("approval_authority",(SourceType.EMAIL,),any_risk_tags=("approval","authority"),exact_wording_required=True),RequiredEvidenceSlot("expiration_or_review_date",(SourceType.SECURITY,SourceType.INTERNAL_NOTE),any_topics=("expiration","review")))
    if task_type == "contract_termination":
        return (RequiredEvidenceSlot("termination_clause",(SourceType.CONTRACT,),any_risk_tags=("termination","cure","breach"),exact_wording_required=True),RequiredEvidenceSlot("breach_event",(SourceType.SUPPORT,SourceType.BILLING),any_risk_tags=("breach","payment_default","operational_signal")),RequiredEvidenceSlot("notice_or_cure_status",(SourceType.EMAIL,SourceType.CALL_NOTE),any_topics=("notice","cure")),RequiredEvidenceSlot("payment_status",(SourceType.BILLING,),all_topics=("billing",),any_topics=("payment","overdue")),RequiredEvidenceSlot("counterparty_position",(SourceType.EMAIL,SourceType.CALL_NOTE),any_topics=("counterparty","position"),exact_wording_required=True))
    if task_type == "incident_postmortem":
        return (RequiredEvidenceSlot("incident_timeline",(SourceType.SUPPORT,SourceType.INTERNAL_NOTE),any_topics=("timeline","incident")),RequiredEvidenceSlot("customer_impact",(SourceType.SUPPORT,SourceType.EMAIL),any_topics=("impact","customer")),RequiredEvidenceSlot("root_cause",(SourceType.INTERNAL_NOTE,SourceType.SECURITY),any_topics=("root","cause")),RequiredEvidenceSlot("remediation_commitment",(SourceType.EMAIL,SourceType.INTERNAL_NOTE),any_risk_tags=("commitment","remediation"),exact_wording_required=True),RequiredEvidenceSlot("conflicting_status",(SourceType.CRM,),any_topics=("status","conflict")))
    raise ValueError(task_type)

def build_task_profile(task_type: str, entity: str, budget: int) -> TaskProfile:
    prompts={"renewal_risk":"Assess renewal risk and cite evidence.","security_exception":"Assess security exception approval.","contract_termination":"Assess whether termination is supportable.","incident_postmortem":"Assess incident postmortem quality."}
    return TaskProfile(task=prompts[task_type],entity=entity,answer_target=task_type,token_budget=budget,risk_profile=task_type,required_slots=task_slots(task_type),slot_mode="task_slots")
