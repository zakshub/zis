"""Minimal Milestone 1 command-line interface."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from . import __version__
from .contracts import CONTRACTS, ContractError, validate
from .export import export_store
from .migration import REVIEW_DECISIONS, SOURCE_REPOSITORY, ZOSMigrationStore, dry_run, load_candidate_specifications
from .records import build_evidence
from .store import EvidenceStore


def _store(args: argparse.Namespace) -> EvidenceStore:
    return EvidenceStore(args.database)


def _migration_store(args: argparse.Namespace) -> ZOSMigrationStore:
    return ZOSMigrationStore(_store(args))


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


def _add_zos_source_arguments(command: argparse.ArgumentParser) -> None:
    command.add_argument("--source-root", required=True, help="Read-only local ZOS checkout root")
    command.add_argument("--source-ref", required=True, help="Exact ZOS commit or immutable ref")
    command.add_argument("--source-repository", default=SOURCE_REPOSITORY)
    command.add_argument("paths", nargs="+", help="Selected paths relative to the source root")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="zis", description="ZIS local evidence foundation")
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
    return root


def main(argv: list[str] | None = None) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = parser().parse_args(argv)
    try:
        args.function(args)
    except (ContractError, KeyError, ValueError, sqlite3.IntegrityError) as error:
        raise SystemExit(str(error)) from error


if __name__ == "__main__":
    main()

