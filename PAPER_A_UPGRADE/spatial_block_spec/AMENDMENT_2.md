# Amendment 2 (3 November 2026, written and hashed before any new computation)

Cause: the advisor asked for spatial blocks based on geographic neighbour relations (spatial contiguity), a description of how blocks are built and their sizes, and a check that results are stable when the grouping changes. The blocks of the first run (Ward clustering of projected province centroids, k = 12, no adjacency constraint) are close in distance but not guaranteed to be contiguous, and only two groupings (12 blocks, 6 regions) were compared. SPEC.md and AMENDMENT_1.md are unchanged.

A1. Adjacency. Two provinces are neighbours if their polygons in CANONICAL_ADM1_63.geojson (projected to EPSG:32648) touch or intersect. Checked before this amendment: 135 neighbour pairs, one connected component of 63 provinces, so no tolerance or island rule is needed.

A2. Contiguous blocks. Agglomerative Ward clustering (scikit-learn) of the projected centroids with the adjacency graph of A1 as connectivity constraint, so every block is a connected set of provinces. Deterministic; no random element.

A3. Primary rule. The primary block rule becomes contiguous blocks with k = 12 (the number of blocks stays fixed at 12, as in SPEC.md, and is not tuned). The reason is the advisor's criterion (contiguity) and that the first rule did not enforce it; it is not a reaction to results, which have not been computed for the new blocks. The unconstrained Ward k = 12 blocks of the first run and the six administrative regions become sensitivity groupings.

A4. Sensitivity over grouping. Contiguous blocks with k = 8, 10, 15 and 20 are added. The values are fixed here and no other k is run. For each statement the report shows, for all seven groupings (contiguous k = 8, 10, 12, 15, 20; unconstrained Ward k = 12; six regions), the interval and whether it excludes zero, and the count of groupings that exclude zero. No grouping is selected by its outcome.

A5. Bootstrap. Same statistics (stat_set of spatial_block_bootstrap_20261103.py, executed from that file's own source), B = 5000, seed 20261010, same draws logic (integers over the number of blocks), percentile 95 percent intervals.

A6. Rules. R1-R6 of SPEC.md apply with "12-block interval" read as the contiguous k = 12 interval. A statement resting on exclusion of zero stays only if the contiguous k = 12 interval excludes zero and the six-region interval does not disagree; additionally a statement is reported as "depends on the grouping" if the sensitivity groupings of A4 split (some exclude zero, some do not). Point-estimate rules are unchanged.

A7. Coverage. The coverage simulation of SPEC.md section 5 is repeated for the contiguous k = 12 blocks only, with the same configurations, datasets and draws as before, because the text quotes coverage for the primary rule. If it is not completed, the text will say that coverage was simulated for the unconstrained blocks only.

A8. Reporting. Block construction (adjacency, constraint, number of blocks), block sizes of the primary rule, and the stability table across groupings go in the supplementary note S8; the main text states the primary rule with its correct name ("contiguous blocks") and one sentence on stability across groupings.
