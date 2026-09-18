RESEARCH_GATE

READY_FOR_PANEL_CONSTRUCTION

G2_VNNIC = PASS_WITH_LIMITATIONS  
G2_NSO_PRIMARY = PASS_WITH_LIMITATIONS  
G2_NSO_ENTRY_RATE = EXPLORATORY_UNAVAILABLE  
G5_PRIMARY_OUTCOME = PASS  
CAUSAL_GATE = CLOSED  
DECISION_2269_GATE = FAIL_PRIMARY_ROUTE  
ANALYSIS_PANEL_CREATED = false  
DESCRIPTIVE_ANALYSIS_RUN = false  
MODEL_RUN = false

# NSO result

Three immutable official PXWeb snapshots were retrieved with complete metadata, request payloads, response headers, sizes and SHA256 hashes. The snapshot contains 1,750 total cells and 1,575 province cells across 63 unique official PX geography codes.

| Table | Exact matches | Mismatches | Verdict |
|---|---:|---:|---|
| V05.02 | 630 | 0 | Official snapshot and local workbook agree |
| V05.04 | 560 | 0 | Official snapshot and local workbook agree |
| V05.05 | 100 | 460 | Local workbook is rounded to two decimals; official snapshot adopted |

The maximum V05.05 absolute difference is 0.004975259154729628. No favorable-version selection occurred: the official API response is the prospective source regardless of reconciliation direction.

The official table title establishes active enterprises at 31 December per 1,000 inhabitants by locality. Detailed denominator-universe metadata are not published in the API response, so the primary outcome is `PASS_WITH_LIMITATIONS`.

The PX dimension codes identify all 70 displayed geographic rows. Seven national/region codes are explicitly excluded and 63 province codes map one-to-one to the legacy-63 dimension. No fuzzy match was used.

# VNNIC result

The official VNNIC Internet Atlas interface and its production JavaScript establish:

- official VNNIC publication endpoint;
- fixed/mobile network selection;
- year, month, ISP and province request parameters;
- download/upload in Mbps and ping/jitter in ms;
- median calculation for displayed data;
- publication only for localities with at least 30 samples per month;
- `isp=ALL` as all enterprises and `cityId=-1` as all provinces.

Test/device composition, internal computation implementation and retrospective revision policy were not found in the bounded official-source cycle. These are recorded limitations but do not change the substantive meaning of the primary download measure. `value` is `NOT_USED`.

# Decision

The two primary semantic blockers are resolved with explicit limitations. The project may proceed to a separate, gated panel-construction run. This sprint did not build a panel or run any analysis.
