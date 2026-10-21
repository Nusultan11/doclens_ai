# ICDAR-2013 corrected — bounded source-pair qualification

21 October 2026. **Engineering execution: PASS** for this bounded qualification and
verification step. **Source-pair qualification: BLOCKED. Gold readiness and QG-00:
NOT_EVALUATED. Production release: NOT AUTHORIZED.** The dependency is not resolved:
zero source-bound pairs were admitted. No parser/model experiment, training,
annotation correction, independent human review, staging or commit was performed.

Started on `main`, HEAD `b816531e292739bb7f7a12a2ad25f18ae49464c6`; the only existing
worktree item was `docs/eda/independent_engineering_audit_20261020.md`, left untouched.
Requirements: root AGENTS/source map, `doclens-data-quality`,
[ML-31](ml31_external_table_gold_feasibility.md),
[QG-00](../../DocLens_AI_Project_Goals_and_Quality_Policy-1.md#QUALITY-GATES), and
[ML-DATA](../../DocLens_AI_ML_Quality_Strategy.md#ML-DATA).

## Result and denominators

The [separate v2 extension manifest](icdar2013_v2_extension_manifest.json) validates
against the unchanged Corpus v2 model/schema. It has three **desired coverage
slots**, not invented sample records: regular, spanning cells, multilevel headers.
Each target allows zero or one table, with explicit blockers; `samples` is empty.
The [qualification ledger](icdar2013_qualification.json) records exact source URLs,
revisions, metadata hashes, declared archive hashes/sizes and unknown permissions.
Original and annotation payload SHA/page/family/geometry fields remain null when
no pair was obtained. Targets are not proof that those categories were found.

| Denominator | Count |
| --- | ---: |
| Desired coverage slots | 3 |
| Identified source-bound pair IDs | 0 |
| Individual PDF/annotation payload requests attempted | 0 |
| Available / rights-resolved / admitted pairs | 0 / 0 / 0 |
| Pairs failed after download | 0 |
| Coverage slots blocked before payload acquisition | 3 |
| Direct bounded metadata GET / archive HEAD requests | 17 / 3 |
| Direct HTTP 200 responses / transport failures | 20 / 0 |
| Real pair geometry / literal checks | 0 / 0 |
| New independent human attestations / verified semantic relations | 0 / 0 |

Acquisition was investigated through the actual publisher file trees, organizer
links and HEAD probes. No qualified individual endpoints or source IDs were found
in those inspected listings. Consequently no artificial three-document attempted
denominator is reported. The three slots remain blocked, rather than being counted
as failed PDF downloads or replaced with unchecked archive examples.

## Authoritative identity and release distinction

The [organizer's competition page](https://tamirhassan.com/html/competition.html)
names Max Goebel, Tamir Hassan, Ermelinda Oro and Giorgio Orsi. Its 2013-11-23 update
links the ground-truthed archive; the server currently reports Last-Modified
2013-11-25. The definitive originals are PDF excerpts, not the included convenience
text conversion. These excerpts do not establish full parent-report identities.

The correcting authors are Brandon Smock, Rohith Pesala and Robin Abraham, documented
in [arXiv:2303.00716v2](https://arxiv.org/html/2303.00716v2). Their paper describes
expert source annotations, manual correction and later automatic alignment; this
is publisher-level provenance, not new DocLens or per-cell independent attestation.

| Distribution | Exact identity | Inspection |
| --- | --- | --- |
| Original ground-truthed organizer release | `https://tamirhassan.com/html/files/icdar2013-competition-dataset-with-gt.zip`; 5,632,009 bytes; HEAD 200 | No body/hash obtained; ETag is not SHA-256 |
| 2023 manual-corrected competition release | `bsmock/ICDAR-2013-Table-Competition-Corrected`, revision `bdb9585690d261e568fd86e3db78df5f24fbf3ae` | Pinned API/card/tree; one 12,340,973-byte `.tar.gz`; HEAD 200 |
| Separately aligned/canonicalized release | `bsmock/ICDAR-2013.c`, revision `e36de0d7a9a4e9673dc8fab7e5f01ee170f93ef9` | Pinned API/card/tree; PDF-annotation archive 1,158,109 bytes and structure archive 8,283,024 bytes |

The two corrected distributions are not interchangeable. The manual-corrected
[pinned card](https://huggingface.co/datasets/bsmock/ICDAR-2013-Table-Competition-Corrected/raw/bdb9585690d261e568fd86e3db78df5f24fbf3ae/README.md)
describes 2023 manual corrections. The separate
[aligned card](https://huggingface.co/datasets/bsmock/ICDAR-2013.c/raw/e36de0d7a9a4e9673dc8fab7e5f01ee170f93ef9/README.md)
also describes automatic canonicalization. Neither pinned tree exposes individual
PDF/XML/JSON table records. The aligned extraction instructions were read as text,
not executed. Archive member contents, matching PDF bytes and original/corrected
annotation differences were not inspected or inferred from archive names.

Publisher metadata declares the manual-corrected archive SHA-256 as
`fbea3d39d186256c56cca5640c197af458d06e1f73210adb78526b92068c193a`.
This is an **unverified publisher LFS declaration**, not a locally computed payload
hash. Equivalent declarations for the aligned archives are retained in the ledger;
`retrieved_sha256` stays null. Metadata bodies/cards have locally computed hashes.

## Rights and individual-access decision

The corrected and aligned card metadata declare CDLA-Permissive-2.0. Their bodies
also state that the original dataset has no known license and offer an inference
from its public availability. That inference is not adopted as permission. Both
the [historical organizer dataset page](https://www.tamirhassan.com/html/dataset.html)
and the [current organizer page](https://roundtrippdf.com/data-extraction/pdf-table-recognition-dataset/)
express an expectation of public-domain status based on EU/US government sources;
they do not establish selected PDF/third-party or upstream annotation rights.
The described Apache-2.0 code license is a separate scope. Paper publication and
public download access likewise do not supply an item-level grant.

Thus original-PDF rights, upstream annotation scope, local evaluation permission,
redistribution and per-item sensitivity remain unresolved. No categorical legal
ban is inferred. No data or human-review permission was invented.

Current access differs from the historical ML-31 observation: the original archive
now answers HEAD 200, rather than being asserted currently unavailable/403.
The legacy `/en/` dataset/download links redirect to the About root. The current
site's actual Downloads menu `https://roundtrippdf.com/?page_id=62` also redirects
there. Current non-`/en/` dataset/competition/format pages were inspected separately;
they did not establish qualified individual pair endpoints. This is a bounded
negative finding, not proof that no endpoint exists anywhere.

The manual-corrected archive exceeds the 10 MiB cap by itself. The original and
aligned annotation archives can individually fit, but downloading a whole archive
solely to select three examples is prohibited by this task, so none was fetched.
Accept-Ranges headers do not establish an authorized individual pair or its rights;
no compressed archive prefix, partial pair or guessed member URL was substituted.
No organizer contact/message was sent.

## Geometry, literals, topology and family boundaries

The [organizer format](https://tamirhassan.com/html/competition/dataset-format.html)
and obtained structure XSD version 1.0 document 1-based excerpt pages, zero-based
row/column positions and optional inclusive end-row/end-column spans. Original
bounding boxes enclose text rather than a verified full cell grid. Blank cells
are omitted. PDF coordinates are documented, but no unobtained page's origin,
MediaBox/CropBox or rotation mapping is fabricated. Organizer adjacency scoring
normalizes content; that is not evidence of exact signs, zeros or spacing.
Competition functional analysis is absent: header/value/unit/period relations
remain unknown. These are documented format capabilities, not measured samples.

The frozen v2 schema has no ICDAR XML annotation kind. It was neither extended
nor bypassed by labelling ICDAR data as PubTables/DocLayNet. With no eligible pair,
the separate manifest legitimately remains empty; no parser/adapter was introduced
for inaccessible payloads. Real pair geometry, literals, cell/span correctness,
parent-document identity and cross-corpus family overlap are NOT_EVALUATED.
No sample type or distinct-family coverage is claimed.

Any subsequently eligible metadata would use frozen `selected_ids` SHA ranking
with seed `icdar2013-3pair-20261021`, one per documented category and a preference
for distinct verified families. The eligible population and selected IDs are zero
now. This exposed feasibility cohort is development-only, never a fresh sealed
test. Unknown family/review/semantic fields stay unknown. Labels are not rewritten.

## Retrieval accounting and immutable evidence

The direct HTTP helper enforced a shared **10,485,760-byte** response-body budget,
256 KiB metadata caps (16 KiB for the extraction-instruction text), identity content
encoding and 20-second per-request timeouts. Archive URLs were HEAD-only. Total
direct bodies read: **303,546 bytes**, all public metadata; **10,182,214 bytes**
remain. Acquired PDF/table-annotation/archive payload bytes: **zero**.
This is body-read accounting, not a measurement of protocol overhead or search
service transport. Web search/navigation was discovery; its reader rejected the
two organizer ZIP links and XSD MIME type, so it supplied no source-pair payload
or checksums. The Hugging Face connector was UNAVAILABLE; bounded HTTP was used.

Raw metadata, HTTP headers (including temporary CDN redirects), ledgers and
validation outputs remain ignored under
`evaluation-output/icdar2013-qualification-20261021/`. The sanitized ledger exports
origin/pinned URLs and selected non-sensitive headers, not temporary signed CDN
query strings, raw documents, literals or unpublished annotations. No raw archive,
original PDF, model or Gold file is included in the scoped change.

All **130 protected files** were unchanged: the prior 111 original/Gold/review/audit
snapshot plus the 19 committed Extraction v2 files. Existing frozen schema,
manifest, Gold, production code and instructions remain unchanged.

| Deterministic identity | Fingerprint |
| --- | --- |
| Extension manifest canonical | 3e36ff3df45ec2071a0e25a8c8fb515a6bed54bebf58432a04b626e911a3f1db |
| Qualification ledger, excluding its own fingerprint | 373dd60c718399f71ad6ed821ab185a605524cec1b791acdb4bd5f40e98c1610 |
| Validation output, both identical runs | 2e296ab3e11e128702898c1372f844c0c2f733396908d014f3687e8afc58358c |

The ledger also binds the extension's actual byte SHA and frozen base SHA values.
Canonical fingerprints use the existing `fidelity_gold.fingerprint` implementation.

## Executed commands and verification

Commands run from the repository root with the existing `.venv`:

```powershell
.venv/Scripts/python.exe evaluation-output/icdar2013-qualification-20261021/fetch_metadata.py
# Initial 11 GET/HEAD metadata probes; subsequent bounded helper calls followed
# organizer-disclosed current links and pinned releases. Full 20-event URLs,
# methods, statuses, byte counts and hashes are in icdar2013_qualification.json.
.venv/Scripts/python.exe evaluation-output/icdar2013-qualification-20261021/build_qualification.py
# PASS: strict empty v2 extension; 3 blocked slots, no admitted pairs
.venv/Scripts/python.exe evaluation-output/icdar2013-qualification-20261021/validate_qualification.py --output evaluation-output/icdar2013-qualification-20261021/validation-1.json
.venv/Scripts/python.exe evaluation-output/icdar2013-qualification-20261021/validate_qualification.py --output evaluation-output/icdar2013-qualification-20261021/validation-2.json
# Both PASS for engineering; outputs identical; pair qualification BLOCKED
.venv/Scripts/python.exe -m pytest tests/unit/test_corpus_v2.py tests/unit/test_dataset_adapters_v2.py -q --strict-config --strict-markers -p no:cacheprovider --basetemp=evaluation-output/icdar2013-qualification-20261021/tests --junitxml=evaluation-output/icdar2013-qualification-20261021/tests.xml
# 57 passed in 2.22s; no skips/deselections
.venv/Scripts/python.exe -m ruff check src tests tools alembic
# All checks passed
```

The manifest/rights/geometry negative regressions include malformed paths/JSON,
missing/changed hashes/assets, unknown rights/sensitivity, false review/coordinate
bases, duplicate source identities, family/translation/exact/near split leakage,
wrong original/annotation/PNG pairing, rotated/nonzero-origin/cropped geometry,
invalid publisher boxes/pages/dimensions and synthetic-versus-human-Gold separation.
They are existing synthetic validator tests, **not real ICDAR quality evidence**.
No implementation file changed, so a new full portable suite/service/GPU run was
not needed or performed. Prior Extraction v2 benchmarks were not rerun.

The two local read-only qualification validations recomputed all metadata bytes,
release IDs/cards/tree declarations, the budget and event denominator, extension
schema/base pins, null rights/sample fields and protected-file hashes. Thus PASS
means correctly completed bounded investigation, not data eligibility.

## Scoped changes, remaining blockers and stop boundary

Only three new sanitized files belong to this task:

- `docs/eda/icdar2013_v2_extension_manifest.json`: unchanged-schema extension with
  explicit blocked coverage targets and zero sample records.
- `docs/eda/icdar2013_qualification.json`: source/rights/access ledger, release
  identities, exact request outcomes, accounting and fingerprints.
- `docs/eda/icdar2013_eligibility_report.md`: this decision and executed verification.

`git diff --stat` and staged diff are empty because the three additions remain
untracked. `git diff --check` / `git diff --cached --check` complete with no errors.
No files were staged or committed. Final exact status:

```text
?? docs/eda/icdar2013_eligibility_report.md
?? docs/eda/icdar2013_qualification.json
?? docs/eda/icdar2013_v2_extension_manifest.json
?? docs/eda/independent_engineering_audit_20261020.md
```

To unblock admission requires a publisher-authorized bounded individual source/
annotation endpoint/package, exact matching original and corrected labels, and
documentary original/annotation usage rights. Only then can real page geometry,
literal fidelity, spans/headers and family relationships be inspected and an
appropriate separate ICDAR annotation contract qualified. Unknown independent
attestations and semantic relationships stay unknown. No subsequent stage or
experiment has been started.
