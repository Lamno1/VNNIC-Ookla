# Common Direction, Divergent Rankings

## A Multi-Level Comparison of VNNIC and Ookla Broadband Measurements in Vietnam, 2021–2024

## Abstract

Broadband comparisons often treat administrative and crowdsourced speed-test systems as interchangeable. We compare VNNIC i-Speed and Ookla fixed-broadband measurements across 63 historical Vietnamese provinces during 2021–2024, separating common direction, dispersion, yearly rank, and change-rank agreement. Both sources report higher performance in every province, and five of six dispersion indicators point to a wider distribution. Yet yearly Spearman correlations fall from 0.542 to 0.248, while the change-rank correlation is -0.247 and remains negative across four Ookla aggregation rules. Ookla speed changes also co-vary with observed tests and devices. Thus, the sources support a common aggregate direction and broadly similar dispersion, but not source-invariant provincial rankings or improvement. Provincial connectivity comparisons depend on the construct and aggregation system used.

## 1 Introduction

Broadband indicators increasingly inform digital-inclusion diagnosis, infrastructure targeting, and comparisons among places. Yet an indicator is not the underlying construct itself. Administrative dashboards, user-initiated tests, passive probes, advertised-speed records, and coverage maps differ in who or what is observed, how observations enter the sample, and how measurements are aggregated. Treating these systems as interchangeable can therefore turn method variance into an apparent geographic difference [4–7].

Vietnam provides a useful test of this problem. VNNIC publishes province-month i-Speed summaries through its Internet Atlas interface [1], whereas Ookla distributes quarterly fixed-broadband performance aggregates for observed zoom-level-16 tiles [2,3]. Both report download performance in familiar units, but they do not necessarily represent the same population, spatial support, or statistical estimand. Prior broadband research has shown that realized speed can differ from advertised availability, that crowdsourced tests require contextualization, and that participation and subscription choices can shape measured performance [8–13]. Research on Vietnam also shows why connectivity should not be reduced to a single access indicator: adoption, capability, geography, and socioeconomic position constitute distinct dimensions of digital inequality [14–16].

We ask how agreement changes as the comparison becomes more demanding. The analysis separates four levels: common direction, cross-province dispersion, yearly provincial rank, and rank of province-specific change. The distinction is consequential. Agreement that nearly all places improved does not establish agreement about which places performed best or improved most.

The study contributes a reusable measurement framework rather than a contest to identify a winning source. It preserves symmetric aggregation alternatives, leave-one-province-out diagnostics, and composition checks without selecting the specification that most closely aligns the systems. The contribution is descriptive: neither series is treated as ground truth, and no policy or infrastructure effect is estimated.

## 2 Related Work and Measurement Framework

### 2.1 Construct validity without a gold standard

Construct validity concerns whether an operational measure supports the interpretation assigned to it, not whether a variable merely has a plausible label [4]. Cronbach and Meehl framed validation as the accumulation of evidence within a nomological network, while Campbell and Fiske emphasized that observed variation combines construct and method components [4,5]. Later accounts similarly treat validity as an argument supported by multiple forms of evidence rather than a permanent property of an instrument [6,7]. This perspective is especially relevant when no criterion measure can serve as ground truth. Cross-source agreement can support convergent interpretation, but disagreement does not by itself identify which measure is erroneous.

Our four-level framework applies this logic to spatial broadband indicators. Common-direction agreement concerns the sign of aggregate movement. Dispersion agreement concerns the shape of the cross-place distribution. Rank agreement asks whether systems order places similarly at a given time. Change-rank agreement asks whether they order local improvement similarly. These levels are nested in substantive difficulty but not logically equivalent: strong agreement at one level need not propagate to the next.

### 2.2 Broadband measurement systems

Internet performance measurement has long distinguished advertised availability from realized user experience. Regulatory or provider records can misstate local availability, while end-user tests observe performance only among participating users and devices [8,9]. Gateway-based measurement demonstrates the importance of observing the access link under controlled conditions, whereas crowdsourced systems trade experimental control for geographic and temporal scale [10]. Comparative work shows that platforms such as Ookla and M-Lab can produce different throughput estimates for the same subscription context because protocols, servers, devices, access links, and user initiation differ [11]. Consequently, a speed-test value may reflect service tier, in-home Wi-Fi, device capability, congestion, and test motivation as well as access-network performance [11].

