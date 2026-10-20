# ML-31 — external PDF-table Gold feasibility

20 October 2026. Documentation-only evidence review at starting HEAD
`f8fb491f0cfb2877d23e5b4ac2e26871f12e073a` on `main`.
Execution: **PASS for this feasibility review**. Dataset admission and extraction
quality: **NOT_EVALUATED**. No dataset, annotations or model were imported.

## Decision and admission boundary

**None of the four dataset families assessed is verified as immediately eligible
to replace the missing internal independent Extraction Gold.** The closest
follow-up candidate is **ICDAR-2013, specifically its 2023 corrected release**:
it has explicit manual inspection/correction evidence, but original-document
rights remain unresolved. This is a conditional investigation priority, not
dataset admission. The other three offer useful automatic reference labels,
without verified independent human review of each released PDF-table annotation.

External human annotations can support a separately identified evaluation cohort;
they need not have been created inside DocLens. However, public availability,
publisher-authored markup, automatic consistency checks and a repository license
do not by themselves establish reviewed PDF Gold or rights to every source file.
No external benchmark supplies missing attestations for the internal five PDFs.
The previous ML-30C result remains unchanged: 20 proposed literals and 24 nulls,
with no justified recovery or independent qualification.

The local owners are [QG-00/QG-01 and coverage](../../DocLens_AI_Project_Goals_and_Quality_Policy-1.md#QUALITY-GATES),
[native PDF fidelity and genuine locators](../../DocLens_AI_Extraction_Strategy.md#EX-PDF),
and [Gold provenance/family isolation](../../DocLens_AI_ML_Quality_Strategy.md#ML-DATA).
They require rights/sensitivity, immutable source identity, reviewed labels,
family-safe splits and paired originals; table evaluation includes literal
anchors, order, cells/spans and relationships. Numeric acceptance thresholds
remain TBD. QG-00–03 remain NOT_EVALUATED, experiment INCONCLUSIVE and production
enrichment disabled. No schema, review contract or production behavior changes.

## Evidence method

Four established families were selected to contrast biomedical articles,
financial reports, recompiled scientific tables and manually annotated government
PDFs. Sources below are dataset authors' papers, official repositories/cards,
organizer documentation and license publishers. URLs were opened on the review
date; versioned papers are pinned below. Mutable cards describe what was observed
on that date, not a frozen dataset revision.

**Verified** below means the cited primary source explicitly documents a property.
It does not mean downloaded bytes, every label or sample correctness were checked.
**Unknown** means the inspected sources do not establish the required fact.
No dataset payload or source-document sample was downloaded; archive listings were
inspected only. No published model score is treated as a DocLens measurement.

## Annotation and source comparison

| Family | Original PDF availability | Geometry | Topology, text and relationships |
| --- | --- | --- | --- |
| **PubTables-1M** | Scientific source PDFs originate in PMC Open Access. Official distribution documents PDF-coordinate JSON annotations alongside rendered images; the listed archives are not a guarantee of bundled original PDFs. Exact source version/bytes must be reacquired and matched. [P1, P2] | Table, row, column and cell boxes, including blank cells; PDF and image coordinates. [P2] | Row/column membership, spanning cells, cell/word text, column headers and projected row headers. A full independently reviewed semantic header/value/unit relation graph is not established. [P1, P2] |
| **FinTabNet** (original; `.c` distinguished below) | Author paper uses financial-report PDFs and PDF/HTML matching. Present IBM URL redirects to DAX deprecation notice. Corrected-release listing offers annotation and structure archives; current access to exact original PDF pairs was not established. [F1–F3] | Table and nonblank text-cell boxes; full grid-cell/blank/row/column boxes differ from the original representation. [F1, A1 §3.1] | Cell content and logical row/column spans; adjacency can be derived. Original explicit header labels are absent according to the alignment paper; derived topology is not a verified semantic relationship graph. [F1, A1 §3.1] |
| **SciTSR** | PDFs are available by release documentation, but are **individual table snippets recompiled from arXiv LaTeX**, not original article pages with their original pagination/layout. [S1, S2] | Supplied text-chunk PDF coordinates are parser output. The documented structure JSON has logical positions, not independently annotated table/cell rectangles; chunk boxes must not be promoted to cell-box Gold. [S2] | Start/end rows/columns encode spans; TeX and space-split content are supplied. Horizontal/vertical chunk relations are automatically matched for training; structural adjacency is derivable. Reviewed header/value/unit semantics are not documented. [S2] |
| **ICDAR-2013** (original and corrected) | Organizer offers born-digital PDF excerpts with region/cell XML. Excerpts are not complete parent reports. Corrected archive is listed publicly; original download fetch failed in this review. Archive contents/byte pairing were not inspected. [I1–I4] | Region PDF boxes/page IDs and nonblank text-cell boxes; original format omits blank cells and does not define full grid-cell boxes. [I2] | Literal cell content and start/end row/column positions encode spans. Directed adjacency is an evaluation relation, not a complete semantic graph. Competition excludes functional analysis; practice data is a separate release with functional representation. [I2, I3] |

### Annotation origin and human-review evidence

- **PubTables-1M:** source XML/HTML is aligned with PDF characters; geometry is
  completed, headers inferred/canonicalized and tables filtered automatically.
  Quality checks even compare non-whitespace content and choose PDF-derived text
  where markup differs. These are meaningful engineering controls, but not
  independent human verification of exact PDF literals/spacing or every inferred
  cell/header. No per-item human review/adjudication evidence was established.
  Useful prospective automatic comparator; not admitted as human Gold. [P1 §3]
- **FinTabNet:** automatic PDF/HTML token matching creates the labels. The `.c`
  derivative makes automated corrections/canonicalization and excludes samples
  it cannot process/verify; it is not a human-reviewed relabeling of every table.
  Company-level validation/test separation is described by the original paper,
  but cross-dataset/internal family overlap remains unchecked. [F1 §3, F3]
- **SciTSR:** 15,000 table PDFs/labels derive from LaTeX parsing and compilation.
  The authors warn that parser-produced chunks and matched relations may contain
  noise. The construction and README do not establish an independent human
  review of each resulting PDF/structure pair. LaTeX authorship is not such a
  review. [S1 §4, S2]
- **ICDAR-2013 corrected:** the correction authors describe original expert
  annotations, inspection of all 256 starting table annotations, errors corrected
  in 18 tables, automated completion/canonicalization, and subsequent manual
  inspection/correction of each table. This is substantially stronger external
  human-review evidence. The same researchers also evaluated models; blinded
  multi-rater adjudication and per-cell reviewer records are not established.
  Their review does not prove error-free literals or resolve source rights. [A1
  §3, Table 1, §4.2; I4]

Published counts are not a locally verified manifest. A future evaluation must
name the precise release, table/region convention and attempted denominator.

## License, redistribution and privacy evidence

| Family | Verified license evidence | Unresolved restrictions / admission consequence |
| --- | --- | --- |
| PubTables-1M | Author-hosted data card declares **CDLA-Permissive-2.0** [P3]; project code has **MIT** [L2]. | These are different artifacts. PMC explicitly says licenses vary by article and not all PMC content permits reuse; use the authorized retrieval services and inspect each article license [P4]. Exact original/derivative rights and sensitivity must be recorded per selected pair. No blanket private-data clearance is established. |
| FinTabNet | `.c` author's card declares **CDLA-Permissive-2.0** and reports original FinTabNet as CDLA-Permissive, citing IBM [F3]. | Original IBM page now redirects [F2]; original license version/text and exact source-report scope were not reverified. The derivative declaration is evidence about `.c`, not proof of every company's underlying rights. No independent sensitivity/redaction audit was established. |
| SciTSR | Official repository **MIT** license covers software/documentation [S3]. | The inspected sources do not establish that this grant covers the separately hosted corpus or all arXiv-derived article/table material. Dataset redistribution/annotation rights and original article licenses remain unknown. A public download link supplies no missing permission. |
| ICDAR-2013 corrected | Card metadata declares **CDLA-Permissive-2.0**, while its body explicitly says the original dataset has no known license [I4]. Organizer says documents are expected to be public domain because they came from EU/US government websites [I3]. | That expectation and the derivative tag do not establish item-level rights. The code's Apache license mentioned in I4 is not a source-PDF license. Resolve originals, annotation permissions and redistribution scope before admission; neither a categorical ban nor blanket public-domain permission is established here. |

[CDLA-Permissive-2.0](https://cdla.dev/permissive-2-0/) permits use,
modification and sharing under its terms; shared data must include the agreement.
It provides no warranty of title or non-infringement. This review records evidence,
not a legal clearance. No additional dataset-specific privacy guarantee was
verified for any family. Public biomedical, company and government documents can
still require sensitivity/third-party-rights checks. No private DocLens text,
Gold, filenames or documents were submitted to search or external services.

## Coverage and suitability limits

The documented domains favor English scientific, financial and EU/US government
material. **No verified RU or KK table coverage or language-stratified annotation
quality was found** in the inspected sources; absence of evidence is not proof
that those languages never occur. EN suitability also needs sample-level checks.
None establishes representative RU/KK/EN or mixed-language DocLens coverage.

Paper tables, annual-report templates, government excerpts and recompiled snippets
are different families from the internal PDFs. Their results cannot be transferred
to internal documents, scans, mixed pages, rotation/font failures, corrupt files,
multi-page context or negative cases without evidence. All assessed sources are
PDF-table cohorts, not DOCX/XLSX, Retrieval Gold or Answer Gold. Even a useful
external table score leaves document text order, non-table anchors and genuine
full-document locators partly or wholly unevaluated.

Coordinate semantics also differ: text-enclosing boxes are not full cell extents;
blank-cell omissions are not negative labels. Canonicalized headers and spacing
conventions must remain explicit. Do not apply a benchmark's center/overlap rule
to weaken DocLens literal ownership checks, silently normalize numbers/whitespace,
invent missing semantic relations or turn parser-derived boxes into human labels.

All four benchmarks are publicly exposed. Check model training histories and
exact/near duplicates, translations and parent-document families before selecting
splits. A public test set cannot be renamed a fresh sealed independent test;
diagnostic/tuning samples must stay out of subsequent blind acceptance data.

## Smallest subsequent step — proposed, not executed

Prioritize a **three-pair ICDAR-2013 corrected source/annotation feasibility check**,
after resolving original and annotation rights. This is not a benchmark run.

1. Establish documentary permission/public-domain evidence for the selected PDFs
   and annotations, the precise corrected revision, and local evaluation/storage/
   redistribution scope. If unavailable, stop with admission NOT_EVALUATED.
2. Obtain only three individually accessible PDF excerpts plus their original and
   corrected annotations: a regular table, a spanning-cell table and a multi-level
   header table, preferably from different parent documents. Record the selection
   rule/IDs before parser inspection and every unavailable/failed selection. Use a
   proposed 10 MiB total retrieval cap; it is a task budget, not a quality threshold.
   The observed corrected distribution is a single 12.3 MB archive [I5]. Do not
   download the full archive to get three examples; obtain an authorized individual
   sample endpoint/package from the publisher or leave retrieval blocked. No such
   endpoint was verified here. Contact would require separate authorization.
3. Store in a fresh ignored external-only workspace; pin URL, release, SHA-256,
   size, source/page identity, article/report family, language, license and label
   origin. Preserve both annotation versions and all missing/unresolved labels.
4. Inspect the paired PDFs and annotations locally: exact literals (including
   signs, leading zeros and spaces), spans, blanks, page/CropBox/rotation and
   coordinate transform, text-box versus cell-box meaning, header/adjacency scope.
   Check label provenance, source binding and internal/family overlap. Codex may
   check structure and mismatches; it must not manufacture human attestations.
5. Deliver a three-record eligibility/discrepancy manifest with attempted,
   available, rights-resolved, supported, failed and needs-review counts. Admit
   only supported dimensions; retain unresolved semantic relations as unknown.
   If a human judgment is necessary and unavailable, that dimension stays blocked.
   Any later paired parser evaluation needs a separate protocol and frozen cohort;
   these three inspected samples are development/feasibility material.

## Primary source ledger and URL checks

All entries were opened successfully on 20 October 2026 unless an access limitation
is stated. Only papers, documentation, cards, licenses and file listings were read.

| ID | Source and inspected evidence |
| --- | --- |
| P1 | [Smock et al., PubTables-1M, arXiv:2110.00061v3](https://arxiv.org/html/2110.00061v3), §3 alignment/completion/canonicalization/quality controls. |
| P2 | [Official Microsoft repository](https://github.com/microsoft/table-transformer), PubTables-1M and distribution sections. |
| P3 | [Author-hosted PubTables-1M card](https://huggingface.co/datasets/bsmock/pubtables-1m/raw/main/README.md), data license and archive descriptions; linked by P2. |
| P4 | [NLM PMC Open Access terms](https://pmc.ncbi.nlm.nih.gov/tools/openftlist/), per-article licenses/retrieval limits. |
| F1 | [Zheng et al., GTE, arXiv:2005.00589v2](https://arxiv.org/pdf/2005.00589v2), §2.3/§3 dataset construction and company splits. |
| F2 | [Original IBM FinTabNet URL](https://developer.ibm.com/data/fintabnet/), redirects to [DAX deprecation notice](https://developer.ibm.com/exchanges/data/); dataset-specific terms unavailable there. |
| F3 | [FinTabNet.c creator's card](https://huggingface.co/datasets/bsmock/FinTabNet.c) and [file listing](https://huggingface.co/datasets/bsmock/FinTabNet.c/tree/main), automatic corrections/filtering, declared license and available archives. |
| S1 | [Chi et al., Complicated Table Structure Recognition, arXiv:1908.04729v1](https://arxiv.org/pdf/1908.04729v1), §4 construction from LaTeX. |
| S2 | [Official SciTSR README](https://raw.githubusercontent.com/Academic-Hammer/SciTSR/master/README.md), PDF/structure/chunk/relation schemas and noise warning. |
| S3 | [SciTSR repository license](https://raw.githubusercontent.com/Academic-Hammer/SciTSR/master/LICENSE), software/documentation MIT terms. |
| I1 | [Organizer competition page](https://tamirhassan.com/html/competition.html), definitive PDFs/excerpts and ground-truth release link. Linked original archive fetch failed in the research tool; no archive availability/content claim is made. |
| I2 | [Organizer dataset format](https://tamirhassan.com/html/competition/dataset-format.html), region/page/content/span schemas, box semantics, absent blanks and adjacency evaluation. |
| I3 | [Organizer dataset page](https://www.tamirhassan.com/html/dataset.html), source origins, expected public-domain status and practice/competition functional-label distinction. |
| I4 | [Corrected-release creator's card](https://huggingface.co/datasets/bsmock/ICDAR-2013-Table-Competition-Corrected), manual correction provenance and contradictory/unresolved upstream license evidence. |
| I5 | [Corrected-release file listing](https://huggingface.co/datasets/bsmock/ICDAR-2013-Table-Competition-Corrected/tree/main), archive-only listing and size; not downloaded. |
| A1 | [Smock et al., Aligning benchmark datasets, arXiv:2303.00716v2](https://arxiv.org/html/2303.00716v2), §3/Table 1/§4.2 human corrections versus automated inference, missing labels and denominators. |
| L1 | [CDLA-Permissive-2.0 license publisher](https://cdla.dev/permissive-2-0/), §§1–4 grants, sharing conditions and warranty limits. |
| L2 | [Microsoft project code license](https://raw.githubusercontent.com/microsoft/table-transformer/main/LICENSE), MIT; separate from data-card terms. |

## Local verification and preserved state

Starting/final scope checks: `git status --short`, `git diff --name-only`,
`git diff --check`, `git diff --cached --name-only`, full `git diff --cached`,
and `git diff --cached --check`. Only this report belongs in the commit.
Content checks found three valid local document links, 20 distinct external URLs,
no credential-pattern matches and no trailing whitespace. The external URL checks
are documented in the ledger; failed/redirected sources are explicitly qualified.

A standard-library SHA-256 check verified the existing 122-file protected snapshot
before writing. A fresh ignored `evaluation-output/ml31/protected-hashes.json`
captured **1,684 files** across `local-corpus`, `local-evaluation`, the frozen review
packet, both `ml29-human-review` and `ml30b-assisted-review`, plus the engineering
audit. Final inventory/hash comparison matched all 1,684 files. Internal RAW/Gold,
packet and resumable review workspaces were not modified.

No implementation edits, dataset/sample downloads, annotation generation, parser
scoring, tests, models, GPU, Docker, package downloads, benchmarks or full E2E
runs were performed. Tests/Ruff are inapplicable to this Markdown-only change;
source/rights inspection, content review, preservation hashes and Git checks are
the scoped verification. Remaining blockers concern subsequent dataset admission,
not completion of this evidence review.
