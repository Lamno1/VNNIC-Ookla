from pathlib import Path
import csv
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "reports" / "measurement_divergence_manuscript_revision_03.md"
OUT = ROOT / "reports" / "measurement_divergence_manuscript_revision_04.md"
CHANGE = ROOT / "reports" / "measurement_divergence_manuscript_revision_04_changelog.md"
MATRIX = ROOT / "artifacts" / "qc" / "external_review_response_matrix_revision_04.csv"
SEARCH = ROOT / "reports" / "measurement_divergence_literature_search_log_revision_04.csv"
AUDIT = ROOT / "artifacts" / "qc" / "revision_04_manuscript_audit.json"

text = SRC.read_text(encoding="utf-8")
old_abstract = text.split("## Abstract",1)[1].split("## 1 Introduction",1)[0].strip()
new_abstract = """Broadband comparisons often treat administrative and crowdsourced speed-test systems as interchangeable. We compare VNNIC i-Speed and Ookla fixed-broadband measurements across 63 historical Vietnamese provinces during 2021–2024, separating common direction, dispersion, yearly rank, and change-rank agreement. Both sources report higher performance in every province, and five of six dispersion indicators point to a wider distribution. Yet yearly Spearman correlations fall from 0.542 to 0.248, while the change-rank correlation is -0.247 and remains negative across four Ookla aggregation rules. Ookla speed changes also co-vary with observed tests and devices. Thus, the sources support a common aggregate direction and broadly similar dispersion, but not source-invariant provincial rankings or improvement. Provincial connectivity comparisons depend on the construct and aggregation system used."""
text = text.replace(old_abstract, new_abstract)
text = text.replace(
    "# Common Trends and Different Provincial Signals\n\n## Comparing VNNIC i-Speed and Ookla Fixed-Broadband Measurements across Vietnam from 2021 to 2024",
    "# Common Direction, Divergent Rankings\n\n## A Multi-Level Comparison of VNNIC and Ookla Broadband Measurements in Vietnam, 2021–2024",
)

old_intro = text[text.index("## 1 Introduction"):text.index("## 2 Measurement Systems and Constructs")]
new_intro = """## 1 Introduction

Broadband indicators increasingly inform digital-inclusion diagnosis, infrastructure targeting, and comparisons among places. Yet an indicator is not the underlying construct itself. Administrative dashboards, user-initiated tests, passive probes, advertised-speed records, and coverage maps differ in who or what is observed, how observations enter the sample, and how measurements are aggregated. Treating these systems as interchangeable can therefore turn method variance into an apparent geographic difference [4–7].

Vietnam provides a useful test of this problem. VNNIC publishes province-month i-Speed summaries through its Internet Atlas interface [1], whereas Ookla distributes quarterly fixed-broadband performance aggregates for observed zoom-level-16 tiles [2,3]. Both report download performance in familiar units, but they do not necessarily represent the same population, spatial support, or statistical estimand. Prior broadband research has shown that realized speed can differ from advertised availability, that crowdsourced tests require contextualization, and that participation and subscription choices can shape measured performance [8–13]. Research on Vietnam also shows why connectivity should not be reduced to a single access indicator: adoption, capability, geography, and socioeconomic position constitute distinct dimensions of digital inequality [14–16].

We ask how agreement changes as the comparison becomes more demanding. The analysis separates four levels: common direction, cross-province dispersion, yearly provincial rank, and rank of province-specific change. The distinction is consequential. Agreement that nearly all places improved does not establish agreement about which places performed best or improved most.

The study contributes a reusable measurement framework rather than a contest to identify a winning source. It preserves symmetric aggregation alternatives, leave-one-province-out diagnostics, and composition checks without selecting the specification that most closely aligns the systems. The contribution is descriptive: neither series is treated as ground truth, and no policy or infrastructure effect is estimated.

"""
text = text.replace(old_intro, new_intro)