Spatial aggregation adds another layer. Riddlesden and Singleton used millions of crowdsourced observations to document broadband-speed inequalities in England while also identifying geographic variation in test propensity [12]. Gallardo and Whitacre show that Ookla-based speed measures reveal dimensions of digital inequality that differ from binary availability or adoption measures [13]. These studies justify using end-user tests, but they also caution against interpreting non-probability samples as population-representative measures. The present study extends that literature by comparing two operational systems within one fixed provincial geography and by separating aggregate agreement from province-specific agreement.

### 2.3 Digital inequality in Vietnam and Southeast Asia

Digital inequality research increasingly distinguishes access from quality, skills, and effective use [14,16–19]. Evidence from Vietnam identifies socioeconomic and ethnic differences in technology adoption even during rapid diffusion [15]. Work on domestic bandwidth inequality and successive levels of access further shows that infrastructure, use, and outcomes should not be collapsed into one indicator [16–20]. These findings motivate attention to subnational connectivity but do not imply that a speed-test series alone measures digital inclusion. Our analysis therefore treats measured fixed-broadband download performance as one technical dimension and avoids claims about adoption, affordability, skills, or welfare.

## 3 Measurement Systems and Constructs

### 3.1 VNNIC i-Speed

The VNNIC construct is a published province-level fixed-broadband user-experience statistic. The official interface identifies the statistic as a median and reports download speed in Mbps, subject to a minimum 30-sample publication rule [1]. For within-source annual description, we use the unweighted median of the nine published monthly values from April through December. For the matched cross-source comparison, we use the median for April through June. The series is not interpreted as physical network capacity, household coverage, or population-weighted service quality. The available documentation does not completely resolve test and device composition or retrospective revision practice.

### 3.2 Ookla Open Data

Ookla Open Data report `avg_d_kbps` as the average download speed of tests observed within each tile, together with counts of tests and unique devices [2]. We convert kilobits per second to Mbps and assign each tile centroid to one canonical province. The primary province-quarter statistic is the unweighted median across assigned observed tiles. This is a spatial tile median, not a person-, household-, subscriber-, or device-level median. The AWS Open Data registry documents the quarterly fixed and mobile map-tile archive and notes its public distribution [3].

### 3.3 Why the constructs are not interchangeable

VNNIC begins with a published locality-month statistic; Ookla begins with quarterly tile aggregates and requires a second aggregation to provinces. Equal units do not make the underlying estimands equal. Different participation patterns, spatial support, within-tile averaging, province aggregation, and revision practices can yield common aggregate trends alongside different local rankings.

## 4 Data and Methods

### 4.1 Scope and geography

The study covers 2021 through 2024 and uses a fixed 63-province analytical geography. The geometry was distributed in the 2021 geoBoundaries release and carries metadata boundary year 2016. Fixing the geography prevents administrative-vintage changes from entering the comparison. Province identifiers, rather than names, link all connectivity records. For Ookla, each tile centroid was decoded in longitude–latitude order and assigned deterministically to exactly one valid Polygon or MultiPolygon in the frozen geometry. Points outside Vietnam were separated from assignment failures; ambiguous or boundary points were quarantined and excluded rather than assigned by row order. The pipeline recorded source-row accounting, assignment status, canonical-boundary hash, geometry-engine version, and 63-province coverage. Centroid assignment is reproducible but remains an approximation for tiles intersecting coastlines or provincial boundaries.

The VNNIC description contains 63 provinces in every year. The Ookla pilot processes fixed-broadband Q2 files for the same four years and produces 252 province-year aggregates. All provinces are represented in each year. No province is excluded from the reported comparisons.

### 4.2 Within-source description

