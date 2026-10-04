"""Local deterministic ZIS command-line interface."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from . import __version__
from .backup import create_backup, restore_backup, verify_backup
from .cognition import CognitiveEngine
from .contracts import CONTRACTS, ContractError, validate
from .export import export_store
from .migration import REVIEW_DECISIONS, SOURCE_REPOSITORY, ZOSMigrationStore, dry_run, load_candidate_specifications
from .records import build_evidence
from .runtime import ClassicalRuntime, build_approval_record
from .store import EvidenceStore


def _store(args: argparse.Namespace) -> EvidenceStore:
    return EvidenceStore(args.database)


def _migration_store(args: argparse.Namespace) -> ZOSMigrationStore:
    return ZOSMigrationStore(_store(args))


def _runtime(args: argparse.Namespace) -> ClassicalRuntime:
    return ClassicalRuntime(_store(args))


def _cognition(args: argparse.Namespace) -> CognitiveEngine:
    return CognitiveEngine(_store(args))


def _print_json(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def cmd_init(args: argparse.Namespace) -> None:
    applied = _store(args).initialize()
    _print_json({"database": str(_store(args).path), "schema_version": _store(args).schema_version(), "migrations_applied": applied})


def cmd_status(args: argparse.Namespace) -> None:
    store = _store(args)
    store.initialize()
    _print_json({"version": __version__, "database": str(store.path), "schema_version": store.schema_version(), "evidence_records": len(store.list_evidence()), "contradictions": len(store.list_contradictions()), "audit_events": len(store.audit_events()), "ai_required": False})


def cmd_validate(args: argparse.Namespace) -> None:
    document = json.loads(Path(args.file).read_text(encoding="utf-8"))
    validate(args.contract, document)
    print(f"valid {args.contract}: {args.file}")


def cmd_evidence_add(args: argparse.Namespace) -> None:
    record = build_evidence(content=args.content, record_type=args.type, source_type=args.source_type, source_reference=args.source_reference, scope=args.scope, confidence=args.confidence, observed_at=args.observed_at, valid_from=args.valid_from, valid_until=args.valid_until, privacy_class=args.privacy_class, provenance_method=args.provenance_method, provenance_actor=args.provenance_actor, source_references=args.source_reference_extra, supersedes=args.supersedes)
    _print_json(_store(args).add_evidence(record))


def cmd_evidence_list(args: argparse.Namespace) -> None:
    rows = _store(args).list_evidence(args.status, args.scope)
    if args.json:
        _print_json(rows)
        return
    for row in rows:
        print(f"{row['id']}  {row['record_type']:<16} {row['confidence']:<11} {row['status']:<10} {row['scope']}  {row['content']}")


def cmd_evidence_show(args: argparse.Namespace) -> None:
    record = _store(args).get_evidence(args.id)
    if not record:
        raise SystemExit(f"evidence not found: {args.id}")
    _print_json(record)


def cmd_evidence_status(args: argparse.Namespace) -> None:
    _print_json(_store(args).set_evidence_status(args.id, args.status))


def cmd_contradiction_add(args: argparse.Namespace) -> None:
    _print_json(_store(args).add_contradiction(args.evidence_id_a, args.evidence_id_b))


def cmd_contradiction_resolve(args: argparse.Namespace) -> None:
    _print_json(_store(args).resolve_contradiction(args.id, args.rationale, args.source_reference))


def cmd_contradictions(args: argparse.Namespace) -> None:
    _print_json(_store(args).list_contradictions())


def cmd_export(args: argparse.Namespace) -> None:
    _print_json({name: str(path) for name, path in export_store(_store(args), args.destination).items()})


def cmd_zos_scan(args: argparse.Namespace) -> None:
    _print_json(_migration_store(args).scan(args.source_root, args.source_ref, args.paths, args.source_repository))


def cmd_zos_inventory(args: argparse.Namespace) -> None:
    migration = _migration_store(args)
    _print_json(migration.get_source(args.id) if args.id else migration.list_sources())


def cmd_zos_candidate_add(args: argparse.Namespace) -> None:
    specification = json.loads(Path(args.file).read_text(encoding="utf-8"))
    _print_json(_migration_store(args).create_candidate(specification))


def cmd_zos_candidates(args: argparse.Namespace) -> None:
    migration = _migration_store(args)
    _print_json(migration.review_packet(args.id) if args.id else migration.list_candidates(args.review_status))


def cmd_zos_review(args: argparse.Namespace) -> None:
    _print_json(_migration_store(args).review_candidate(args.id, args.decision, args.note))


def cmd_zos_approve(args: argparse.Namespace) -> None:
    _print_json(_migration_store(args).review_candidate(args.id, "approve", args.note))


def cmd_zos_reject(args: argparse.Namespace) -> None:
    _print_json(_migration_store(args).review_candidate(args.id, "reject", args.note))


def cmd_zos_import(args: argparse.Namespace) -> None:
    migration = _migration_store(args)
    _print_json(migration.import_candidate(args.id) if args.id else migration.import_approved())


def cmd_zos_status(args: argparse.Namespace) -> None:
    _print_json(_migration_store(args).status())


def cmd_zos_dry_run(args: argparse.Namespace) -> None:
    specifications = load_candidate_specifications(args.candidate_file)
    _print_json(dry_run(args.source_root, args.source_ref, args.paths, specifications, args.source_repository))


def _load_json_file(path: str) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def cmd_runtime_status(args: argparse.Namespace) -> None:
    _print_json(_runtime(args).status())


def cmd_runtime_operations(args: argparse.Namespace) -> None:
    _print_json(_runtime(args).list_operations())


def cmd_source_add(args: argparse.Namespace) -> None:
    _print_json(_runtime(args).register_source(_load_json_file(args.file)))


def cmd_source_list(args: argparse.Namespace) -> None:
    _print_json(_runtime(args).list_sources())


def cmd_source_show(args: argparse.Namespace) -> None:
    _print_json(_runtime(args).get_source(args.id))


def cmd_source_status(args: argparse.Namespace) -> None:
    _print_json(_runtime(args).set_source_status(args.id, args.status))


def cmd_memory_propose(args: argparse.Namespace) -> None:
    _print_json(_runtime(args).propose_memory(args.content, args.type, args.evidence_ids, args.scope, args.confidence, args.rationale, args.risk, args.impact, args.valid_from, args.valid_until))


def cmd_memory_list(args: argparse.Namespace) -> None:
    _print_json(_runtime(args).list_memories())


def cmd_memory_show(args: argparse.Namespace) -> None:
    _print_json(_runtime(args).get_memory(args.id))


def cmd_memory_status(args: argparse.Namespace) -> None:
    _print_json(_runtime(args).set_memory_status(args.id, args.status, args.approval_id))


def cmd_capability_add(args: argparse.Namespace) -> None:
    _print_json(_runtime(args).register_capability(_load_json_file(args.file)))


def cmd_capability_list(args: argparse.Namespace) -> None:
    _print_json(_runtime(args).list_capabilities())


def cmd_capability_show(args: argparse.Namespace) -> None:
    _print_json(_runtime(args).get_capability(args.id))


def cmd_capability_status(args: argparse.Namespace) -> None:
    _print_json(_runtime(args).set_capability_status(args.id, args.status, args.approval_id))


def cmd_specialist_add(args: argparse.Namespace) -> None:
    _print_json(_runtime(args).register_specialist(_load_json_file(args.file)))


def cmd_specialist_list(args: argparse.Namespace) -> None:
    _print_json(_runtime(args).list_specialists())


def cmd_specialist_show(args: argparse.Namespace) -> None:
    _print_json(_runtime(args).get_specialist(args.id))


def cmd_specialist_status(args: argparse.Namespace) -> None:
    _print_json(_runtime(args).set_specialist_status(args.id, args.status, args.approval_id))


def cmd_approval_request(args: argparse.Namespace) -> None:
    record = build_approval_record(args.action_type, args.action_reference, args.rationale, args.scope, args.risk, args.impact)
    _print_json(_runtime(args).request_approval(record))


def cmd_approval_list(args: argparse.Namespace) -> None:
    _print_json(_runtime(args).list_approvals())


def cmd_approval_show(args: argparse.Namespace) -> None:
    _print_json(_runtime(args).get_approval(args.id))


def cmd_approval_decide(args: argparse.Namespace) -> None:
    decisions = {"approve": "approved", "reject": "rejected", "defer": "deferred", "expire": "expired", "revoke": "revoked"}
    _print_json(_runtime(args).decide_approval(args.id, decisions[args.decision], args.note))


def cmd_route(args: argparse.Namespace) -> None:
    request = {"action_type": args.action_type, "scope": args.scope, "requested_at": args.requested_at, "action_reference": args.action_reference, "capability_id": args.capability_id, "specialist_id": args.specialist_id, "approval_id": args.approval_id}
    _print_json(_runtime(args).run_task(request))


def cmd_backup_create(args: argparse.Namespace) -> None:
    _print_json(create_backup(_store(args), args.destination))


def cmd_backup_verify(args: argparse.Namespace) -> None:
    result = verify_backup(args.manifest)
    if not result["valid"]:
        raise ValueError("backup verification failed: " + "; ".join(result["errors"]))
    _print_json(result)


def cmd_restore(args: argparse.Namespace) -> None:
    _print_json(restore_backup(args.manifest, args.destination, args.overwrite))


def cmd_health(args: argparse.Namespace) -> None:
    result = _runtime(args).health()
    _print_json(result)
    if not result["healthy"]:
        raise SystemExit(1)


def cmd_cognition_run(args: argparse.Namespace) -> None:
    _print_json(_cognition(args).run_session(_load_json_file(args.file)))


def cmd_cognition_sessions(args: argparse.Namespace) -> None:
    engine = _cognition(args)
    _print_json(engine.session_result(args.id) if args.id else engine.list_family("sessions"))


def cmd_cognition_artifacts(args: argparse.Namespace) -> None:
    engine = _cognition(args)
    _print_json(engine.get_record(args.family, args.id) if args.id else engine.list_family(args.family, args.session_id))


def cmd_cognition_transition(args: argparse.Namespace) -> None:
    engine = _cognition(args)
    if args.family == "patterns":
        result = engine.set_pattern_status(args.id, args.status)
    elif args.family == "hypotheses":
        result = engine.set_hypothesis_status(args.id, args.status)
    elif args.family == "ideas":
        result = engine.set_idea_status(args.id, args.status)
    else:
        result = engine.set_model_update_status(args.id, args.status, args.approval_id)
    _print_json(result)


def _add_zos_source_arguments(command: argparse.ArgumentParser) -> None:
    command.add_argument("--source-root", required=True, help="Read-only local ZOS checkout root")
    command.add_argument("--source-ref", required=True, help="Exact ZOS commit or immutable ref")
    command.add_argument("--source-repository", default=SOURCE_REPOSITORY)
    command.add_argument("paths", nargs="+", help="Selected paths relative to the source root")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="zis", description="ZIS local deterministic runtime")
    root.add_argument("--database", help="SQLite path (default: .zis/zis.sqlite3)")
    commands = root.add_subparsers(dest="command", required=True)
    for name, function in (("init", cmd_init), ("status", cmd_status), ("contradictions", cmd_contradictions)):
        command = commands.add_parser(name)
        command.set_defaults(function=function)
    command = commands.add_parser("validate")
    command.add_argument("contract", choices=sorted(CONTRACTS))
    command.add_argument("file")
    command.set_defaults(function=cmd_validate)
    evidence = commands.add_parser("evidence")
    evidence_commands = evidence.add_subparsers(dest="evidence_command", required=True)
    add = evidence_commands.add_parser("add")
    add.add_argument("content")
    add.add_argument("--type", required=True, choices=["observation", "user_statement", "external_fact", "inference", "hypothesis", "correction", "derived_pattern"])
    add.add_argument("--source-type", required=True)
    add.add_argument("--source-reference", required=True)
    add.add_argument("--source-reference-extra", action="append", default=[])
    add.add_argument("--scope", required=True)
    add.add_argument("--confidence", default="unknown", choices=["unknown", "weak", "probable", "strong", "established"])
    add.add_argument("--observed-at")
    add.add_argument("--valid-from")
    add.add_argument("--valid-until")
    add.add_argument("--privacy-class", default="private", choices=["public", "internal", "private", "restricted"])
    add.add_argument("--provenance-method", default="manual_entry")
    add.add_argument("--provenance-actor", default="owner")
    add.add_argument("--supersedes")
    add.set_defaults(function=cmd_evidence_add)
    listing = evidence_commands.add_parser("list")
    listing.add_argument("--status")
    listing.add_argument("--scope")
    listing.add_argument("--json", action="store_true")
    listing.set_defaults(function=cmd_evidence_list)
    show = evidence_commands.add_parser("show")
    show.add_argument("id")
    show.set_defaults(function=cmd_evidence_show)
    status = evidence_commands.add_parser("status")
    status.add_argument("id")
    status.add_argument("status", choices=["reviewed", "promoted", "rejected", "expired"])
    status.set_defaults(function=cmd_evidence_status)
    contradiction = commands.add_parser("contradiction")
    contradiction_commands = contradiction.add_subparsers(dest="contradiction_command", required=True)
    add_contradiction = contradiction_commands.add_parser("add")
    add_contradiction.add_argument("evidence_id_a")
    add_contradiction.add_argument("evidence_id_b")
    add_contradiction.set_defaults(function=cmd_contradiction_add)
    resolve = contradiction_commands.add_parser("resolve")
    resolve.add_argument("id")
    resolve.add_argument("rationale")
    resolve.add_argument("source_reference")
    resolve.set_defaults(function=cmd_contradiction_resolve)
    export = commands.add_parser("export")
    export.add_argument("destination")
    export.set_defaults(function=cmd_export)
    migrate = commands.add_parser("migrate")
    migration_commands = migrate.add_subparsers(dest="migration_command", required=True)
    zos = migration_commands.add_parser("zos")
    zos_commands = zos.add_subparsers(dest="zos_command", required=True)
    scan = zos_commands.add_parser("scan")
    _add_zos_source_arguments(scan)
    scan.set_defaults(function=cmd_zos_scan)
    inventory = zos_commands.add_parser("inventory")
    inventory.add_argument("--id")
    inventory.set_defaults(function=cmd_zos_inventory)
    candidate_add = zos_commands.add_parser("candidate-add")
    candidate_add.add_argument("file")
    candidate_add.set_defaults(function=cmd_zos_candidate_add)
    candidates = zos_commands.add_parser("candidates")
    candidates.add_argument("--id")
    candidates.add_argument("--review-status")
    candidates.set_defaults(function=cmd_zos_candidates)
    review = zos_commands.add_parser("review")
    review.add_argument("id")
    review.add_argument("decision", choices=sorted(REVIEW_DECISIONS))
    review.add_argument("--note", required=True)
    review.set_defaults(function=cmd_zos_review)
    approve = zos_commands.add_parser("approve")
    approve.add_argument("id")
    approve.add_argument("--note", required=True)
    approve.set_defaults(function=cmd_zos_approve)
    reject = zos_commands.add_parser("reject")
    reject.add_argument("id")
    reject.add_argument("--note", required=True)
    reject.set_defaults(function=cmd_zos_reject)
    import_command = zos_commands.add_parser("import")
    import_command.add_argument("id", nargs="?")
    import_command.set_defaults(function=cmd_zos_import)
    migration_status = zos_commands.add_parser("status")
    migration_status.set_defaults(function=cmd_zos_status)
    migration_dry_run = zos_commands.add_parser("dry-run")
    _add_zos_source_arguments(migration_dry_run)
    migration_dry_run.add_argument("--candidate-file", action="append", default=[])
    migration_dry_run.set_defaults(function=cmd_zos_dry_run)
    runtime = commands.add_parser("runtime")
    runtime_commands = runtime.add_subparsers(dest="runtime_command", required=True)
    runtime_status = runtime_commands.add_parser("status")
    runtime_status.set_defaults(function=cmd_runtime_status)
    runtime_operations = runtime_commands.add_parser("operations")
    runtime_operations.set_defaults(function=cmd_runtime_operations)
    source = commands.add_parser("source")
    source_commands = source.add_subparsers(dest="source_command", required=True)
    source_add = source_commands.add_parser("add")
    source_add.add_argument("file")
    source_add.set_defaults(function=cmd_source_add)
    source_list = source_commands.add_parser("list")
    source_list.set_defaults(function=cmd_source_list)
    source_show = source_commands.add_parser("show")
    source_show.add_argument("id")
    source_show.set_defaults(function=cmd_source_show)
    source_status = source_commands.add_parser("status")
    source_status.add_argument("id")
    source_status.add_argument("status", choices=["active", "inactive"])
    source_status.set_defaults(function=cmd_source_status)
    memory = commands.add_parser("memory")
    memory_commands = memory.add_subparsers(dest="memory_command", required=True)
    memory_propose = memory_commands.add_parser("propose")
    memory_propose.add_argument("evidence_ids", nargs="+")
    memory_propose.add_argument("--content", required=True)
    memory_propose.add_argument("--type", required=True, choices=["core_principle", "pattern", "preference", "project", "evidence_backed", "experimental"])
    memory_propose.add_argument("--scope", required=True)
    memory_propose.add_argument("--confidence", required=True, choices=["unknown", "weak", "probable", "strong", "established"])
    memory_propose.add_argument("--rationale", required=True)
    memory_propose.add_argument("--risk", default="medium", choices=["low", "medium", "high", "critical"])
    memory_propose.add_argument("--impact", default="Promotes reviewed evidence into durable memory storage.")
    memory_propose.add_argument("--valid-from")
    memory_propose.add_argument("--valid-until")
    memory_propose.set_defaults(function=cmd_memory_propose)
    memory_list = memory_commands.add_parser("list")
    memory_list.set_defaults(function=cmd_memory_list)
    memory_show = memory_commands.add_parser("show")
    memory_show.add_argument("id")
    memory_show.set_defaults(function=cmd_memory_show)
    memory_status = memory_commands.add_parser("status")
    memory_status.add_argument("id")
    memory_status.add_argument("status", choices=["active", "superseded", "rejected", "expired", "deprecated"])
    memory_status.add_argument("--approval-id")
    memory_status.set_defaults(function=cmd_memory_status)
    capability = commands.add_parser("capability")
    capability_commands = capability.add_subparsers(dest="capability_command", required=True)
    capability_add = capability_commands.add_parser("add")
    capability_add.add_argument("file")
    capability_add.set_defaults(function=cmd_capability_add)
    capability_list = capability_commands.add_parser("list")
    capability_list.set_defaults(function=cmd_capability_list)
    capability_show = capability_commands.add_parser("show")
    capability_show.add_argument("id")
    capability_show.set_defaults(function=cmd_capability_show)
    capability_status = capability_commands.add_parser("status")
    capability_status.add_argument("id")
    capability_status.add_argument("status", choices=["approved", "available", "unavailable", "deprecated", "retired"])
    capability_status.add_argument("--approval-id")
    capability_status.set_defaults(function=cmd_capability_status)
    specialist = commands.add_parser("specialist")
    specialist_commands = specialist.add_subparsers(dest="specialist_command", required=True)
    specialist_add = specialist_commands.add_parser("add")
    specialist_add.add_argument("file")
    specialist_add.set_defaults(function=cmd_specialist_add)
    specialist_list = specialist_commands.add_parser("list")
    specialist_list.set_defaults(function=cmd_specialist_list)
    specialist_show = specialist_commands.add_parser("show")
    specialist_show.add_argument("id")
    specialist_show.set_defaults(function=cmd_specialist_show)
    specialist_status = specialist_commands.add_parser("status")
    specialist_status.add_argument("id")
    specialist_status.add_argument("status", choices=["approved", "available", "unavailable", "retired"])
    specialist_status.add_argument("--approval-id")
    specialist_status.set_defaults(function=cmd_specialist_status)
    approval = commands.add_parser("approval")
    approval_commands = approval.add_subparsers(dest="approval_command", required=True)
    approval_request = approval_commands.add_parser("request")
    approval_request.add_argument("action_type")
    approval_request.add_argument("action_reference")
    approval_request.add_argument("--rationale", required=True)
    approval_request.add_argument("--scope", required=True)
    approval_request.add_argument("--risk", required=True, choices=["low", "medium", "high", "critical"])
    approval_request.add_argument("--impact", required=True)
    approval_request.set_defaults(function=cmd_approval_request)
    approval_list = approval_commands.add_parser("list")
    approval_list.set_defaults(function=cmd_approval_list)
    approval_show = approval_commands.add_parser("show")
    approval_show.add_argument("id")
    approval_show.set_defaults(function=cmd_approval_show)
    approval_decide = approval_commands.add_parser("decide")
    approval_decide.add_argument("id")
    approval_decide.add_argument("decision", choices=["approve", "reject", "defer", "expire", "revoke"])
    approval_decide.add_argument("--note", required=True)
    approval_decide.set_defaults(function=cmd_approval_decide)
    route = commands.add_parser("route")
    route.add_argument("action_type", choices=["no_action", "runtime_status", "existing_capability", "specialist", "persistent_change"])
    route.add_argument("--scope", required=True)
    route.add_argument("--requested-at")
    route.add_argument("--action-reference")
    route.add_argument("--capability-id")
    route.add_argument("--specialist-id")
    route.add_argument("--approval-id")
    route.set_defaults(function=cmd_route)
    backup = commands.add_parser("backup")
    backup_commands = backup.add_subparsers(dest="backup_command", required=True)
    backup_create = backup_commands.add_parser("create")
    backup_create.add_argument("destination")
    backup_create.set_defaults(function=cmd_backup_create)
    backup_verify = backup_commands.add_parser("verify")
    backup_verify.add_argument("manifest")
    backup_verify.set_defaults(function=cmd_backup_verify)
    restore = commands.add_parser("restore")
    restore.add_argument("manifest")
    restore.add_argument("destination")
    restore.add_argument("--overwrite", action="store_true")
    restore.set_defaults(function=cmd_restore)
    health = commands.add_parser("health")
    health.set_defaults(function=cmd_health)
    cognition = commands.add_parser("cognition")
    cognition_commands = cognition.add_subparsers(dest="cognition_command", required=True)
    cognition_run = cognition_commands.add_parser("run")
    cognition_run.add_argument("file", help="Structured cognitive-session JSON input")
    cognition_run.set_defaults(function=cmd_cognition_run)
    cognition_sessions = cognition_commands.add_parser("sessions")
    cognition_sessions.add_argument("--id")
    cognition_sessions.set_defaults(function=cmd_cognition_sessions)
    cognition_artifacts = cognition_commands.add_parser("artifacts")
    cognition_artifacts.add_argument("family", choices=["attention", "associations", "patterns", "hypotheses", "ideas", "evaluations", "reflections", "proposals"])
    cognition_artifacts.add_argument("--id")
    cognition_artifacts.add_argument("--session-id")
    cognition_artifacts.set_defaults(function=cmd_cognition_artifacts)
    cognition_transition = cognition_commands.add_parser("transition")
    cognition_transition.add_argument("family", choices=["patterns", "hypotheses", "ideas", "proposals"])
    cognition_transition.add_argument("id")
    cognition_transition.add_argument("status")
    cognition_transition.add_argument("--approval-id")
    cognition_transition.set_defaults(function=cmd_cognition_transition)
    return root


def main(argv: list[str] | None = None) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = parser().parse_args(argv)
    try:
        args.function(args)
    except (ContractError, KeyError, ValueError, OSError, sqlite3.IntegrityError) as error:
        raise SystemExit(str(error)) from error


if __name__ == "__main__":
    main()

