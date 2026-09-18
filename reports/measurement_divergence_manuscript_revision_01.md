# Common Trends and Different Provincial Signals

## Comparing VNNIC i-Speed and Ookla Fixed-Broadband Measurements across Vietnam from 2021 to 2024

## Abstract

Administrative and crowdsourced speed-test systems are often treated as interchangeable measures of local digital connectivity. We compare VNNIC i-Speed and Ookla fixed-broadband measurements across a fixed geography of 63 historical Vietnamese provinces from 2021 to 2024. The comparison separates agreement in the common direction of change, cross-province dispersion, yearly provincial ranks, and province-specific improvement. Between their matched-Q2 observations in 2021 and 2024, both systems record higher measured download performance in every province. Five of six declared dispersion indicators also move in the same direction across the two sources, toward a wider cross-province distribution. Agreement weakens at finer resolutions. Yearly Spearman rank correlations for the primary matched-quarter comparison are 0.542, 0.488, 0.296, and 0.248, while the Spearman correlation of province-specific changes is -0.247. The negative change-rank result persists under four reasonable Ookla aggregation rules. Changes in Ookla speed also co-vary with changes in observed tests and devices. The evidence therefore supports a common direction of change across the 63 province-level distributions and broad dispersion agreement, but not a source-invariant provincial ordering or improvement intensity. Descriptions of local connectivity inequality depend on the measurement construct and aggregation system used.

## 1 Introduction

Digital-connectivity indicators increasingly enter regional dashboards, benchmarking exercises, and empirical research as if a single number represented an observable local condition. In practice, measurement systems differ in participation, sampling, geographic assignment, time aggregation, and implicit weighting. Agreement at a national or aggregate level therefore need not imply agreement about which places perform better or improve faster.

Vietnam offers a useful setting for examining this distinction. VNNIC publishes province-month i-Speed summaries through its Internet Atlas interface [1]. Ookla distributes quarterly fixed-broadband performance aggregates for observed zoom-level-16 map tiles [2,3]. Both systems describe download performance, but their aggregation chains target different observational units. This study asks how far their conclusions travel across four levels: the common direction of change, cross-province dispersion, yearly provincial ranks, and province-specific changes.

Our central finding is layered. Both systems show broad improvement between the matched-Q2 endpoints, and most declared dispersion measures show a wider cross-province distribution. Yet cross-source agreement falls markedly when attention shifts to provincial ordering and relative improvement. This distinction matters because aggregate progress, spatial inequality, and province-specific performance are different claims. A measurement system may support one without supporting the others.

The contribution is methodological and descriptive. We provide an auditable decomposition of agreement rather than a single validity score. We also report aggregation sensitivity, leave-one-province-out influence checks, and composition diagnostics without selecting the specification that most closely aligns the sources.

## 2 Measurement Systems and Constructs

### 2.1 VNNIC i-Speed

The VNNIC construct is a published province-level fixed-broadband user-experience statistic. The official interface identifies the statistic as a median and reports download speed in Mbps, subject to a minimum 30-sample publication rule [1]. For within-source annual description, we use the unweighted median of the nine published monthly values from April through December. For the matched cross-source comparison, we use the median for April through June. The series is not interpreted as physical network capacity, household coverage, or population-weighted service quality. The available documentation does not completely resolve test and device composition or retrospective revision practice.

### 2.2 Ookla Open Data

Ookla Open Data report `avg_d_kbps` as the average download speed of tests observed within each tile, together with counts of tests and unique devices [2]. We convert kilobits per second to Mbps and assign each tile centroid to one canonical province. The primary province-quarter statistic is the unweighted median across assigned observed tiles. This is a spatial tile median, not a person-, household-, subscriber-, or device-level median. The AWS Open Data registry documents the quarterly fixed and mobile map-tile archive and notes its public distribution [3].

### 2.3 Why the constructs are not interchangeable

VNNIC begins with a published locality-month statistic; Ookla begins with quarterly tile aggregates and requires a second aggregation to provinces. Equal units do not make the underlying estimands equal. Different participation patterns, spatial support, within-tile averaging, province aggregation, and revision practices can yield common aggregate trends alongside different local rankings.

## 3 Data and Methods

### 3.1 Scope and geography