For VNNIC we report the mean, median, standard deviation, coefficient of variation, interquartile range, percentile ratios, extrema, maps, and rank mobility. The unweighted average-province download mean rises from 48.16 Mbps in 2021 to 89.18 Mbps in 2024; the corresponding medians are 48.07 and 91.14 Mbps. Every province records a positive 2021-to-2024 change, with a median increase of 42.34 Mbps.

Dispersion is assessed jointly using six registered measures: the standard deviations of levels and logs, coefficient of variation, interquartile range, p90-to-p10 ratio, and maximum-to-minimum ratio. No single measure determines the interpretation.

### 4.3 Cross-source comparison

The primary timing match compares Ookla Q2 with VNNIC April-June. We calculate yearly Spearman rank correlation, Pearson correlation of positive log levels, absolute rank differences, median-split agreement, and 2021-to-2024 change-rank agreement. A secondary comparison uses the VNNIC April-December measure and is explicitly temporally mismatched.

We retain the preregistered Ookla definition, the unweighted tile median, regardless of its agreement with VNNIC. Three alternatives are reported symmetrically: unweighted tile mean, tests-weighted mean, and devices-weighted mean. Post-hoc leave-one-province-out and composition checks are labeled as such and do not alter the original mixed-measurement decision.

## 5 Results

### 5.1 Broad improvement and dispersion

The province distribution shifts upward between 2021 and 2024 (Figures 1–4). All 63 VNNIC provinces have a positive endpoint change, and the unweighted province median rises from 48.07 to 91.14 Mbps. This establishes broad improvement within the published series; it is not a population-weighted national estimate.

Endpoint comparisons also indicate wider cross-province dispersion. All six registered VNNIC indicators are higher in 2024 than in 2021, although they do not move monotonically in every intervening year. In the matched-Q2 comparison, five of six dispersion indicators have the same endpoint direction across VNNIC and Ookla (Figure 12). The tables retain the complete declared statistics; the text emphasizes their joint pattern rather than repeating every cell.

### 5.2 Rank persistence within VNNIC

VNNIC provincial ranks show moderate and uneven persistence (Figure 5). Spearman persistence equals 0.448 for 2021-2022, 0.273 for 2021-2023, 0.475 for 2021-2024, 0.788 for 2022-2023, and 0.504 for 2023-2024. Between 2021 and 2024, 20 provinces remain in the same quartile, 18 move up one quartile, five move up at least two, 12 move down one, and eight move down at least two. These movements describe the published VNNIC ordering only.

### 5.3 Cross-source provincial ranks

Yearly rank agreement is positive but declines across the period (Figure 10). Spearman rank correlations between the primary Ookla aggregate and matched VNNIC Q2 measure are 0.542 in 2021, 0.488 in 2022, 0.296 in 2023, and 0.248 in 2024. Pearson correlations of log levels likewise move from 0.584 and 0.539 in the first two years to 0.220 and 0.047 in the last two. Depending on year, 20 to 29 provinces differ by more than 15 rank positions. Thus, a shared upward shift does not preserve a stable cross-source provincial ordering.

### 5.4 Province-specific changes

Between their matched-Q2 observations in 2021 and 2024, the two systems agree on the sign of change for all 63 provinces, but not on relative improvement (Figure 11). The primary Spearman correlation between 2021-to-2024 province changes is -0.247. A province that rises more in one system therefore does not generally rise more in the other. This result separates common-trend agreement from agreement about local improvement intensity.

### 5.5 Aggregation, influence, and composition diagnostics

All four Ookla aggregation variants retain a negative change-rank correlation: -0.247 for the unweighted tile median, -0.193 for the unweighted tile mean, -0.178 for the tests-weighted mean, and -0.169 for the devices-weighted mean. Weighting changes magnitudes but does not restore positive province-specific change agreement. These comparisons are post-hoc measurement diagnostics and are not substitutes for the preregistered primary aggregation.

Leave-one-province-out checks do not reverse the overall interpretation. Every influence flag is retained, so the analysis does not manufacture agreement by deleting provinces. Composition concern remains material: for the primary tile median, Ookla speed change has Pearson and Spearman associations of 0.591 and 0.545 with changes in tests, and 0.583 and 0.535 with changes in devices. These patterns heighten concern that province-change comparisons may be sensitive to observed test and device participation; they do not identify the source or magnitude of any measurement bias.

