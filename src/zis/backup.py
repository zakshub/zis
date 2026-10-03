"""Verified local SQLite backup and safe restore for the Classical Runtime."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

from . import __version__
from .contracts import ContractError, validate
from .ids import deterministic_id
from .runtime import LATEST_SCHEMA_VERSION
from .store import EvidenceStore, utc_now


DURABLE_TABLES = (
    "schema_migrations",
    "evidence_records",
    "contradictions",
    "audit_events",
    "migration_sources",
    "migration_candidates",
    "migration_review_events",
    "runtime_sources",
    "approval_records",
    "memory_records",
    "memory_evidence_links",
    "capability_registry",
    "capability_dependencies",
    "specialist_registry",
    "route_decisions",
    "runtime_operations",
)


def file_checksum(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _database_summary(path: str | Path) -> dict[str, Any]:
    database = Path(path).resolve()
    connection = sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)
    try:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        missing = [table for table in DURABLE_TABLES if table not in tables]
        if missing:
            raise ValueError("backup database is missing required tables: " + ", ".join(missing))
        counts = {table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]) for table in DURABLE_TABLES}
        schema_version = int(connection.execute("SELECT COALESCE(MAX(version),0) FROM schema_migrations").fetchone()[0])
        foreign_key_issues = [tuple(row) for row in connection.execute("PRAGMA foreign_key_check")]
        return {"integrity_check": integrity, "schema_version": schema_version, "counts": counts, "foreign_key_issues": foreign_key_issues}
    finally:
        connection.close()


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def create_backup(store: EvidenceStore, destination: str | Path) -> dict[str, Any]:
    store.initialize()
    target = Path(destination).resolve()
    target.mkdir(parents=True, exist_ok=True)
    created_at = utc_now()
    filename_stamp = created_at.replace("-", "").replace(":", "").replace(".", "")
    backup_path = target / f"zis-backup-{filename_stamp}.sqlite3"
    manifest_path = target / f"zis-backup-{filename_stamp}.manifest.json"
    descriptor, temporary_name = tempfile.mkstemp(prefix=".zis-backup-", suffix=".tmp", dir=target)
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        with store.connect() as source_connection:
            destination_connection = sqlite3.connect(temporary)
            try:
                source_connection.backup(destination_connection)
            finally:
                destination_connection.close()
        summary = _database_summary(temporary)
        if summary["integrity_check"] != "ok" or summary["foreign_key_issues"]:
            raise ValueError("backup verification failed before publication")
        checksum = file_checksum(temporary)
        manifest = {
            "id": deterministic_id("bkp", {"checksum": checksum, "created_at": created_at, "schema_version": summary["schema_version"], "version": 1}),
            "format": "zis-sqlite-backup",
            "backup_file": backup_path.name,
            "checksum": checksum,
            "checksum_algorithm": "sha256",
            "created_at": created_at,
            "schema_version": summary["schema_version"],
            "runtime_version": __version__,
            "source_database": str(store.path.resolve()),
            "counts": summary["counts"],
            "integrity_check": "ok",
            "version": 1,
        }
        validate("backup-manifest", manifest)
        os.replace(temporary, backup_path)
        _write_json_atomic(manifest_path, manifest)
        verification = verify_backup(manifest_path)
        if not verification["valid"]:
            raise ValueError("published backup failed verification: " + "; ".join(verification["errors"]))
        return {"backup": str(backup_path), "manifest": str(manifest_path), "metadata": manifest, "verification": verification}
    except Exception:
        temporary.unlink(missing_ok=True)
        manifest_path.unlink(missing_ok=True)
        backup_path.unlink(missing_ok=True)
        raise


def verify_backup(manifest_file: str | Path) -> dict[str, Any]:
    manifest_path = Path(manifest_file).resolve()
    errors: list[str] = []
    manifest: dict[str, Any] | None = None
    backup_path: Path | None = None
    summary: dict[str, Any] | None = None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        validate("backup-manifest", manifest)
        if Path(manifest["backup_file"]).name != manifest["backup_file"]:
            raise ValueError("backup_file must be a sibling basename")
        backup_path = manifest_path.parent / manifest["backup_file"]
        if not backup_path.is_file():
            raise ValueError("backup database does not exist")
        if file_checksum(backup_path) != manifest["checksum"]:
            raise ValueError("backup checksum mismatch")
        if manifest["schema_version"] != LATEST_SCHEMA_VERSION:
            raise ValueError(f"unsupported backup schema version: {manifest['schema_version']}")
        if manifest["runtime_version"] != __version__:
            raise ValueError(f"unsupported backup runtime version: {manifest['runtime_version']}")
        summary = _database_summary(backup_path)
        if summary["integrity_check"] != "ok":
            raise ValueError(f"SQLite integrity check failed: {summary['integrity_check']}")
        if summary["foreign_key_issues"]:
            raise ValueError("backup contains foreign-key integrity problems")
        if summary["schema_version"] != manifest["schema_version"]:
            raise ValueError("backup schema version does not match manifest")
        if summary["counts"] != manifest["counts"]:
            raise ValueError("backup durable-state counts do not match manifest")
    except (OSError, json.JSONDecodeError, sqlite3.DatabaseError, ContractError, ValueError) as error:
        errors.append(str(error))
    return {"valid": not errors, "manifest": str(manifest_path), "backup": str(backup_path) if backup_path else None, "metadata": manifest, "database_summary": summary, "errors": errors}


def restore_backup(manifest_file: str | Path, destination: str | Path, overwrite: bool = False) -> dict[str, Any]:
    verification = verify_backup(manifest_file)
    if not verification["valid"]:
        raise ValueError("backup verification failed: " + "; ".join(verification["errors"]))
    manifest = verification["metadata"]
    assert manifest is not None
    backup_path = Path(verification["backup"])
    destination_path = Path(destination).resolve()
    if destination_path == backup_path.resolve():
        raise ValueError("restore destination must differ from the backup database")
    if destination_path.exists() and not overwrite:
        raise ValueError("restore destination already exists; explicit overwrite is required")
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{destination_path.name}.", suffix=".restore.tmp", dir=destination_path.parent)
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        source_connection = sqlite3.connect(f"file:{backup_path.resolve().as_posix()}?mode=ro", uri=True)
        destination_connection = sqlite3.connect(temporary)
        try:
            source_connection.backup(destination_connection)
        finally:
            destination_connection.close()
            source_connection.close()
        summary = _database_summary(temporary)
        if summary["integrity_check"] != "ok" or summary["foreign_key_issues"]:
            raise ValueError("restored temporary database failed integrity verification")
        if summary["schema_version"] != manifest["schema_version"] or summary["counts"] != manifest["counts"]:
            raise ValueError("restored temporary database does not match backup manifest")
        os.replace(temporary, destination_path)
        reopened = _database_summary(destination_path)
        return {"restored": True, "destination": str(destination_path), "schema_version": reopened["schema_version"], "counts": reopened["counts"], "source_manifest": str(Path(manifest_file).resolve())}
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
