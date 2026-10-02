# CapabilityProposal

Required fields:

id

created_at

observed_need

evidence_ids

current_capabilities_checked

problem_frequency

problem_severity

proposed_solution_level

alternatives

expected_value

implementation_cost

maintenance_cost

privacy_impact

security_impact

architecture_summary

reversibility

approval_status

approval_record

post_build_review

Allowed solution levels:

no_action

reasoning_only

research_only

existing_capability

extend_existing

small_tool

product

system

new_specialist_intelligence

Invariant: persistent creation cannot start while approval status is pending or rejected.