The study covers 2021 through 2024 and uses a fixed 63-province analytical geography. The geometry was distributed in the 2021 geoBoundaries release and carries metadata boundary year 2016. Fixing the geography prevents administrative-vintage changes from entering the comparison. Province identifiers, rather than names, link all connectivity records.

The VNNIC description contains 63 provinces in every year. The Ookla pilot processes fixed-broadband Q2 files for the same four years and produces 252 province-year aggregates. All provinces are represented in each year. No province is excluded from the reported comparisons.

### 3.2 Within-source description

For VNNIC we report the mean, median, standard deviation, coefficient of variation, interquartile range, percentile ratios, extrema, maps, and rank mobility. The unweighted average-province download mean rises from 48.16 Mbps in 2021 to 89.18 Mbps in 2024; the corresponding medians are 48.07 and 91.14 Mbps. Every province records a positive 2021-to-2024 change, with a median increase of 42.34 Mbps.

Dispersion is assessed jointly using six registered measures: the standard deviations of levels and logs, coefficient of variation, interquartile range, p90-to-p10 ratio, and maximum-to-minimum ratio. No single measure determines the interpretation.

### 3.3 Cross-source comparison

The primary timing match compares Ookla Q2 with VNNIC April-June. We calculate yearly Spearman rank correlation, Pearson correlation of positive log levels, absolute rank differences, median-split agreement, and 2021-to-2024 change-rank agreement. A secondary comparison uses the VNNIC April-December measure and is explicitly temporally mismatched.

We retain the preregistered Ookla definition, the unweighted tile median, regardless of its agreement with VNNIC. Three alternatives are reported symmetrically: unweighted tile mean, tests-weighted mean, and devices-weighted mean. Post-hoc leave-one-province-out and composition checks are labeled as such and do not alter the original mixed-measurement decision.

## 4 Results

### 4.1 Broad improvement within VNNIC

The VNNIC distribution shifts upward between 2021 and 2024 (Figures 1-4). Mean province performance increases from 48.16 to 89.18 Mbps, and the median rises from 48.07 to 91.14 Mbps. The median province-level increase is 42.34 Mbps, and all 63 provinces move in the same positive direction. This is an unweighted description across provinces, not a population-weighted national statistic.

### 4.2 Cross-province dispersion

The six VNNIC dispersion statistics do not move monotonically every year, but their endpoints generally indicate a wider distribution in 2024 than in 2021. The standard deviation of levels rises from 3.65 to 9.86 Mbps; the standard deviation of logs rises from 0.076 to 0.121; and the coefficient of variation rises from 0.076 to 0.111. The interquartile range rises from 4.22 to 11.93 Mbps, while the p90-to-p10 ratio increases from 1.184 to 1.294 and the maximum-to-minimum ratio from 1.474 to 1.947.

The matched Q2 comparison yields broad directional support across sources: five of the six registered dispersion indicators agree on the direction of the 2021-to-2024 change (Figure 12). This is evidence about the distribution of measured performance across provinces, not about the process producing that distribution.

### 4.3 Rank persistence within VNNIC

VNNIC provincial ranks show moderate and uneven persistence (Figure 5). Spearman persistence equals 0.448 for 2021-2022, 0.273 for 2021-2023, 0.475 for 2021-2024, 0.788 for 2022-2023, and 0.504 for 2023-2024. Between 2021 and 2024, 20 provinces remain in the same quartile, 18 move up one quartile, five move up at least two, 12 move down one, and eight move down at least two. These movements describe the published VNNIC ordering only.

### 4.4 Cross-source provincial ranks

Yearly agreement is positive but declines across the period (Figure 10). Spearman rank correlations between the primary Ookla aggregate and matched VNNIC Q2 measure are 0.542 in 2021, 0.488 in 2022, 0.296 in 2023, and 0.248 in 2024. Pearson correlations of log levels likewise move from 0.584 and 0.539 in the first two years to 0.220 and 0.047 in the last two. Depending on year, 20 to 29 provinces differ by more than 15 rank positions. Thus, a shared upward shift does not preserve a stable cross-source provincial ordering.

### 4.5 Province-specific changes

Between their matched-Q2 observations in 2021 and 2024, the two systems agree on the sign of change for all 63 provinces, but not on relative improvement (Figure 11). The primary Spearman correlation between 2021-to-2024 province changes is -0.247. A province that rises more in one system therefore does not generally rise more in the other. This result separates common-trend agreement from agreement about local improvement intensity.