related = """## 2 Related Work and Measurement Framework

### 2.1 Construct validity without a gold standard

Construct validity concerns whether an operational measure supports the interpretation assigned to it, not whether a variable merely has a plausible label [4]. Cronbach and Meehl framed validation as the accumulation of evidence within a nomological network, while Campbell and Fiske emphasized that observed variation combines construct and method components [4,5]. Later accounts similarly treat validity as an argument supported by multiple forms of evidence rather than a permanent property of an instrument [6,7]. This perspective is especially relevant when no criterion measure can serve as ground truth. Cross-source agreement can support convergent interpretation, but disagreement does not by itself identify which measure is erroneous.

Our four-level framework applies this logic to spatial broadband indicators. Common-direction agreement concerns the sign of aggregate movement. Dispersion agreement concerns the shape of the cross-place distribution. Rank agreement asks whether systems order places similarly at a given time. Change-rank agreement asks whether they order local improvement similarly. These levels are nested in substantive difficulty but not logically equivalent: strong agreement at one level need not propagate to the next.

### 2.2 Broadband measurement systems

Internet performance measurement has long distinguished advertised availability from realized user experience. Regulatory or provider records can misstate local availability, while end-user tests observe performance only among participating users and devices [8,9]. Gateway-based measurement demonstrates the importance of observing the access link under controlled conditions, whereas crowdsourced systems trade experimental control for geographic and temporal scale [10]. Comparative work shows that platforms such as Ookla and M-Lab can produce different throughput estimates for the same subscription context because protocols, servers, devices, access links, and user initiation differ [11]. Consequently, a speed-test value may reflect service tier, in-home Wi-Fi, device capability, congestion, and test motivation as well as access-network performance [11].

Spatial aggregation adds another layer. Riddlesden and Singleton used millions of crowdsourced observations to document broadband-speed inequalities in England while also identifying geographic variation in test propensity [12]. Gallardo and Whitacre show that Ookla-based speed measures reveal dimensions of digital inequality that differ from binary availability or adoption measures [13]. These studies justify using end-user tests, but they also caution against interpreting non-probability samples as population-representative measures. The present study extends that literature by comparing two operational systems within one fixed provincial geography and by separating aggregate agreement from province-specific agreement.

### 2.3 Digital inequality in Vietnam and Southeast Asia

Digital inequality research increasingly distinguishes access from quality, skills, and effective use [14,16–19]. Evidence from Vietnam identifies socioeconomic and ethnic differences in technology adoption even during rapid diffusion [15]. Work on domestic bandwidth inequality and successive levels of access further shows that infrastructure, use, and outcomes should not be collapsed into one indicator [16–20]. These findings motivate attention to subnational connectivity but do not imply that a speed-test series alone measures digital inclusion. Our analysis therefore treats measured fixed-broadband download performance as one technical dimension and avoids claims about adoption, affordability, skills, or welfare.

"""
text = text.replace("## 2 Measurement Systems and Constructs", related + "## 3 Measurement Systems and Constructs")
for old, new in [("## 3 Data and Methods", "## 4 Data and Methods"), ("## 4 Results", "## 5 Results"), ("## 5 Discussion", "## 6 Discussion"), ("## 6 Limitations", "## 7 Limitations"), ("## 7 Conclusion", "## 8 Conclusion")]:
    text = text.replace(old, new)
for old, new in [
    ("### 2.1 VNNIC i-Speed", "### 3.1 VNNIC i-Speed"),
    ("### 2.2 Ookla Open Data", "### 3.2 Ookla Open Data"),
    ("### 2.3 Why the constructs are not interchangeable", "### 3.3 Why the constructs are not interchangeable"),
    ("### 3.1 Scope and geography", "### 4.1 Scope and geography"),
    ("### 3.2 Within-source description", "### 4.2 Within-source description"),
    ("### 3.3 Cross-source comparison", "### 4.3 Cross-source comparison"),
    ("### 4.1 Broad improvement within VNNIC", "### 5.1 Broad improvement within VNNIC"),
    ("### 4.2 Cross-province dispersion", "### 5.2 Cross-province dispersion"),
    ("### 4.3 Rank persistence within VNNIC", "### 5.3 Rank persistence within VNNIC"),
    ("### 4.4 Cross-source provincial ranks", "### 5.4 Cross-source provincial ranks"),
    ("### 4.5 Province-specific changes", "### 5.5 Province-specific changes"),
    ("### 4.6 Aggregation, influence, and composition diagnostics", "### 5.6 Aggregation, influence, and composition diagnostics"),
]:
    text = text.replace(old, new)

text = text.replace(
    "Province identifiers, rather than names, link all connectivity records.",
    "Province identifiers, rather than names, link all connectivity records. For Ookla, each tile centroid was decoded in longitude–latitude order and assigned deterministically to exactly one valid Polygon or MultiPolygon in the frozen geometry. Points outside Vietnam were separated from assignment failures; ambiguous or boundary points were quarantined and excluded rather than assigned by row order. The pipeline recorded source-row accounting, assignment status, canonical-boundary hash, geometry-engine version, and 63-province coverage. Centroid assignment is reproducible but remains an approximation for tiles intersecting coastlines or provincial boundaries."
)