## 6 Discussion

Measurement agreement depends on the level of comparison. At the broadest level, both sources record improvement across every province. At the distributional level, most declared indicators point toward increasing cross-province dispersion. At the cross-sectional level, provincial ranks align only moderately in the early years and weakly later. At the change level, the ordering is negative across every reasonable Ookla aggregation examined.

The evidence is consistent with related but non-equivalent measurement constructs. VNNIC publishes a locality-month statistic after its own eligibility and aggregation rules. Ookla observes a changing spatial set of tests and devices, summarizes within tiles, and is then aggregated across tiles. The observed differences may arise from participation, spatial support, implicit weights, timing, or revision practice. The available diagnostics do not identify one explanation as definitive.

This decomposition changes the interpretation of measured cross-province connectivity differences. Statements about broad improvement are robust across these two sources. Statements about wider provincial dispersion receive substantial, though not universal, support. Statements that identify the best-connected provinces or the places improving fastest are much more source-dependent. A single measurement series can therefore be adequate for one descriptive claim and inadequate for another.


This pattern is consistent with prior warnings that speed-test measures require contextualization [9,11] and that geographic test propensity can vary systematically [12]. It also complements work using Ookla to study digital inequality [13]: end-user speed is informative, but the resulting geographic ordering is conditional on the measurement chain. Our contribution is to show empirically that agreement can remain strong for common direction and dispersion while weakening sharply for ranks and change ranks.

The absence of an external ground truth is a design boundary, not a reason to declare one source inaccurate. The data cannot determine whether a particular provincial discrepancy reflects true heterogeneous change, participation, subscription tiers, devices, spatial support, timing, or revision. Accordingly, the negative change-rank correlation diagnoses non-interchangeability; it does not identify a measurement-error correction.

For policy use, the safest implication concerns indicator governance. Agencies may reasonably use multiple sources to monitor broad direction, but should not allocate resources or publicly rank “fastest-improving” provinces from a single system without documenting its construct, participation process, aggregation rule, and stability. The results do not identify which provinces should receive funding and do not evaluate any Vietnamese programme.

## 7 Limitations

First, both systems depend on speed-test participation and do not form probability samples of residents, households, or locations. Second, VNNIC's test/device composition and historical revision process are incompletely documented. Third, Ookla observed tiles do not constitute a documented geographic-coverage denominator, and centroid assignment differs from area allocation near boundaries. Fourth, the main cross-source validation covers Q2 in four years; it does not establish seasonality or temporal reliability across every quarter. Additional quarters require a separately registered extension rather than post-result selection. Fifth, aggregation sensitivity can reveal dependence on implicit weights but cannot establish which aggregation is substantively correct. Sixth, the 63-province geometry is a fixed analytical reference with metadata boundary year 2016, not a claim of month-specific historical boundaries.

These limitations restrict the claims to descriptive measurement comparisons. The study does not designate either source as ground truth. Without an external criterion or controlled measurement frame, it cannot partition observed disagreement into true local change and source-specific error. It does not interpret agreement as infrastructure activation or population coverage, and it does not attribute the reported patterns to a particular programme or mechanism. The VNNIC 30-sample publication threshold is verified, but the available aggregate series does not reveal the number of suppressed below-threshold locality-month cells; complete publication for the locked window therefore cannot be interpreted as evidence that no selection occurred upstream.

## 8 Conclusion

Across the 63 matched province-level Q2 observations, VNNIC and Ookla show a common positive direction between 2021 and 2024 and mostly agree that the measured cross-province distributions widened between those endpoints. They do not tell a common story about provincial ordering or which provinces improved most. The loss of agreement from aggregate direction to province-specific change persists across four Ookla aggregation choices and remains negative in the leave-one-province-out diagnostics; all provinces remain in the reported sample. Observed changes in tests and devices remain an important composition concern.

The practical conclusion is narrow but consequential: the measured extent and ordering of cross-province connectivity differences depend partly on the construct and measurement system used. Future work should define the intended construct before selecting a source and should establish temporal and composition reliability before treating province-specific change as a stable exposure.