### 4.6 Aggregation, influence, and composition diagnostics

All four Ookla aggregation variants retain a negative change-rank correlation: -0.247 for the unweighted tile median, -0.193 for the unweighted tile mean, -0.178 for the tests-weighted mean, and -0.169 for the devices-weighted mean. Weighting changes magnitudes but does not restore positive province-specific change agreement. These comparisons are post-hoc measurement diagnostics and are not substitutes for the preregistered primary aggregation.

Leave-one-province-out checks do not reverse the overall interpretation. Every influence flag is retained, so the analysis does not manufacture agreement by deleting provinces. Composition diagnostics remain material: for the primary tile median, Ookla speed change has Pearson and Spearman associations of 0.591 and 0.545 with changes in tests, and 0.583 and 0.535 with changes in devices. These patterns heighten concern that province-change comparisons may be sensitive to observed test and device participation; they do not identify the source or magnitude of any measurement bias.

## 5 Discussion

The findings show why measurement agreement must be stated at the correct level. At the broadest level, both sources record improvement across every province. At the distributional level, most declared indicators point toward increasing cross-province dispersion. At the cross-sectional level, provincial ranks align only moderately in the early years and weakly later. At the change level, the ordering is negative across every reasonable Ookla aggregation examined.

The evidence is consistent with the systems measuring related but non-equivalent constructs. VNNIC publishes a locality-month statistic after its own eligibility and aggregation rules. Ookla observes a changing spatial set of tests and devices, summarizes within tiles, and is then aggregated across tiles. The observed differences may arise from participation, spatial support, implicit weights, timing, or revision practice. The available diagnostics do not identify one explanation as definitive.

This decomposition changes the interpretation of measured cross-province connectivity differences. Statements about broad improvement are robust across these two sources. Statements about wider provincial dispersion receive substantial, though not universal, support. Statements that identify the best-connected provinces or the places improving fastest are much more source-dependent. A single measurement series can therefore be adequate for one descriptive claim and inadequate for another.

## 6 Limitations

First, both systems depend on speed-test participation and do not form probability samples of residents, households, or locations. Second, VNNIC's test/device composition and historical revision process are incompletely documented. Third, Ookla observed tiles do not constitute a documented geographic-coverage denominator, and centroid assignment differs from area allocation near boundaries. Fourth, the main cross-source validation covers Q2 in four years; it does not establish temporal reliability across every quarter. Fifth, aggregation sensitivity can reveal dependence on implicit weights but cannot establish which aggregation is substantively correct. Sixth, the 63-province geometry is a fixed analytical reference with metadata boundary year 2016, not a claim of month-specific historical boundaries.

These constraints preserve a descriptive-measurement claim ceiling. The study does not designate either source as ground truth, does not interpret agreement as infrastructure activation or population coverage, and does not attribute the reported patterns to a particular program or mechanism.

## 7 Conclusion

Across the 63 matched province-level Q2 observations, VNNIC and Ookla show a common positive direction between 2021 and 2024 and mostly agree that the measured cross-province distributions widened between those endpoints. They do not tell a common story about provincial ordering or which provinces improved most. The loss of agreement from aggregate direction to province-specific change persists across four Ookla aggregation choices and remains negative in the leave-one-province-out diagnostics; all provinces remain in the reported sample. Observed changes in tests and devices remain an important composition concern.

The practical conclusion is narrow but consequential: the measured extent and ordering of cross-province connectivity differences depend partly on the construct and measurement system used. Future work should define the intended construct before selecting a source and should establish temporal and composition reliability before treating province-specific change as a stable exposure.

## References

1. Vietnam Internet Network Information Center. VNNIC Internet Atlas i-Speed. https://internetatlas.vnnic.vn/i-speed. Accessed 13 September 2026.
2. Ookla. Speedtest Open Data Performance Maps Overview. https://github.com/teamookla/ookla-open-data. Accessed 13 September 2026.
3. Amazon Web Services Open Data Registry. Speedtest by Ookla Global Fixed and Mobile Network Performance Map Tiles. https://registry.opendata.aws/speedtest-global-performance/. Accessed 13 September 2026.