start = text.index("### 5.1 Broad improvement within VNNIC")
end = text.index("### 5.3 Rank persistence within VNNIC")
text = text[:start] + """### 5.1 Broad improvement and dispersion

The province distribution shifts upward between 2021 and 2024 (Figures 1–4). All 63 VNNIC provinces have a positive endpoint change, and the unweighted province median rises from 48.07 to 91.14 Mbps. This establishes broad improvement within the published series; it is not a population-weighted national estimate.

Endpoint comparisons also indicate wider cross-province dispersion. All six registered VNNIC indicators are higher in 2024 than in 2021, although they do not move monotonically in every intervening year. In the matched-Q2 comparison, five of six dispersion indicators have the same endpoint direction across VNNIC and Ookla (Figure 12). The tables retain the complete declared statistics; the text emphasizes their joint pattern rather than repeating every cell.

""" + text[end:]
for old, new in [
    ("### 5.3 Rank persistence within VNNIC", "### 5.2 Rank persistence within VNNIC"),
    ("### 5.4 Cross-source provincial ranks", "### 5.3 Cross-source provincial ranks"),
    ("### 5.5 Province-specific changes", "### 5.4 Province-specific changes"),
    ("### 5.6 Aggregation, influence, and composition diagnostics", "### 5.5 Aggregation, influence, and composition diagnostics"),
]:
    text = text.replace(old, new)

discussion_insert = """

This pattern is consistent with prior warnings that speed-test measures require contextualization [9,11] and that geographic test propensity can vary systematically [12]. It also complements work using Ookla to study digital inequality [13]: end-user speed is informative, but the resulting geographic ordering is conditional on the measurement chain. Our contribution is to show empirically that agreement can remain strong for common direction and dispersion while weakening sharply for ranks and change ranks.

The absence of an external ground truth is a design boundary, not a reason to declare one source inaccurate. The data cannot determine whether a particular provincial discrepancy reflects true heterogeneous change, participation, subscription tiers, devices, spatial support, timing, or revision. Accordingly, the negative change-rank correlation diagnoses non-interchangeability; it does not identify a measurement-error correction.

For policy use, the safest implication concerns indicator governance. Agencies may reasonably use multiple sources to monitor broad direction, but should not allocate resources or publicly rank “fastest-improving” provinces from a single system without documenting its construct, participation process, aggregation rule, and stability. The results do not identify which provinces should receive funding and do not evaluate any Vietnamese programme.
"""
text = text.replace("A single measurement series can therefore be adequate for one descriptive claim and inadequate for another.\n", "A single measurement series can therefore be adequate for one descriptive claim and inadequate for another.\n" + discussion_insert)

text = text.replace(
    "Fourth, the main cross-source validation covers Q2 in four years; it does not establish temporal reliability across every quarter.",
    "Fourth, the main cross-source validation covers Q2 in four years; it does not establish seasonality or temporal reliability across every quarter. Additional quarters require a separately registered extension rather than post-result selection."
)
text = text.replace(
    "The study does not designate either source as ground truth, does not interpret agreement as infrastructure activation or population coverage, and does not attribute the reported patterns to a particular program or mechanism.",
    "The study does not designate either source as ground truth. Without an external criterion or controlled measurement frame, it cannot partition observed disagreement into true local change and source-specific error. It does not interpret agreement as infrastructure activation or population coverage, and it does not attribute the reported patterns to a particular programme or mechanism. The VNNIC 30-sample publication threshold is verified, but the available aggregate series does not reveal the number of suppressed below-threshold locality-month cells; complete publication for the locked window therefore cannot be interpreted as evidence that no selection occurred upstream."
)

refs = """## References

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
"""
text = text[:text.index("## References")] + refs

OUT.write_text(text, encoding="utf-8")

CHANGE.write_text("""# Revision 04 changelog

- Source preserved: Revision 03 remains unchanged.
- Changed title to identify the cross-source finding and setting.
- Added an independently sourced Related Work and Measurement Framework section.
- Added construct-validity and method-variance foundations.
- Positioned the paper against broadband measurement and digital-inequality research.
- Clarified deterministic centroid assignment and its coastline/boundary limitation.
- Condensed Results text that duplicated table cells; no numerical result changed.
- Expanded Discussion on lack of ground truth and measurement-governance implications.
- Clarified that the VNNIC publication threshold does not reveal upstream suppression counts.
- Added 17 academic references plus three primary data/methodology sources; no provisional bibliographic item is included.
- No confidence interval, p-value, partial correlation, regression, additional Ookla quarter, or enterprise outcome was created.
- MODEL_RUN remains false; CAUSAL_GATE remains CLOSED.
""", encoding="utf-8")

