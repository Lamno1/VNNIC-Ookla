# Target Journal Selection

Date verified: 13 September 2026  
Source manuscript: journal-neutral LaTeX converted from Revision 03  
Claim ceiling: descriptive measurement

## Decision

**Primary target: Information Development — Original Article.**

This is the best current fit because the journal explicitly welcomes original articles on current and specific aspects of information work from a practical rather than necessarily theoretical viewpoint, emphasizes problems in developing countries, and includes telecommunications within its scope. The paper's comparison of two province-level broadband measurement systems in Vietnam can therefore be positioned as a transparent measurement and information-infrastructure contribution without manufacturing a causal or policy-effect claim.

The official author instructions permit articles of 3,000–10,000 words, require an abstract of no more than 150 words and five or six keywords, accept LaTeX, require double-anonymized review files, and permit online supplemental material. The subscription route has no submission or publication fee; optional open access is available separately. Figures must be supplied at 300 dpi. The journal encourages repository sharing and a data-availability statement, subject to legal and ethical restrictions.

Official evidence:

- Scope and journal overview: https://journals.sagepub.com/home/idv
- Author instructions: https://journals.sagepub.com/author-instructions/idv

## Backup 1

**Digital Geography and Society — research article.**

This has the strongest topical fit with digital geography, spatial measurement and place-based divergence. The official journal page describes an interdisciplinary social-science and humanities remit focused on geographies relating to the digital. It is fully open access. On the page retrieved for this review, the displayed geographically adjusted APC was USD 600 against a standard USD 1,200, with 88 days to first decision and 296 days review time. Those commercial and timing fields are dynamic and must be rechecked immediately before submission.

Its main desk-rejection risk is conceptual: the manuscript must make the spatial and construct-dependent implications of measurement divergence explicit, rather than read as a technical comparison of data products. The current evidence can support that framing without expanding its claim ceiling.

Official evidence:

- Journal scope, APC display and journal insights: https://www.sciencedirect.com/journal/digital-geography-and-society
- Guide for authors entry point: https://www.sciencedirect.com/journal/digital-geography-and-society/publish/guide-for-authors

## Backup 2

**The Electronic Journal of Information Systems in Developing Countries — Research Article.**

EJISDC explicitly publishes empirical Information Systems research in identifiable Global South contexts. Its Research Articles may use diverse methods and normally should not exceed 10,000 words excluding references and appendices. It accepts a 250-word abstract and requires strong contextualization of the developing-country setting.

This is a defensible backup, but it has a higher theory-fit burden than Information Development. The manuscript would need to explain why dual-source broadband measurement is an Information Systems problem grounded in Vietnam's institutional and data-production context; the journal explicitly warns that location in a developing country alone is insufficient. That requirement can guide framing but must not be used to invent a new empirical result.

Official evidence:

- Scope and author requirements: https://onlinelibrary.wiley.com/page/journal/16814835/homepage/forauthors.html
- Journal homepage: https://onlinelibrary.wiley.com/journal/16814835

## Comparative ranking

| Criterion | Information Development | Digital Geography and Society | EJISDC |
|---|---|---|---|
| Measurement-method fit | High | High | Moderate |
| Digital inequality/spatial fit | Moderate–high | Very high | Moderate |
| Descriptive design accepted without causal identification | High | Plausible, subject to conceptual contribution | Plausible, subject to theory/context contribution |
| Single-country international fit | High when context is explained | High when spatial implications generalize | High only with substantive Global South contextualization |
| Main-text length | 3,000–10,000 words | Verify at packaging from live guide | Normally ≤10,000 words excluding references/appendices |
| Supplement support | Explicit | Publisher workflow supports research-data/supplement files; verify exact journal options | Appendices excluded from stated main-text limit; submission packaging to be rechecked |
| Data/code policy | Sharing encouraged; data-availability statement | Elsevier research-data policy applies; exact journal option to be verified | Wiley author policy applies; exact repository wording to be verified |
| Standard publication fee | None on subscription route | Gold OA; displayed APC USD 600, standard USD 1,200 on review date | Verify current licensing/APC route at submission |
| Principal desk risk | Paper framed too narrowly as network engineering | Insufficient critical/spatial interpretation | Insufficient IS theory and local contextualization |

Publication time is not used as a tie-breaker where the publisher does not display a stable journal-specific metric. No unverified estimate is presented as fact.

## Locked packaging strategy

The main article will answer five questions only: common-direction trend, cross-province dispersion, annual rank agreement, province-specific change agreement, and measurement-composition concern. It will not include enterprise outcomes, H2, regression, Decision 2269 treatment language, or a claim that one system is the ground truth.

The full 130-page audit PDF remains immutable. Journal packaging will create new main and supplement files; it will not delete or rewrite the underlying evidence. The mapping is locked in `artifacts/manifests/main_supplement_split_manifest.csv`.

## Gate decision

```text
TARGET_JOURNAL = INFORMATION_DEVELOPMENT
ARTICLE_TYPE = ORIGINAL_ARTICLE
BACKUP_JOURNALS = 2
SCOPE_FIT = PASS
ARTICLE_TYPE_CONFIRMED = true
SUBMISSION_REQUIREMENTS_VERIFIED = true
MAIN_SUPPLEMENT_SPLIT_PLAN = LOCKED
MODEL_RUN = false
CAUSAL_GATE = CLOSED
NEXT_STAGE = JOURNAL_SPECIFIC_PACKAGING
```

The requirement verification is sufficient to select and package for the primary target. Dynamic fees, submission-portal fields and publisher policies must be checked again on the actual submission date.