## References

1. Vietnam Internet Network Information Center. VNNIC Internet Atlas i-Speed. https://internetatlas.vnnic.vn/i-speed. Accessed 13 September 2026.
2. Ookla. Speedtest Open Data Performance Maps Overview. https://github.com/teamookla/ookla-open-data. Accessed 13 September 2026.
3. Amazon Web Services Open Data Registry. Speedtest by Ookla Global Fixed and Mobile Network Performance Map Tiles. https://registry.opendata.aws/speedtest-global-performance/. Accessed 13 September 2026.
4. Cronbach LJ and Meehl PE. Construct validity in psychological tests. Psychological Bulletin 1955; 52(4): 281–302. doi:10.1037/h0040957.
5. Campbell DT and Fiske DW. Convergent and discriminant validation by the multitrait-multimethod matrix. Psychological Bulletin 1959; 56(2): 81–105. doi:10.1037/h0046016.
6. Messick S. Validity of psychological assessment: Validation of inferences from persons' responses and performances as scientific inquiry into score meaning. American Psychologist 1995; 50(9): 741–749. doi:10.1037/0003-066X.50.9.741.
7. Adcock R and Collier D. Measurement validity: A shared standard for qualitative and quantitative research. American Political Science Review 2001; 95(3): 529–546. doi:10.1017/S0003055401003100.
8. Grubesic TH. The U.S. national broadband map: Data limitations and implications. Telecommunications Policy 2012; 36(2): 113–126. doi:10.1016/j.telpol.2011.11.012.
9. Feamster N and Livingood J. Measuring Internet speed: Current challenges and future recommendations. Communications of the ACM 2020; 63(12): 72–80. doi:10.1145/3372135.
10. Sundaresan S, de Donato W, Feamster N, et al. Broadband Internet performance: A view from the gateway. In: Proceedings of ACM SIGCOMM 2011. doi:10.1145/2018436.2018452.
11. Paul U, Liu J, Gu M, Gupta A and Belding E. The importance of contextualization of crowdsourced active speed test measurements. In: Proceedings of the 22nd ACM Internet Measurement Conference, 2022, pp. 697–714. doi:10.1145/3517745.3561441.
12. Riddlesden D and Singleton AD. Broadband speed equity: A new digital divide? Applied Geography 2014; 52: 25–33. doi:10.1016/j.apgeog.2014.04.008.
13. Gallardo R and Whitacre B. An unexpected digital divide? A look at internet speeds and socioeconomic groups. Telecommunications Policy 2024; 48(6): 102777. doi:10.1016/j.telpol.2024.102777.
14. Sharp M. Revisiting the measurement of digital inclusion. The World Bank Research Observer 2024; 39(2): 289–318. doi:10.1093/wbro/lkad007.
15. Kaila H. Ethnic digital divide? Evidence on mobile phone adoption. Applied Economics 2023; 55(22): 2536–2550. doi:10.1080/00036846.2022.2103502.
16. Hilbert M. The bad news is that the digital access divide is here to stay: Domestically installed bandwidths among 172 countries for 1986–2014. Telecommunications Policy 2016; 40(6): 567–581. doi:10.1016/j.telpol.2016.01.006.
17. van Deursen AJAM and van Dijk JAGM. The first-level digital divide shifts from inequalities in physical access to inequalities in material access. New Media & Society 2019; 21(2): 354–375. doi:10.1177/1461444818797082.
18. Helsper EJ. A corresponding fields model for the links between social and digital exclusion. Communication Theory 2012; 22(4): 403–426. doi:10.1111/j.1468-2885.2012.01416.x.
19. Scheerder A, van Deursen A and van Dijk J. Determinants of Internet skills, uses and outcomes: A systematic review of the second- and third-level digital divide. Telematics and Informatics 2017; 34(8): 1607–1624. doi:10.1016/j.tele.2017.07.007.
20. Lutz C. Digital inequalities in the age of artificial intelligence and big data. Human Behavior and Emerging Technologies 2019; 1(2): 141–148. doi:10.1002/hbe2.140.
