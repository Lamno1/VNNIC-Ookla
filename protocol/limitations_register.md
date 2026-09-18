# Limitations Register

| ID | Severity | Status | Limitation | Downstream consequence |
|---|---|---|---|---|
| L001 | Critical | OPEN | No verified Decision 2269 locality rollout/activation/completion/acceptance dates or attribution | Causal route closed |
| L002 | High | OPEN | Official semantics and units for VNNIC download/upload/ping/jitter/value not yet locally verified | Blocks G2 and models |
| L003 | High | OPEN | NSO origin, units, table semantics, and revision vintage not yet verified | Blocks G1/G2/G5 and models |
| L004 | High | OPEN | VNNIC historical endpoints were retrieved retrospectively in 2026; revision policy unknown | Requires disclosure and provenance verification |
| L005 | Medium | OPEN | Ookla has two structural schema variants | Extended latency fields require structural-NA handling |
| L006 | Medium | OPEN | Ookla test/device composition may be endogenous | Weighting cannot be treated as neutral |
| L007 | Medium | OPEN | Canonical boundary was distributed in 2021 but metadata boundaryYear is 2016 | Must be described as fixed analytical reference |
| L008 | Medium | OPEN | WBES geography is broad sampling region, not necessarily province | Do not force province merge |
| L009 | Medium | OPEN | PCI schemas and overall score coverage vary by year | PCI remains auxiliary pending audit |

## Active blockers at the structural-audit checkpoint

- VNNIC export aggregation, geographic assignment, filtering, revision policy and `value` semantics are unverified for the acquired files.
- NSO local workbook acquisition/vintage and detailed statistical universes are not provenance-complete.
- Compatibility of V05.02 annual registrations with lagged V05.04 active-enterprise stock is unverified.
- NSO province-name candidates require explicit identifier review or an official code-bearing extract.
- No locality implementation dates exist for Decision 2269 in the acquired evidence; the causal route remains closed.

## Residual limitations after semantic rescue

- VNNIC test/device composition, internal calculation implementation and retrospective revision policy remain undocumented.
- V05.05's official API title defines the per-1,000-population outcome, but detailed denominator-universe metadata are not present in the API response.
- Local V05.05 workbooks are rounded derivatives; future analytical construction must use the immutable official API snapshot.
- V05.02/V05.04 universe compatibility is unresolved, so the gross entry-intensity proxy is unavailable.

## Limitations carried into the panel

- VNNIC semantics remain verified with limitations: test/device composition, internal implementation details, and retrospective revision policy are undocumented.
- The official PXWeb V05.05 snapshot is authoritative for this study, but its detailed denominator universe is not supplied in API metadata and its official-statistics designation is preserved as “Không”.
- Local NSO workbooks are quarantined derivatives and do not contribute analytical values.
- The entry-intensity proxy is absent from the panel (`EXPLORATORY_UNAVAILABLE`).
- The panel supports descriptive work next; causal interpretation remains prohibited.
