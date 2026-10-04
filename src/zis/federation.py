"""Explicit, governed specialist federation without embedded specialist expertise."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any, Protocol

from . import __version__
from .contracts import ContractError, validate, validate_schema
from .identity import direct_identity_text_findings, enforce_identity_boundary
from .ids import deterministic_id
from .runtime import ClassicalRuntime
from .store import EvidenceStore, utc_now


REQUEST_CONTRACT_VERSION = "1.0"
RESPONSE_CONTRACT_VERSION = "1.0"
FEDERATION_VERSION = "m6.v1"
MANIFEST_CREATED_AT = "2026-10-04T00:00:00Z"
REQUEST_FIELDS = {
    "specialist_id", "action", "purpose", "requested_capability",
    "structured_input", "context_references", "privacy_class",
    "context_forwarding_approved", "approval_id", "timeout_seconds", "created_at",
}
TAX_SUBMISSION_ACTIONS = frozenset({"submit_tax_return", "submit_filing", "file_tax_return", "iris_submit"})
TAX_HIGH_IMPACT_ACTIONS = frozenset({"prepare_filing", "tax_reconciliation", "filing_preparation"})
RESPONSE_STATUSES = frozenset({"success", "unavailable", "incompatible", "timeout", "specialist_error", "invalid_output", "rejected", "disabled"})


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


@dataclass
class SpecialistAdapterResult:
    status: str
    structured_output: dict[str, Any] | None = None
    warnings: list[str] | None = None
    limitations: list[str] | None = None
    trace_id: str | None = None
    error_category: str | None = None
    error_message: str | None = None


class SpecialistInvocationError(RuntimeError):
    def __init__(self, category: str, safe_message: str):
        super().__init__(safe_message)
        self.category = category
        self.safe_message = safe_message


class SpecialistAdapter(Protocol):
    specialist_id: str
    adapter_version: str
    request_contract_version: str
    response_contract_version: str
    output_schema: dict[str, Any]

    def availability(self, manifest: dict[str, Any]) -> dict[str, Any]: ...
    def compatibility(self, manifest: dict[str, Any], runtime_version: str) -> dict[str, Any]: ...
    def request(self, request_record: dict[str, Any]) -> SpecialistAdapterResult: ...


class MetadataOnlySpecialistAdapter:
    adapter_version = FEDERATION_VERSION
    request_contract_version = REQUEST_CONTRACT_VERSION
    response_contract_version = RESPONSE_CONTRACT_VERSION
    output_schema = {"type": "object"}

    def __init__(self, specialist_id: str, reason: str):
        self.specialist_id = specialist_id
        self.reason = reason

    def availability(self, manifest: dict[str, Any]) -> dict[str, Any]:
        return {"state": "not_configured", "reason": self.reason, "destructive": False}

    def compatibility(self, manifest: dict[str, Any], runtime_version: str) -> dict[str, Any]:
        return _compatibility(manifest, self, runtime_version)

    def request(self, request_record: dict[str, Any]) -> SpecialistAdapterResult:
        return SpecialistAdapterResult(status="unavailable", error_category="not_configured", error_message=self.reason)


class SpecialistAdapterRegistry:
    def __init__(self, adapters: list[SpecialistAdapter] | None = None):
        self._adapters: dict[str, SpecialistAdapter] = {}
        for adapter in adapters or []:
            self.register(adapter)

    def register(self, adapter: SpecialistAdapter) -> None:
        if adapter.specialist_id in self._adapters:
            raise ValueError(f"specialist adapter already registered: {adapter.specialist_id}")
        self._adapters[adapter.specialist_id] = adapter

    def get(self, specialist_id: str) -> SpecialistAdapter | None:
        return self._adapters.get(specialist_id)

    def ids(self) -> list[str]:
        return sorted(self._adapters)


def _compatibility(manifest: dict[str, Any], adapter: SpecialistAdapter, runtime_version: str) -> dict[str, Any]:
    runtime_line = runtime_version.rsplit(".", 1)[0]
    required = {
        "runtime": runtime_line,
        "request_contract": manifest.get("request_contract_version"),
        "response_contract": manifest.get("response_contract_version"),
    }
    available = {
        "runtime": manifest.get("compatible_runtime_versions", []),
        "request_contract": adapter.request_contract_version,
        "response_contract": adapter.response_contract_version,
    }
    compatible = (
        runtime_line in available["runtime"]
        and required["request_contract"] == available["request_contract"]
        and required["response_contract"] == available["response_contract"]
    )
    return {"compatible": compatible, "required": required, "available": available}


def _manifest(
    specialist_id: str,
    name: str,
    domain: str,
    purpose: str,
    capabilities: list[str],
    repository: str,
    limitation: str,
) -> dict[str, Any]:
    return {
        "id": specialist_id,
        "name": name,
        "domain": domain,
        "purpose": purpose,
        "capabilities": capabilities,
        "input_contract": "SpecialistRequest/1.0",
        "output_contract": "SpecialistResponse/1.0",
        "interface_version": "metadata-1",
        "compatible_runtime_versions": ["0.6"],
        "when_to_use": [f"Explicit, bounded request in the {domain} domain after a callable adapter is approved."],
        "when_not_to_use": [limitation],
        "maturity": "working",
        "location": repository,
        "invocation_modes": ["repository"],
        "health_check": "Metadata-only registration; no destructive or full-job health request.",
        "security_boundary": "Explicit public/internal structured context only; no identity, secrets, raw database or hidden history.",
        "fallback": "Return unavailable; do not substitute another specialist automatically.",
        "provenance_requirement": "Return an M6 execution provenance receipt for every successful response.",
        "owner_approval_required_for_changes": True,
        "status": "proposed",
        "availability": "unknown",
        "request_contract_version": REQUEST_CONTRACT_VERSION,
        "response_contract_version": RESPONSE_CONTRACT_VERSION,
        "adapter_type": "metadata_only",
        "health_state": "not_configured",
        "privacy_classification": "internal",
        "invocation_policy": "Explicit invocation only; unavailable until a stable specialist task interface is separately approved.",
        "confidence": "strong",
        "provenance": {"method": "m6_repository_interface_review", "actor": "owner_approved_implementation", "chain": [repository]},
        "created_at": MANIFEST_CREATED_AT,
        "updated_at": MANIFEST_CREATED_AT,
        "source_references": [repository],
        "version": 1,
    }


BUILTIN_MANIFESTS = (
    _manifest("sp_designer", "Designer", "UX, product design, interaction architecture, design systems and Figma-oriented design intelligence", "Provide specialist design judgment without copying design expertise into ZIS.", ["ux_ui", "product_design", "interaction_architecture", "design_systems", "figma_design", "implementation_aware_design"], "https://github.com/zakshub/designer", "Do not use as a generic task executor; the current API governs knowledge records rather than design jobs."),
    _manifest("sp_studio", "Studio", "imagery, photography, image generation and editing, cinematic realism and visual production", "Provide governed visual-production intelligence outside ZIS core.", ["image_generation", "image_editing", "photographic_realism", "visual_production", "source_preservation", "quality_control"], "https://github.com/zakshub/studio", "Do not claim execution; the current intelligence API skeleton has no implemented executor boundary."),
    _manifest("sp_seo", "SEO", "keyword and niche research, opportunity validation, SERP and market intelligence, web venture workflows", "Provide web-market specialist results without embedding SEO logic in ZIS.", ["niche_research", "opportunity_validation", "serp_intelligence", "market_intelligence", "web_venture_research"], "https://github.com/zakshub/seo", "Do not invoke without its separately operated authenticated multi-service runtime and an approved federation contract."),
    _manifest("sp_taxbot", "TaxBot", "Pakistan income tax, IRIS workflow, reconciliation, tax-record processing and filing preparation", "Provide bounded tax preparation support while preserving human authority over filing.", ["tax_reconciliation", "filing_preparation", "tax_record_processing", "iris_workflow_review"], "https://github.com/zakshub/taxbot", "Never submit a tax filing; the current CLI exposes storage and recovery only."),
)


def default_registry() -> SpecialistAdapterRegistry:
    reasons = {
        "sp_designer": "Designer has no approved generic design-task invocation endpoint.",
        "sp_studio": "Studio execution is not implemented behind a stable authenticated contract.",
        "sp_seo": "SEO federation requires an approved adapter and separately configured runtime.",
        "sp_taxbot": "TaxBot exposes no approved tax-analysis or filing invocation endpoint.",
    }
    return SpecialistAdapterRegistry([MetadataOnlySpecialistAdapter(key, value) for key, value in reasons.items()])


class SpecialistFederation:
    def __init__(self, store: EvidenceStore, adapters: SpecialistAdapterRegistry | None = None):
        self.store = store
        self.runtime = ClassicalRuntime(store)
        self.adapters = adapters or default_registry()

    def initialize(self) -> list[str]:
        self.store.initialize()
        existing = {item["id"] for item in self.runtime.list_specialists()}
        added: list[str] = []
        for manifest in BUILTIN_MANIFESTS:
            if manifest["id"] not in existing:
                self.runtime.register_specialist(dict(manifest))
                added.append(manifest["id"])
        return added

    @staticmethod
    def zist_evaluation() -> dict[str, Any]:
        return {
            "candidate": "ZIST",
            "decision": "deferred_not_registered",
            "reason": "No local checkout or verified stable privacy-scoped invocation interface was available; its archive/corpus boundary also needs owner review before M7.",
            "source_references": ["https://github.com/zakshub/zist", "docs/09_REPOSITORY_CAPABILITY_MAP.md"],
            "version": 1,
        }

    @staticmethod
    def _validate_input(value: Any) -> None:
        enforce_identity_boundary(value)
        findings = direct_identity_text_findings(value)
        if findings:
            raise ValueError("specialist request contains direct identity or credential signals: " + ", ".join(findings))

    def build_request(self, specification: dict[str, Any]) -> dict[str, Any]:
        extra = sorted(set(specification) - REQUEST_FIELDS)
        if extra:
            raise ValueError("unsupported specialist request fields: " + ", ".join(extra))
        for name in ("specialist_id", "action", "purpose", "requested_capability", "structured_input", "privacy_class"):
            if name not in specification or specification[name] in (None, ""):
                raise ValueError(f"specialist request requires {name}")
        if not isinstance(specification["structured_input"], dict):
            raise ValueError("specialist structured_input must be an object")
        if specification.get("context_forwarding_approved") is not True:
            raise ValueError("specialist request requires context_forwarding_approved=true")
        if specification["privacy_class"] not in {"public", "internal"}:
            raise ValueError("private or restricted context cannot cross the specialist boundary")
        self._validate_input(specification)
        self.initialize()
        manifest = self.runtime.get_specialist(specification["specialist_id"])
        if specification["requested_capability"] not in manifest["capabilities"]:
            raise ValueError("requested capability is not declared by the specialist manifest")
        action = str(specification["action"])
        if manifest["id"] == "sp_taxbot" and action in TAX_SUBMISSION_ACTIONS:
            raise ValueError("tax filing/submission is not implemented")
        references = sorted(set(specification.get("context_references", [])))
        timeout = float(specification.get("timeout_seconds", 30.0))
        stable = {
            "specialist_id": manifest["id"], "action": action, "purpose": specification["purpose"],
            "requested_capability": specification["requested_capability"], "structured_input": specification["structured_input"],
            "context_references": references, "privacy_class": specification["privacy_class"],
            "context_forwarding_approved": True, "approval_id": specification.get("approval_id"),
            "timeout_seconds": timeout, "request_contract_version": REQUEST_CONTRACT_VERSION,
            "response_contract_version": RESPONSE_CONTRACT_VERSION, "version": 1,
        }
        fingerprint = _fingerprint(stable)
        created_at = specification.get("created_at") or utc_now()
        record = {
            "id": deterministic_id("spreq", {"input_fingerprint": fingerprint, "created_at": created_at, "version": 1}),
            **stable, "input_fingerprint": fingerprint, "created_at": created_at,
        }
        validate("specialist-request", record)
        return record

    def _authorization(self, request: dict[str, Any]) -> None:
        if request["specialist_id"] == "sp_taxbot" and request["action"] in TAX_HIGH_IMPACT_ACTIONS:
            self.runtime.authorize(request.get("approval_id") or "", "specialist.invoke.high_impact", "sp_taxbot", request["action"])

    def health(self, specialist_id: str | None = None) -> dict[str, Any]:
        self.store.initialize()
        manifests = [self.runtime.get_specialist(specialist_id)] if specialist_id else self.runtime.list_specialists()
        results: dict[str, Any] = {}
        for manifest in manifests:
            adapter = self.adapters.get(manifest["id"])
            compatibility = adapter.compatibility(manifest, __version__) if adapter else {"compatible": False, "required": {}, "available": {}}
            availability = adapter.availability(manifest) if adapter else {"state": "not_configured", "reason": "No adapter is registered.", "destructive": False}
            if not compatibility["compatible"]:
                availability = {"state": "incompatible", "reason": "Contract or runtime version mismatch.", "destructive": False}
            elif manifest["status"] == "retired":
                availability = {"state": "disabled", "reason": "Specialist is retired.", "destructive": False}
            results[manifest["id"]] = {
                "registered": True, "registry_status": manifest["status"], "registry_availability": manifest["availability"],
                "adapter_registered": adapter is not None, "availability": availability, "compatibility": compatibility,
                "last_successful_interaction": self._last_success(manifest["id"]),
            }
        return {"core_healthy": self.runtime.health()["healthy"], "specialists_optional": True, "specialists": results}

    def _last_success(self, specialist_id: str) -> str | None:
        with self.store.connect() as connection:
            row = connection.execute("SELECT created_at FROM specialist_responses WHERE specialist_id=? AND status='success' ORDER BY created_at DESC LIMIT 1", (specialist_id,)).fetchone()
            return row[0] if row else None

    def invoke(self, specification: dict[str, Any]) -> dict[str, Any]:
        request_record = self.build_request(specification)
        manifest = self.runtime.get_specialist(request_record["specialist_id"])
        with self.store.connect() as connection:
            existing = connection.execute("SELECT record_json FROM specialist_responses WHERE request_id=?", (request_record["id"],)).fetchone()
            if existing:
                response = json.loads(existing[0])
                receipt = None
                if response["provenance_receipt_id"]:
                    receipt = json.loads(connection.execute("SELECT record_json FROM specialist_provenance_receipts WHERE id=?", (response["provenance_receipt_id"],)).fetchone()[0])
                return {"request": json.loads(connection.execute("SELECT record_json FROM specialist_requests WHERE id=?", (request_record["id"],)).fetchone()[0]), "response": response, "provenance_receipt": receipt}

        adapter = self.adapters.get(manifest["id"])
        started = time.monotonic()
        compatibility = adapter.compatibility(manifest, __version__) if adapter else {"compatible": False, "required": {}, "available": {}}
        if not compatibility["compatible"]:
            result = SpecialistAdapterResult("incompatible", error_category="version_mismatch", error_message=f"Required versus available versions: {_canonical(compatibility)}")
            adapter_version = adapter.adapter_version if adapter else FEDERATION_VERSION
        elif manifest["status"] == "retired":
            result = SpecialistAdapterResult("disabled", error_category="disabled", error_message="Specialist is retired.")
            adapter_version = adapter.adapter_version if adapter else FEDERATION_VERSION
        elif manifest["status"] != "available" or manifest["availability"] != "available":
            state = adapter.availability(manifest) if adapter else {"state": "not_configured", "reason": "No adapter is registered."}
            result = SpecialistAdapterResult("disabled" if state["state"] == "disabled" else "unavailable", error_category=state["state"], error_message=state.get("reason") or "Specialist is unavailable.")
            adapter_version = adapter.adapter_version if adapter else FEDERATION_VERSION
        else:
            self._authorization(request_record)
            state = adapter.availability(manifest) if adapter else {"state": "not_configured", "reason": "No adapter is registered."}
            adapter_version = adapter.adapter_version if adapter else FEDERATION_VERSION
            if state["state"] != "available":
                result = SpecialistAdapterResult("disabled" if state["state"] == "disabled" else "unavailable", error_category=state["state"], error_message=state.get("reason") or "Specialist adapter is unavailable.")
            else:
                try:
                    result = adapter.request(request_record)
                except SpecialistInvocationError as error:
                    status = "timeout" if error.category == "timeout" else "specialist_error"
                    result = SpecialistAdapterResult(status, error_category=error.category, error_message=error.safe_message)
                except Exception:
                    result = SpecialistAdapterResult("specialist_error", error_category="transport", error_message="Specialist transport or process failed.")
        latency_ms = max(0, int((time.monotonic() - started) * 1000))
        warnings = list(result.warnings or [])
        limitations = list(result.limitations or [])
        if result.status not in RESPONSE_STATUSES:
            result = SpecialistAdapterResult("invalid_output", error_category="invalid_adapter_result", error_message="Specialist adapter returned an unsupported outcome.")
            warnings, limitations = [], []
        if result.status == "success":
            try:
                if result.structured_output is None:
                    raise ContractError("structured output is missing")
                self._validate_input({"output": result.structured_output, "warnings": warnings, "limitations": limitations, "trace_id": result.trace_id})
                validate_schema(result.structured_output, adapter.output_schema)
            except (ContractError, ValueError):
                result = SpecialistAdapterResult("invalid_output", error_category="invalid_structured_output", error_message="Specialist output failed its registered response contract.")
                warnings, limitations = [], []
        elif direct_identity_text_findings({"warnings": warnings, "limitations": limitations, "trace_id": result.trace_id, "error": result.error_message}):
            result = SpecialistAdapterResult(result.status, error_category=result.error_category, error_message="Specialist returned a redacted unsafe error detail.")
            warnings, limitations = [], []

        output_fingerprint = _fingerprint(result.structured_output) if result.status == "success" and result.structured_output is not None else None
        response_id = deterministic_id("spresp", {"request_id": request_record["id"], "status": result.status, "output_fingerprint": output_fingerprint, "version": 1})
        created_at = utc_now()
        receipt = None
        receipt_id = None
        if output_fingerprint:
            receipt_id = deterministic_id("spreceipt", {"request_id": request_record["id"], "response_id": response_id, "output_fingerprint": output_fingerprint, "version": 1})
            receipt = {
                "id": receipt_id, "specialist_id": manifest["id"], "specialist_version": manifest["interface_version"],
                "request_id": request_record["id"], "response_id": response_id, "capability": request_record["requested_capability"],
                "action": request_record["action"], "context_references": request_record["context_references"], "executed_at": created_at,
                "adapter_version": adapter_version, "output_fingerprint": output_fingerprint, "warnings": warnings,
                "limitations": limitations, "trace_id": result.trace_id, "version": 1,
            }
            validate("specialist-receipt", receipt)
            self._validate_input(receipt)
        response = {
            "id": response_id, "request_id": request_record["id"], "specialist_id": manifest["id"],
            "specialist_version": manifest["interface_version"], "adapter_version": adapter_version, "status": result.status,
            "structured_output": result.structured_output if result.status == "success" else None,
            "warnings": warnings, "limitations": limitations, "provenance_receipt_id": receipt_id, "latency_ms": latency_ms,
            "error_category": result.error_category, "error_message": result.error_message, "created_at": created_at, "version": 1,
        }
        validate("specialist-response", response)
        self._validate_input(response)
        audit = {
            "request_id": request_record["id"], "response_id": response_id, "specialist_id": manifest["id"],
            "capability": request_record["requested_capability"], "action": request_record["action"], "outcome": response["status"],
            "latency_ms": latency_ms, "compatible": compatibility["compatible"], "provenance_receipt_id": receipt_id,
            "error_category": response["error_category"], "input_fingerprint": request_record["input_fingerprint"],
        }
        with self.store.connect() as connection:
            connection.execute("INSERT INTO specialist_requests(id,record_json,specialist_id,action,requested_capability,privacy_class,input_fingerprint,created_at,version) VALUES (?,?,?,?,?,?,?,?,?)", (request_record["id"], _canonical(request_record), request_record["specialist_id"], request_record["action"], request_record["requested_capability"], request_record["privacy_class"], request_record["input_fingerprint"], request_record["created_at"], 1))
            connection.execute("INSERT INTO specialist_responses(id,record_json,request_id,specialist_id,status,error_category,provenance_receipt_id,created_at,version) VALUES (?,?,?,?,?,?,?,?,?)", (response["id"], _canonical(response), response["request_id"], response["specialist_id"], response["status"], response["error_category"], receipt_id, response["created_at"], 1))
            if receipt:
                connection.execute("INSERT INTO specialist_provenance_receipts(id,record_json,request_id,response_id,specialist_id,output_fingerprint,executed_at,version) VALUES (?,?,?,?,?,?,?,?)", (receipt["id"], _canonical(receipt), receipt["request_id"], receipt["response_id"], receipt["specialist_id"], receipt["output_fingerprint"], receipt["executed_at"], 1))
            self.store._audit(connection, "specialist.interaction_recorded", "specialist_response", response_id, audit)
        return {"request": request_record, "response": response, "provenance_receipt": receipt}

    def list_records(self, family: str) -> list[dict[str, Any]]:
        tables = {"requests": "specialist_requests", "responses": "specialist_responses", "receipts": "specialist_provenance_receipts"}
        if family not in tables:
            raise ValueError(f"unknown specialist record family: {family}")
        self.store.initialize()
        with self.store.connect() as connection:
            return [json.loads(row[0]) for row in connection.execute(f"SELECT record_json FROM {tables[family]} ORDER BY id")]

    def snapshot(self) -> dict[str, Any]:
        self.store.initialize()
        return {
            "registry": self.runtime.list_specialists(),
            "requests": self.list_records("requests"),
            "responses": self.list_records("responses"),
            "receipts": self.list_records("receipts"),
            "zist_evaluation": self.zist_evaluation(),
        }