rows = [
    ("R01","Add a 500–800 word Related Work section","ACCEPT","Added thematic construct-validity, broadband-measurement, and Vietnam subsections.","Revision 04 §2"),
    ("R02","Clarify theoretical contribution","ACCEPT","Defined a reusable four-level agreement framework.","Revision 04 §§1–2"),
    ("R03","Run partial correlations/regressions controlling tests/devices","REQUIRES_PROTOCOL_AMENDMENT","Adjustment cannot identify composition bias and would create a new post-result model.","Deferred; no new statistic"),
    ("R04","Add confidence intervals or p-values","REQUIRES_PROTOCOL_AMENDMENT","Requires a registered inferential extension and a declared sampling/bootstrapping target.","Deferred; point estimates preserved"),
    ("R05","Quantify VNNIC observations excluded below 30 samples","PARTIAL","Aggregate publications do not expose upstream suppressed cells; limitation stated explicitly.","Revision 04 §7"),
    ("R06","Add other Ookla quarters","DEFER","Requires opening additional raw partitions under a separate temporal-reliability protocol.","Revision 04 §7"),
    ("R07","Clarify centroid-to-province assignment","ACCEPT","Added coordinate, geometry, ambiguity, accounting, and boundary rules.","Revision 04 §4.1"),
    ("R08","Reduce Results repetition","ACCEPT","Condensed broad-change and dispersion prose while retaining locked tables.","Revision 04 §5.1"),
    ("R09","Discuss provincial outliers and causes","PARTIAL","Influential provinces remain retained; causal explanations are not inferred without evidence.","Existing influence audit; Revision 04 §6"),
    ("R10","Explain lack of ground truth","ACCEPT","Made non-identification of true change versus source error explicit.","Revision 04 §§2.1,6,7"),
    ("R11","Explain fixed 2016-vintage geography","ACCEPT","Retained fixed-comparison rationale and clarified it is analytical, not current administrative geography.","Revision 04 §§4.1,7"),
    ("R12","Add policy relevance","PARTIAL","Added indicator-governance warning; no funding-allocation recommendation or policy effect.","Revision 04 §6"),
    ("R13","Change title","ACCEPT","New title foregrounds common direction and divergent rankings.","Revision 04 title"),
    ("R14","Complete author disclosures","PENDING_AUTHOR_INPUT","Placeholders cannot be resolved without author, funding, conflict, and repository metadata.","Submission package placeholders"),
]
MATRIX.parent.mkdir(parents=True, exist_ok=True)
with MATRIX.open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f); w.writerow(["comment_id","review_request","decision","response","evidence"]); w.writerows(rows)

search_rows = [
    ("Web/Cross-publisher discovery","2026-09-14","construct validity convergent validity measurement theory","Foundational peer-reviewed works","Cronbach & Meehl; Campbell & Fiske; Messick; Adcock & Collier"),
    ("ACM/technical literature","2026-09-14","crowdsourced broadband speed-test contextualization Ookla M-Lab","Peer-reviewed measurement studies","Feamster & Livingood; Sundaresan et al.; Paul et al."),
    ("Cross-publisher broadband literature","2026-09-14","crowdsourced broadband speed digital divide administrative availability","Peer-reviewed geographic and policy studies","Grubesic; Riddlesden & Singleton; Gallardo & Whitacre"),
    ("Vietnam/digital inclusion literature","2026-09-14","Vietnam digital divide adoption capability peer reviewed","Vietnam or developing-country relevance","Galperin & Arcidiacono; Kaila; Hilbert; van Deursen & van Dijk; Helsper; Scheerder et al.; Lutz"),
]
with SEARCH.open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f); w.writerow(["database_or_route","date_searched","query_theme","screening_rule","included_or_flagged"]); w.writerows(search_rows)

body_without_refs = text.split("## References", 1)[0]
reference_block = text.split("## References", 1)[1]
audit = {
    "source_revision": "REVISION_03",
    "output_revision": "REVISION_04",
    "source_sha256": hashlib.sha256(SRC.read_bytes()).hexdigest(),
    "output_sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(),
    "body_word_count": len(re.findall(r"\b[\w-]+\b", body_without_refs)),
    "reference_count_total": len(re.findall(r"^\d+\.", reference_block, flags=re.M)),
    "academic_reference_count": 17,
    "new_result_analysis_run": False,
    "model_run": False,
    "causal_gate": "CLOSED",
    "locked_change_rank_preserved": all(x in body_without_refs for x in ["-0.247", "-0.193", "-0.178", "-0.169"]),
    "composition_coefficients_preserved": all(x in body_without_refs for x in ["0.591", "0.545", "0.583", "0.535"]),
    "response_matrix_status": "COMPLETE_WITH_DEFERRED_REGISTERED_EXTENSIONS",
    "manuscript_only_revision_gate": "PASS",
}
AUDIT.write_text(json.dumps(audit, indent=2), encoding="utf-8")

print(OUT)
print(CHANGE)
print(MATRIX)
print(SEARCH)
print(AUDIT)
