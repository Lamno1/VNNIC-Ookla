RESEARCH_GATE

BLOCKED_BY_SEMANTICS

CAUSAL_GATE = CLOSED  
DECISION_2269_GATE = FAIL_PRIMARY_ROUTE

# Executive finding

The project is structurally feasible for a 63-province, 2021–2024 descriptive and associational study, but analysis is not currently authorized. The acquired-file semantics and vintage of the primary VNNIC exposure and NSO outcomes are not sufficiently verified. No analysis panel or model has been released.

# Gates

| Gate | Status | Evidence |
|---|---|---|
| G0 Security | PASS | Output separation, allow-list, credential exclusion, protocol lock |
| G1 Provenance | WARN | Core manifests exist; primary-variable provenance remains incomplete |
| G2 Semantics | FAIL | Exact VNNIC export construction and NSO local-workbook vintage/universe unresolved |
| G3 Geography | PASS | 63 unique units; deterministic crosswalk; canonical SHA256 locked |
| G4 VNNIC key/coverage | PASS | 7,360 rows; 0 duplicate keys; 2,268/2,268 valid primary-window downloads |
| G5 NSO outcomes | FAIL | Structure parsed, but candidates remain quarantined pending provenance/identifier review |
| G6 Merge | NOT RUN | Depends on G2 and G5 |
| G7 Analysis readiness | NOT RUN | Depends on G1–G6 |
| G8 Claims | PASS | Maximum claim level remains ASSOCIATIONAL; no empirical association estimated |
| G9 Reproducibility | PARTIAL | Audit pipeline reruns deterministically; blocked downstream deliverables do not exist |

# Verified structural evidence

- Canonical geography: 63 provinces, 63 unique IDs/ISO/name mappings, 63 distinct geometries, canonical hash `c64a07c3fd5d3ca0339a5002983dc76ddd60a0ef88e889522e37ca2408f74400`.
- VNNIC legacy panel: 7,360 observed rows, no duplicate network–province–month key, and 1,082 explicitly enumerated missing expected cells over 2019-12 through 2025-06.
- Locked primary FTTH window: 63 × 4 × 9 = 2,268 observations, all download values non-null, finite and positive.
- NSO structural candidates: V05.02, V05.04 and V05.05 each expose 63 province candidates and seven audited aggregate exclusions. Candidate values are quarantined, not analytical outputs.
- Decision 2269 evidence contains no verified locality activation/completion dates. It is not encoded as treatment.

# Exact blockers

1. VNNIC: obtain documentation tied to the acquired files that defines province-month construction, geographic assignment, filtering, revision policy and the `value` field.
2. NSO: prove official acquisition/vintage and detailed universes for the local V05.02/V05.04/V05.05 workbooks.
3. Entry-rate outcome: verify compatibility of annual registrations with lagged year-end active enterprises.
4. Province identifiers in NSO: review and approve the quarantined deterministic name crosswalk or obtain an official code-bearing extract.

# Safe next action

Acquire or document the specific materials listed in `missing_document_request.md`, amend the frozen protocol only if the definitions require a design change, and rerun the gated pipeline. Do not build the 252-row analysis panel until G2 and G5 pass.
