# QG-00 source-bound annotation eligibility and review handoff — 21 October 2026

**Engineering STATUS: PASS for this scoped handoff.** Starting HEAD
`3d64cfb92b15f667172589be61c9f696049f817b`, branch `main`.
Independent Gold, QG-00 and QG-01 quality remain **NOT_EVALUATED**.
Two candidates are admitted for new local development annotations; no reviewer
attestation, new Gold, model comparison or production authorization is created.

## Decisions and documentary basis

This revises the earlier blocked intake without changing its ledgers, frozen
manifests or Gold. A null annotation-use field did not establish absence of
permission. The [official OGL v3.0 grant](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/)
permits adaptation of information actually offered under that licence, subject to
attribution and exclusions. [GOV.UK terms](https://www.gov.uk/help/terms-conditions)
provide the publishing framework. Neither hosting nor a generic licence link alone
establishes permission for a particular attachment.

Each decision combines the exact official attachment link, publisher/context,
captured licence offer, fresh attachment bytes matching the historical acquisition,
and document inspection for exclusions, third-party notices and sensitivity.
Official pages, licence, terms and three PDFs returned HTTP 200; acquisition
receipts preserve exact URLs, UTC timestamps, byte counts and capture hashes.
Source acquisitions remain traceable through the frozen CSV rows and
[11 October acquisition protocol](corpus_v1_protocol.md).

| Candidate | Decision and precise scope | Publisher and source evidence |
| --- | --- | --- |
| c1-0033 | **ADMIT** new annotations of the institutional role/department table for local dev. Entire page inspected: no names, personal contact data, third-party notices or alternate rights statement identified. Scope excludes identifying people from roles or annotating personal information. | The Insolvency Service; [official source page](https://www.gov.uk/government/statistics/individual-insolvency-statistics-july-to-september-2020), exact attachment and OGL offer captured as `c1-0033-page` / `c1-0033-attachment`. |
| c1-0040 | **ADMIT** new annotations of the government-provided blank budget template for local dev. Entire page inspected: no populated applicant data, third-party credits or alternate rights statement identified. Scope excludes future completed applications. | British Embassy Tunis / Foreign & Commonwealth Office; [official source page](https://www.gov.uk/government/news/call-for-project-proposals-2016-2017-promoting-human-rights-in-tunisia), full-proposal template context and exact attachment. Frozen publisher `Unknown` is preserved; the verified publisher is recorded only in eligibility v2. |
| c1-0045 | **BLOCKED** specific reproduction/adaptation permission unresolved. Generic OGL footer does not resolve the publisher's restrictive policy; no sample exception was verified. | UK Hydrographic Office; [exact source page](https://www.gov.uk/government/publications/ukho-tidal-prediction-service-sample-pdf-format-seven), [linked format collection](https://www.gov.uk/government/collections/ukho-tidal-prediction-service-sample-formats), [publisher service policy](https://www.gov.uk/government/organisations/uk-hydrographic-office/about/about-our-services), [copyright/custodian policy](https://copyright.ukho.gov.uk/datasets.aspx). |

The two admissions use verified existing adaptation terms; no additional grant is
required for the recorded use. Their OGL attribution, publisher identification,
source links and licence link are retained in the private versioned record.
No separate third-party rights were identified in the admitted content. OGL
exclusions for personal data, unpublished information, non-integral logos/insignia,
third-party rights, other IP and identity documents remain applicable. New evidence
of an exclusion requires a new decision; this gate does not decide legal truth.
Non-endorsement and no-warranty terms remain applicable.

Permission to annotate the original source **does not authorize reuse of unrelated
third-party annotations**. All entries explicitly deny that inference. Existing
legacy assertions retain their original provenance, one historical reviewer per
candidate, and are isolated for later adjudication. Existing c1-0040 machine
sidecars remain automatic, unreviewed and outside the blank independent draft.
Documentary analysis by the agent is not a human reviewer attestation.

| Candidate | Original SHA-256 | Bytes / observed pages | Declared family |
| --- | --- | --- | --- |
| c1-0033 | `081c9cfcc8e885544698f617dfdb9bf351fcf60b512cc449a3620deb538695fd` | 29,702 / 1 | `f-de5a37738e823a8f44ec7b0f` |
| c1-0040 | `18a25155acbe6dfb0a97309097234dc3040a67d2f54250af82288e56dc8c4344` | 64,968 / 1 | `f-3ed94a499073bb2cc8254c6e` |
| c1-0045 | `04358ce617249f170d38ea302cbc96a35701987507e61fb87ea2be30da2cfddc` | 107,597 / 7 | `f-79488c502a03ed9f4a53cc97` |

**Pool 5; attempted 3; admitted 2; blocked 1; unavailable 0; excluded 2.**
c1-0048 and c1-0049 retain their outside-budget exclusions. The selected sources
have distinct declared source-page families; family completeness remains unreviewed.
All are publicly exposed legacy controls, **dev only**, never sealed-test Gold.

## Reused workflow and private evidence

[QG-00](../../DocLens_AI_Project_Goals_and_Quality_Policy-1.md#QUALITY-GATES),
[ML-DATA](../../DocLens_AI_ML_Quality_Strategy.md#ML-DATA), the
[data-quality skill](../../.agents/skills/doclens-data-quality/SKILL.md) and existing
[ML29](ml29_pdf_review_workbench.md)/[ML30](ml30a_visual_pdf_annotation.md) contracts apply.
The demonstrated gap was admission of an authorized subset: the existing builder
and workbench required all five historical PDFs. Optional `--eligibility` now
validates a source-bound decision revision before selecting originals. Full frozen
90-RAW / 19-record / five-PDF / 110-assertion / 19-region checks remain enforced.
Default historical behavior is preserved. This adds no parallel annotation UI.

The gate binds source bytes, pages, declared families, acquisition/evidence hashes,
licence offer, scope and complete selection denominator. Missing rights, unknown
third-party rights, exclusions, duplicate identities/JSON keys, drift and unsupported
claims fail closed. It validates explicit documentary decisions, not legal facts or
authenticated human signatures. The workbench binds the eligibility fingerprint on
resume and rechecks it before independent freeze; exposed controls require dev.
Review/export validation retains the existing independent-human requirements.

All following locations are **private, ignored and untracked**, relative to the repo:

- `evaluation-output/qg00-annotation-rights-20261021/eligibility-v2.json`: revision `qg00-annotation-eligibility-20261021-v2`; SHA `fbd71e522782e64a66d8e2a5d079f6a2d2e2af4873c05becd50ed5b484737c32`; normalized fingerprint `7aec430b7b41cc1e172ffe866d30f8520c8a02df0a281b61e752bb84e2e2274b`.
- Same directory: `acquisition.json`, `supplemental-acquisition.json`, original official captures, `document-inspections.json`, checked page renders, frozen acquisition copies and prior intake/report snapshots. OGL capture SHA `f5b2b9f2af63647cde889fa6c3508f5705925295b74912c68caa28dd37e64aa5`.
- `packet-1/` and `packet-2/`: **13 files each, byte-identical**, two original PDFs/two pages, blank independent sheets, separate faithful legacy assertions, unsigned adjudication and deterministic completion manifests. Packet fingerprint `15911fa7084d4a96c7951d1c9e9c55d0617921a634a7f5accd172b859fbf25bd`.
- `workspace/`: existing ML29 workflow, freshly initialized for this admitted revision and verified resumable. Both drafts unsigned/unsealed, no pages marked human-inspected, no tables/relations asserted, legacy locked. Blocked c1-0045 cannot be accessed in this workspace.
- `verification.json`, `protected-before.json`, `unsigned-validation.json`, `scopes.json`, `cli-review-validation/` and `cli-export-negative/`: reproducibility, preservation and expected negative export evidence.
- Historical `evaluation-output/qg00-review-handoff-20261021/run-{1,2}/intake.json`, old packets and `evaluation-output/ml29-human-review/` remain unchanged. Prior report is preserved as `prior-handoff-report.md`; earlier blocked reasoning is superseded only by the v2 decisions above.

No cell literal, span, semantic relationship, reviewer identity or approval was
fabricated. Blank drafts preserve unknown relationships and exact original page
identities; faithful legacy literals remain separate. Human structural/category,
family, language, source/cell and semantic review and adjudication remain pending.

## Executed verification

Commands run from the repository root (local venv; all task outputs ignored):

```powershell
$env:PYTHONPATH=(Get-Location).Path
$env:HF_HUB_OFFLINE='1'; $env:TRANSFORMERS_OFFLINE='1'
$env:ML30_NODE='C:/Users/nurs/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
$env:ML30_NODE_MODULES='C:/Users/nurs/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules'
.venv/Scripts/python.exe -B evaluation-output/qg00-annotation-rights-20261021/capture.py
.venv/Scripts/python.exe -B evaluation-output/qg00-annotation-rights-20261021/capture_extra.py
.venv/Scripts/python.exe -B evaluation-output/qg00-annotation-rights-20261021/decisions.py
.venv/Scripts/python.exe -B -m pytest tests/unit/test_pdf_review_eligibility.py tests/unit/test_pdf_table_review_packet.py tests/unit/test_pdf_review_workbench.py tests/unit/test_pdf_review_visual.py tests/unit/test_pdf_grid_proposals.py tests/unit/test_pdf_proposal_review.py tests/unit/test_ml28_review.py tests/unit/test_ml28_evidence.py tests/unit/test_corpus_v2.py -q --tb=short --strict-config --strict-markers -p no:cacheprovider --basetemp=evaluation-output/qg00-annotation-rights-20261021-tests-final --junitxml=evaluation-output/qg00-annotation-rights-20261021-tests-final.xml
# 276 passed, zero skipped/failed, 182.58s; local loopback/browser subprocess permission
.venv/Scripts/python.exe -B -m pytest tests/unit/test_pdf_review_eligibility.py tests/unit/test_pdf_table_review_packet.py tests/unit/test_ml28_review.py -q --tb=short --strict-config --strict-markers -p no:cacheprovider --basetemp=evaluation-output/qg00-annotation-rights-20261021-tests-code-final --junitxml=evaluation-output/qg00-annotation-rights-20261021-tests-code-final.xml
# Final-code affected-test rerun: 70 passed, zero skipped/failed, 34.09s.
foreach ($build in 1,2) {
  .venv/Scripts/python.exe -B -m tools.extraction_quality.pdf_table_review_packet --manifest docs/eda/corpus_v1_manifest.csv --corpus local-corpus --gold local-evaluation/extraction_fidelity_v1_expanded_approved.jsonl --eligibility evaluation-output/qg00-annotation-rights-20261021/eligibility-v2.json --output "evaluation-output/qg00-annotation-rights-20261021/packet-$build"
}
# Two individually executed commands; both preparation PASS. Existing destinations reject rebuilding.
.venv/Scripts/python.exe -B evaluation-output/qg00-annotation-rights-20261021/verify.py
# PASS: identical packets, resume, locked legacy, blocked source inaccessible;
# all 90 RAW identities and 1,750 protected existing files verified unchanged.
.venv/Scripts/python.exe -B -m tools.extraction_quality.pdf_review_validation --manifest docs/eda/corpus_v1_manifest.csv --corpus local-corpus --gold local-evaluation/extraction_fidelity_v1_expanded_approved.jsonl --review-dir evaluation-output/qg00-annotation-rights-20261021/packet-1/review --scopes evaluation-output/qg00-annotation-rights-20261021/scopes.json --revision qg00-review-pending-v2 --eligibility evaluation-output/qg00-annotation-rights-20261021/eligibility-v2.json --output evaluation-output/qg00-annotation-rights-20261021/cli-export-negative --export
# Expected BLOCKED, native exit 2, zero completed reviews, no Gold file.
.venv/Scripts/python.exe -m ruff check src tests tools alembic
git diff --check
git diff --cached --stat
git status --short
```

Tests include negative licence/adaptation and third-party rights, generic-link-only
offers, wrong SHA/size/page/family/source, missing originals/evidence/rights,
duplicates, concealed exclusions, sealed-test use, fabricated review/Gold status,
machine/synthetic/legacy promotion, unsupported geometry, deterministic builds,
resume and blinding. No real reviewer evidence was created. Initial test-authoring
runs exposed an exclusive-writer misuse and missing import in the new fixture;
these were corrected before the passing runs. Initial sandbox HTTP resolution was
unavailable; bounded official downloads succeeded with network permission.

No private RAW/Gold, images, body text or review payload enters Git or an external
service. External activity was GET-only retrieval of official public evidence.
Production parsers, indexing and API are unchanged. The pre-existing untracked
engineering audit is preserved and excluded from this commit.

## Remaining boundary and Git

The smallest unblock for **c1-0045** is a verified UKHO permission or explicit sample
exception covering this exact PDF/SHA and local annotation adaptation/reproduction,
including any underlying third-party rights. No contact was sent on the user's behalf.
The two admitted candidates can proceed to genuine independent human review through
ML29; reviewers must attest their own identity, independence, inspection and rights
reference. Missing attestations still block Gold. Coverage and quality are not PASS.

Resume command for the prepared workspace (documented, server not started here):

```powershell
.venv/Scripts/python.exe -B -m tools.extraction_quality.pdf_review_workbench --manifest docs/eda/corpus_v1_manifest.csv --corpus local-corpus --gold local-evaluation/extraction_fidelity_v1_expanded_approved.jsonl --packet evaluation-output/qg00-annotation-rights-20261021/packet-1 --output evaluation-output/qg00-annotation-rights-20261021/workspace --eligibility evaluation-output/qg00-annotation-rights-20261021/eligibility-v2.json --resume
```

Use the eligibility revision and its SHA as the documentary permission reference;
reviewers supply their own attestations. The record never fills those fields.
Report links/anchors, RAW filename exclusion, bounded credential/payload checks and
the pre-existing audit hash were verified locally; this is not a universal detector.

One focused Conventional Commit is authorized only after all scoped verification,
diff and staged-content checks pass. No push. Final SHA and exact status are returned
in the task completion message; the earlier unrelated audit remains untracked.
