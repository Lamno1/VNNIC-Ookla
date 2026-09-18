# Protocol amendment — 2026-09-13 semantic rescue

## Prior rule

Use NSO V05.05 as the primary outcome and V05.02 divided by lagged V05.04 as the secondary entry-rate outcome, with G2 blocking analysis until semantics and provenance are verified.

## New rule

Use the latest official NSO PXWeb V05.05 snapshot retrieved on 2026-09-13 as the prospective primary-outcome source. This is an ex-post historical snapshot; revised historical values are not interpreted as information available contemporaneously. Local workbooks are comparison derivatives only.

The V05.02 / lagged V05.04 ratio is renamed a researcher-constructed gross entry-intensity proxy and assigned `EXPLORATORY_UNAVAILABLE` until universe compatibility is documented. Its unavailability does not block the verified V05.05 primary outcome.

VNNIC FTTH download remains the locked primary exposure. Its status is `PASS_WITH_LIMITATIONS`; `value` is `NOT_USED` and cannot be used as a weight.

## Reason and evidence

- Reproducible PXWeb metadata, request payloads and response hashes are stored under `data/reference/nso_official_snapshot_20260913`.
- V05.02 and V05.04 match the local workbooks exactly. V05.05 local values are rounded to two decimals; the official response retains greater precision.
- Official Internet Atlas interface and production JavaScript verify metric units, median method, selection parameters and minimum sample publication rule.

## Affected artifacts

Semantic registry, NSO/VNNIC semantic decisions, prospective NSO source lineage, subsequent outcome construction, and future panel construction.

## Invalidation

No analytical results existed. Quarantined local NSO candidates remain quarantined and are not promoted. The prior fail-closed semantic report is retained as historical run evidence.

## Effective protocol identity

The amendment file SHA256 and composite protocol identity are recorded in `protocol/protocol_effective_lock.json`.
