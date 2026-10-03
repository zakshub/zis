# SpecialistManifest

Machine contract: `SpecialistManifest.schema.json`. M3 implements registry storage and lifecycle only; no specialist is invoked or integrated through federation.

Required fields:

id

name

domain

purpose

capabilities

input_contract

output_contract

interface_version

compatible_runtime_versions

when_to_use

when_not_to_use

maturity

location

invocation_modes

health_check

security_boundary

fallback

provenance_requirement

owner_approval_required_for_changes

status

availability

confidence

provenance

created_at

updated_at

source_references

version

Invariant: registering a repository does not copy its knowledge into ZIS and does not authorize invocation.
