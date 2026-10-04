# ObservationRecord v2

Machine contract: `ObservationRecord.schema.json`. M7 replaces the conceptual M1 shape with the governed ledger record while preserving the original privacy invariant.

Every record identifies its approved source and explicit collection session; adapter/version; observed, recorded and imported time; exact scope and data class; content fingerprint; provenance; privacy and capture-integrity confidence; review and retention state; and any later evidence links.

`observed_at` is nullable only when `observed_time_status` is `unknown`; import time is not substituted. `capture_confidence` describes whether capture was faithful, not whether content is true.

Private local content may exist only in the gitignored runtime vault. Restricted, denied, suspected-secret and unsafe public/internal input becomes a content-free quarantine marker. Default export includes only metadata/fingerprints for private, restricted and quarantined records.

Invariant: ObservationRecord is not EvidenceRecord, MemoryRecord, truth, permission or automatic learning.
