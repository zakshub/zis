"""Optional provider-neutral AI assistance for the deterministic ZIS core.

AI output is persisted only as an unreviewed candidate. It is never evidence,
memory, approval, execution, contradiction resolution, or hidden reasoning.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Protocol

from .contracts import ContractError, validate, validate_schema
from .identity import direct_identity_text_findings, enforce_identity_boundary
from .ids import deterministic_id
from .runtime import ClassicalRuntime
from .store import EvidenceStore, utc_now


ADAPTER_VERSION = "m5.v1"
OPENAI_ENDPOINT = "https://api.openai.com/v1/responses"
REQUEST_FIELDS = {
    "purpose", "task_type", "instruction", "context", "expected_output_schema",
    "context_references", "privacy_class", "external_transmission_approved",
    "timeout_seconds", "max_output_tokens", "model_id", "created_at",
}
HIDDEN_REASONING_KEYS = frozenset({
    "chain_of_thought",
    "chain-of-thought",
    "hidden_reasoning",
    "reasoning_trace",
    "internal_reasoning",
    "private_reasoning",
    "scratchpad",
    "internal_monologue",
})
HIDDEN_REASONING_PHRASES = (
    "chain of thought",
    "hidden reasoning",
    "reasoning trace",
    "internal reasoning",
    "private reasoning",
    "scratchpad",
    "internal monologue",
)
HIDDEN_REASONING_REQUEST_VERBS = (
    "show", "provide", "include", "return", "reveal", "expose", "write",
    "output", "give", "share", "record", "generate", "display", "list",
    "describe", "explain", "request", "want", "need",
)


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _unknown_usage() -> dict[str, int | None]:
    return {"input_tokens": None, "output_tokens": None, "total_tokens": None}


def _unknown_cost() -> dict[str, Any]:
    return {"status": "unknown", "amount": None, "currency": None, "pricing_version": None, "pricing_source": None}


def _contains_hidden_reasoning_key(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            str(key).strip().casefold() in HIDDEN_REASONING_KEYS
            or _contains_hidden_reasoning_key(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_hidden_reasoning_key(item) for item in value)
    return False


def _instruction_requests_hidden_reasoning(instruction: str) -> bool:
    normalized = re.sub(r"[_-]+", " ", instruction.casefold())
    phrases = "|".join(re.escape(phrase) for phrase in HIDDEN_REASONING_PHRASES)
    verbs = "|".join(re.escape(verb) for verb in HIDDEN_REASONING_REQUEST_VERBS)
    direct_request = rf"\b(?:{verbs})\b.{{0,100}}\b(?:{phrases})\b"
    passive_request = rf"\b(?:{phrases})\b.{{0,100}}\b(?:must|should|needs? to)\s+be\s+(?:included|returned|provided|shown|revealed|exposed|written|output|recorded|generated|displayed)\b"
    return bool(re.search(direct_request, normalized) or re.search(passive_request, normalized))


@dataclass(frozen=True)
class AIConfiguration:
    enabled: bool = False
    provider_id: str = "none"
    model_id: str = ""
    endpoint: str = OPENAI_ENDPOINT
    timeout_seconds: float = 30.0
    max_output_tokens: int = 512
    credential_environment_variable: str = "OPENAI_API_KEY"

    @classmethod
    def from_environment(cls) -> "AIConfiguration":
        enabled = os.environ.get("ZIS_AI_ENABLED", "false").strip().casefold() in {"1", "true", "yes", "on"}
        return cls(
            enabled=enabled,
            provider_id=os.environ.get("ZIS_AI_PROVIDER", "openai" if enabled else "none").strip() or "none",
            model_id=os.environ.get("ZIS_AI_MODEL", "").strip(),
            endpoint=os.environ.get("ZIS_AI_ENDPOINT", OPENAI_ENDPOINT).strip() or OPENAI_ENDPOINT,
            timeout_seconds=float(os.environ.get("ZIS_AI_TIMEOUT_SECONDS", "30")),
            max_output_tokens=int(os.environ.get("ZIS_AI_MAX_OUTPUT_TOKENS", "512")),
            credential_environment_variable="OPENAI_API_KEY",
        )


@dataclass(frozen=True)
class PricingEntry:
    provider_id: str
    model_id: str
    input_per_million: float
    output_per_million: float
    currency: str
    version: str
    source: str


@dataclass
class AdapterResult:
    status: str
    structured_output: dict[str, Any] | None = None
    finish_reason: str | None = None
    usage: dict[str, int | None] | None = None
    provider_reference: str | None = None
    error_category: str | None = None
    error_message: str | None = None


class ProviderInvocationError(RuntimeError):
    def __init__(self, category: str, safe_message: str):
        super().__init__(safe_message)
        self.category = category
        self.safe_message = safe_message


class AIProviderAdapter(Protocol):
    provider_id: str
    adapter_version: str
    requires_credential: bool

    def availability(self, configuration: AIConfiguration, credential: str | None) -> dict[str, Any]: ...

    def request(self, request_record: dict[str, Any], credential: str | None) -> AdapterResult: ...


class DisabledAIAdapter:
    provider_id = "none"
    adapter_version = ADAPTER_VERSION
    requires_credential = False

    def availability(self, configuration: AIConfiguration, credential: str | None) -> dict[str, Any]:
        return {"state": "disabled", "configured": False, "network_verified": False}

    def request(self, request_record: dict[str, Any], credential: str | None) -> AdapterResult:
        return AdapterResult(status="disabled", error_category="disabled", error_message="AI assistance is disabled.")


Transport = Callable[[str, dict[str, str], dict[str, Any], float], dict[str, Any]]


def _urllib_transport(url: str, headers: dict[str, str], payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=_canonical(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        if error.code in {401, 403}:
            raise ProviderInvocationError("authentication", "Provider authentication/configuration failed.") from error
        if error.code == 429:
            raise ProviderInvocationError("rate_limit", "Provider rate limit was reached.") from error
        if error.code >= 500:
            raise ProviderInvocationError("provider_server", "Provider server returned an error.") from error
        raise ProviderInvocationError("transport", "Provider request was rejected.") from error
    except (TimeoutError, socket.timeout) as error:
        raise ProviderInvocationError("timeout", "Provider request timed out.") from error
    except urllib.error.URLError as error:
        if isinstance(error.reason, (TimeoutError, socket.timeout)):
            raise ProviderInvocationError("timeout", "Provider request timed out.") from error
        raise ProviderInvocationError("transport", "Provider transport/network error.") from error
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ProviderInvocationError("invalid_provider_response", "Provider returned an invalid response envelope.") from error


class OpenAIResponsesAdapter:
    """Exactly one M5 real provider adapter, isolated behind an injected transport."""

    provider_id = "openai"
    adapter_version = ADAPTER_VERSION
    requires_credential = True

    def __init__(self, endpoint: str = OPENAI_ENDPOINT, transport: Transport | None = None):
        self.endpoint = endpoint
        self.transport = transport or _urllib_transport

    def availability(self, configuration: AIConfiguration, credential: str | None) -> dict[str, Any]:
        if not configuration.enabled:
            return {"state": "disabled", "configured": False, "network_verified": False}
        if not configuration.model_id or not credential:
            return {"state": "not_configured", "configured": False, "network_verified": False}
        return {"state": "available", "configured": True, "network_verified": False}

    @staticmethod
    def build_payload(request_record: dict[str, Any]) -> dict[str, Any]:
        selected_context = {
            "purpose": request_record["purpose"],
            "task_type": request_record["task_type"],
            "context": request_record["context"],
            "context_references": request_record["context_references"],
        }
        return {
            "model": request_record["model_id"],
            "instructions": (
                "Return only the requested concise structured output. Do not provide or expose chain-of-thought, "
                "hidden reasoning, credentials, or unrelated context. " + request_record["instruction"]
            ),
            "input": _canonical(selected_context),
            "max_output_tokens": request_record["max_output_tokens"],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "zis_structured_output",
                    "strict": True,
                    "schema": request_record["expected_output_schema"],
                }
            },
        }

    @staticmethod
    def _output_text(payload: dict[str, Any]) -> str:
        if isinstance(payload.get("output_text"), str):
            return payload["output_text"]
        for item in payload.get("output", []):
            if not isinstance(item, dict):
                continue
            for content in item.get("content", []):
                if isinstance(content, dict) and content.get("type") == "output_text" and isinstance(content.get("text"), str):
                    return content["text"]
        raise ProviderInvocationError("invalid_provider_response", "Provider response did not contain structured output text.")

    def request(self, request_record: dict[str, Any], credential: str | None) -> AdapterResult:
        if not credential:
            return AdapterResult(status="unavailable", error_category="not_configured", error_message="Provider credential is not configured.")
        payload = self.transport(
            self.endpoint,
            {"Authorization": f"Bearer {credential}", "Content-Type": "application/json"},
            self.build_payload(request_record),
            float(request_record["timeout_seconds"]),
        )
        if not isinstance(payload, dict):
            raise ProviderInvocationError("invalid_provider_response", "Provider returned an invalid response envelope.")
        try:
            structured = json.loads(self._output_text(payload))
        except json.JSONDecodeError as error:
            raise ProviderInvocationError("invalid_structured_output", "Provider structured output was malformed JSON.") from error
        if not isinstance(structured, dict):
            raise ProviderInvocationError("invalid_structured_output", "Provider structured output was not an object.")
        raw_usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
        usage = {
            "input_tokens": raw_usage.get("input_tokens") if isinstance(raw_usage.get("input_tokens"), int) else None,
            "output_tokens": raw_usage.get("output_tokens") if isinstance(raw_usage.get("output_tokens"), int) else None,
            "total_tokens": raw_usage.get("total_tokens") if isinstance(raw_usage.get("total_tokens"), int) else None,
        }
        return AdapterResult(
            status="success",
            structured_output=structured,
            finish_reason=payload.get("status") if isinstance(payload.get("status"), str) else None,
            usage=usage,
            provider_reference=payload.get("id") if isinstance(payload.get("id"), str) else None,
        )


class AIAdapterRegistry:
    def __init__(self, adapters: list[AIProviderAdapter] | None = None):
        defaults: list[AIProviderAdapter] = [DisabledAIAdapter(), OpenAIResponsesAdapter()]
        self._adapters = {adapter.provider_id: adapter for adapter in (adapters or defaults)}

    def register(self, adapter: AIProviderAdapter) -> None:
        self._adapters[adapter.provider_id] = adapter

    def get(self, provider_id: str) -> AIProviderAdapter | None:
        return self._adapters.get(provider_id)

    def providers(self) -> list[str]:
        return sorted(self._adapters)


class AIService:
    def __init__(
        self,
        store: EvidenceStore,
        configuration: AIConfiguration | None = None,
        registry: AIAdapterRegistry | None = None,
        pricing: list[PricingEntry] | None = None,
    ):
        self.store = store
        self.configuration = configuration or AIConfiguration.from_environment()
        self.registry = registry or AIAdapterRegistry()
        self.pricing = {(item.provider_id, item.model_id): item for item in (pricing or [])}

    def initialize(self) -> list[int]:
        return self.store.initialize()

    @staticmethod
    def _json_row(connection: Any, table: str, record_id: str) -> dict[str, Any] | None:
        row = connection.execute(f"SELECT record_json FROM {table} WHERE id=?", (record_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def _credential(self, adapter: AIProviderAdapter) -> str | None:
        if not adapter.requires_credential:
            return None
        return os.environ.get(self.configuration.credential_environment_variable)

    def _select_adapter(self) -> AIProviderAdapter | None:
        provider_id = self.configuration.provider_id if self.configuration.enabled else "none"
        return self.registry.get(provider_id)

    def provider_status(self) -> dict[str, Any]:
        adapter = self._select_adapter()
        if adapter is None:
            return {"provider_id": self.configuration.provider_id, "state": "unavailable", "configured": False, "network_verified": False, "reason": "unsupported_provider"}
        status = adapter.availability(self.configuration, self._credential(adapter))
        return {"provider_id": adapter.provider_id, "adapter_version": adapter.adapter_version, **status}

    def status(self) -> dict[str, Any]:
        self.initialize()
        with self.store.connect() as connection:
            counts = {
                "requests": int(connection.execute("SELECT COUNT(*) FROM ai_requests").fetchone()[0]),
                "responses": int(connection.execute("SELECT COUNT(*) FROM ai_responses").fetchone()[0]),
                "candidates": int(connection.execute("SELECT COUNT(*) FROM ai_candidates").fetchone()[0]),
            }
        core = ClassicalRuntime(self.store).health()
        return {"core_healthy": core["healthy"], "ai_optional": True, "ai": self.provider_status(), "counts": counts}

    @staticmethod
    def _validate_external_input(value: Any) -> None:
        enforce_identity_boundary(value)
        findings = direct_identity_text_findings(value)
        if findings:
            raise ValueError("AI input contains direct identity or credential signals: " + ", ".join(findings))

    def build_request(self, specification: dict[str, Any]) -> dict[str, Any]:
        extra = sorted(set(specification) - REQUEST_FIELDS)
        if extra:
            raise ValueError("unsupported AI request fields: " + ", ".join(extra))
        for required in ("purpose", "task_type", "instruction", "context", "expected_output_schema", "privacy_class"):
            if required not in specification or specification[required] in (None, ""):
                raise ValueError(f"AI request requires {required}")
        if specification.get("external_transmission_approved") is not True:
            raise ValueError("AI request requires explicit external_transmission_approved=true")
        if specification["privacy_class"] not in {"public", "internal"}:
            raise ValueError("private or restricted context cannot be sent to an external AI provider")
        if not isinstance(specification["context"], dict):
            raise ValueError("AI context must be a structured object")
        schema = specification["expected_output_schema"]
        if not isinstance(schema, dict) or schema.get("type") != "object":
            raise ValueError("expected_output_schema must describe an object")
        if _contains_hidden_reasoning_key(specification):
            raise ValueError("AI request contains a forbidden hidden-reasoning field name")
        if _instruction_requests_hidden_reasoning(specification["instruction"]):
            raise ValueError("AI instruction requests forbidden hidden reasoning")
        self._validate_external_input(specification)
        provider_id = self.configuration.provider_id if self.configuration.enabled else "none"
        model_id = str(specification.get("model_id") or self.configuration.model_id or "none")
        context_references = sorted(set(specification.get("context_references", [])))
        timeout_seconds = float(specification.get("timeout_seconds", self.configuration.timeout_seconds))
        max_output_tokens = int(specification.get("max_output_tokens", self.configuration.max_output_tokens))
        stable_prompt = {
            "purpose": specification["purpose"],
            "task_type": specification["task_type"],
            "provider_id": provider_id,
            "model_id": model_id,
            "instruction": specification["instruction"],
            "context": specification["context"],
            "expected_output_schema": schema,
            "context_references": context_references,
            "privacy_class": specification["privacy_class"],
            "external_transmission_approved": True,
            "timeout_seconds": timeout_seconds,
            "max_output_tokens": max_output_tokens,
            "version": 1,
        }
        fingerprint = _fingerprint(stable_prompt)
        created_at = specification.get("created_at") or utc_now()
        record = {
            "id": deterministic_id("aireq", {"prompt_fingerprint": fingerprint, "created_at": created_at, "version": 1}),
            **{key: stable_prompt[key] for key in ("purpose", "task_type", "provider_id", "model_id", "instruction", "context", "expected_output_schema", "context_references", "privacy_class", "external_transmission_approved", "timeout_seconds", "max_output_tokens")},
            "prompt_fingerprint": fingerprint,
            "created_at": created_at,
            "version": 1,
        }
        validate("ai-request", record)
        return record

    def _cost(self, provider_id: str, model_id: str, usage: dict[str, int | None]) -> dict[str, Any]:
        price = self.pricing.get((provider_id, model_id))
        if not price or usage["input_tokens"] is None or usage["output_tokens"] is None:
            return _unknown_cost()
        amount = (
            usage["input_tokens"] * price.input_per_million
            + usage["output_tokens"] * price.output_per_million
        ) / 1_000_000
        return {
            "status": "estimated",
            "amount": round(amount, 12),
            "currency": price.currency,
            "pricing_version": price.version,
            "pricing_source": price.source,
        }

    @staticmethod
    def _failure_result(error: ProviderInvocationError) -> AdapterResult:
        status = "timeout" if error.category == "timeout" else ("invalid_output" if error.category in {"invalid_provider_response", "invalid_structured_output"} else "provider_error")
        return AdapterResult(status=status, error_category=error.category, error_message=error.safe_message)

    def request_assistance(self, specification: dict[str, Any]) -> dict[str, Any]:
        request_record = self.build_request(specification)
        self.initialize()
        with self.store.connect() as connection:
            existing_response = connection.execute("SELECT record_json FROM ai_responses WHERE request_id=?", (request_record["id"],)).fetchone()
            if existing_response:
                response = json.loads(existing_response[0])
                candidate = self._json_row(connection, "ai_candidates", response["candidate_id"]) if response["candidate_id"] else None
                return {"request": self._json_row(connection, "ai_requests", request_record["id"]), "response": response, "candidate": candidate}

        adapter = self._select_adapter()
        started = time.monotonic()
        if adapter is None:
            result = AdapterResult(status="unavailable", error_category="unsupported_provider", error_message="Configured AI provider is not registered.")
            adapter_id, adapter_version = self.configuration.provider_id, ADAPTER_VERSION
        else:
            adapter_id, adapter_version = adapter.provider_id, adapter.adapter_version
            availability = adapter.availability(self.configuration, self._credential(adapter))
            if availability["state"] == "disabled":
                result = AdapterResult(status="disabled", error_category="disabled", error_message="AI assistance is disabled.")
            elif availability["state"] == "not_configured":
                result = AdapterResult(status="unavailable", error_category="not_configured", error_message="AI provider is not configured.")
            else:
                try:
                    result = adapter.request(request_record, self._credential(adapter))
                except ProviderInvocationError as error:
                    result = self._failure_result(error)
                except Exception:
                    result = AdapterResult(status="provider_error", error_category="transport", error_message="Provider transport/network error.")
        latency_ms = max(0, int((time.monotonic() - started) * 1000))
        usage = result.usage or _unknown_usage()
        usage = {name: usage.get(name) if isinstance(usage.get(name), int) else None for name in _unknown_usage()}

        if result.status == "success":
            try:
                if result.structured_output is None:
                    raise ContractError("structured output is missing")
                if _contains_hidden_reasoning_key(result.structured_output):
                    raise ContractError("structured output contains a forbidden hidden-reasoning field")
                self._validate_external_input(result.structured_output)
                validate_schema(result.structured_output, request_record["expected_output_schema"])
            except (ContractError, ValueError):
                result = AdapterResult(status="invalid_output", error_category="invalid_structured_output", error_message="Provider structured output failed validation.", usage=usage, provider_reference=result.provider_reference, finish_reason=result.finish_reason)

        output_fingerprint = _fingerprint(result.structured_output) if result.status == "success" and result.structured_output is not None else None
        response_material = {"request_id": request_record["id"], "provider_id": adapter_id, "status": result.status, "output_fingerprint": output_fingerprint, "provider_reference": result.provider_reference, "version": 1}
        response_id = deterministic_id("airesp", response_material)
        candidate = None
        candidate_id = None
        if result.status == "success" and result.structured_output is not None:
            candidate_id = deterministic_id("aicand", {"request_id": request_record["id"], "response_id": response_id, "output_fingerprint": output_fingerprint, "version": 1})
            candidate = {
                "id": candidate_id,
                "request_id": request_record["id"],
                "response_id": response_id,
                "provider_id": adapter_id,
                "model_id": request_record["model_id"],
                "purpose": request_record["purpose"],
                "context_references": request_record["context_references"],
                "output": result.structured_output,
                "review_state": "pending_review",
                "truth_status": "ai_candidate_not_truth",
                "provenance": {"method": "provider_generated_candidate", "actor": adapter_id, "chain": [request_record["id"], response_id, *request_record["context_references"]]},
                "created_at": utc_now(),
                "version": 1,
            }
            validate("ai-candidate", candidate)

        response = {
            "id": response_id,
            "request_id": request_record["id"],
            "provider_id": adapter_id,
            "model_id": request_record["model_id"],
            "adapter_version": adapter_version,
            "status": result.status,
            "structured_output": result.structured_output if result.status == "success" else None,
            "text_output": None,
            "finish_reason": result.finish_reason,
            "usage": usage,
            "cost": self._cost(adapter_id, request_record["model_id"], usage),
            "latency_ms": latency_ms,
            "provider_reference": result.provider_reference,
            "error_category": result.error_category,
            "error_message": result.error_message,
            "output_fingerprint": output_fingerprint,
            "candidate_id": candidate_id,
            "provenance": {"method": "normalized_provider_response", "actor": adapter_id, "chain": [request_record["id"]]},
            "created_at": utc_now(),
            "version": 1,
        }
        validate("ai-response", response)
        enforce_identity_boundary(response)

        audit_metadata = {
            "request_id": request_record["id"],
            "response_id": response_id,
            "provider_id": adapter_id,
            "model_id": request_record["model_id"],
            "purpose": request_record["purpose"],
            "outcome": response["status"],
            "latency_ms": latency_ms,
            "usage": usage,
            "cost": response["cost"],
            "candidate_id": candidate_id,
            "error_category": response["error_category"],
            "prompt_fingerprint": request_record["prompt_fingerprint"],
        }
        with self.store.connect() as connection:
            connection.execute(
                "INSERT INTO ai_requests(id,record_json,purpose,task_type,provider_id,model_id,privacy_class,prompt_fingerprint,created_at,version) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (request_record["id"], _canonical(request_record), request_record["purpose"], request_record["task_type"], request_record["provider_id"], request_record["model_id"], request_record["privacy_class"], request_record["prompt_fingerprint"], request_record["created_at"], 1),
            )
            connection.execute(
                "INSERT INTO ai_responses(id,record_json,request_id,provider_id,model_id,status,error_category,candidate_id,created_at,version) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (response["id"], _canonical(response), response["request_id"], response["provider_id"], response["model_id"], response["status"], response["error_category"], response["candidate_id"], response["created_at"], 1),
            )
            if candidate:
                connection.execute(
                    "INSERT INTO ai_candidates(id,record_json,request_id,response_id,review_state,created_at,version) VALUES (?,?,?,?,?,?,?)",
                    (candidate["id"], _canonical(candidate), candidate["request_id"], candidate["response_id"], candidate["review_state"], candidate["created_at"], 1),
                )
            self.store._audit(connection, "ai.interaction_recorded", "ai_response", response_id, audit_metadata)
        return {"request": request_record, "response": response, "candidate": candidate}

    def request_cognitive_assistance(self, session_id: str, specification: dict[str, Any]) -> dict[str, Any]:
        from .cognition import CognitiveEngine

        CognitiveEngine(self.store).session_result(session_id)
        bounded = dict(specification)
        bounded["context_references"] = sorted(set([*bounded.get("context_references", []), session_id]))
        return self.request_assistance(bounded)

    def list_records(self, family: str) -> list[dict[str, Any]]:
        tables = {"requests": "ai_requests", "responses": "ai_responses", "candidates": "ai_candidates"}
        if family not in tables:
            raise ValueError(f"unknown AI record family: {family}")
        self.initialize()
        with self.store.connect() as connection:
            return [json.loads(row[0]) for row in connection.execute(f"SELECT record_json FROM {tables[family]} ORDER BY id")]

    def get_record(self, family: str, record_id: str) -> dict[str, Any]:
        tables = {"requests": "ai_requests", "responses": "ai_responses", "candidates": "ai_candidates"}
        if family not in tables:
            raise ValueError(f"unknown AI record family: {family}")
        self.initialize()
        with self.store.connect() as connection:
            record = self._json_row(connection, tables[family], record_id)
            if not record:
                raise KeyError(record_id)
            return record

    def snapshot(self) -> dict[str, list[dict[str, Any]]]:
        return {family: self.list_records(family) for family in ("requests", "responses", "candidates")}
