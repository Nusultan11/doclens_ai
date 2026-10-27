# Extraction Native Baseline

EX-01 — 27 October 2026. **STATUS: PASS for this technical DEV execution.**
**Quality, semantic dimensions, QG-00 and QG-01: NOT_EVALUATED.**
This is an OFFLINE BASELINE of the current native implementation, not independent
Extraction Gold evaluation, parser promotion, Test acceptance or production qualification.

## Scope and source admission

Sources: root `AGENTS.md`, the extraction-benchmark skill,
[readiness v2](extraction_data_readiness_20261023_v2.md),
[Extraction Strategy](../../DocLens_AI_Extraction_Strategy.md),
[Quality Policy](../../DocLens_AI_Project_Goals_and_Quality_Policy-1.md) and
[ML experiment protocol](../../DocLens_AI_ML_Quality_Strategy.md#ML-EXPERIMENT).

The runner recursively verified the frozen release and parent artifacts using the
existing verifier and archived validation code. It rechecked rights receipts,
reserved QA and declared family components through `validate_continuation`.
All 217 registered originals passed SHA-256, size, format signature/package and
identity checks. The cohort came from the frozen effective matrix, using the
existing readiness scorer rule: `split == dev`, evaluation rights exactly `True`,
and `reserved_qa_family == False`. No filesystem discovery selected inputs.
Checks were repeated before each pass and after both passes.

| Population | Count |
| --- | ---: |
| Registered distinct identities | 217 |
| DEV | 215 |
| Sealed candidates, excluded | 2 |
| Reserved QA sources, excluded | 12 |
| Evaluation rights denied/unknown, excluded | 4 |
| Eligible DEV originals attempted per pass | 199 |

These exclusions are disjoint in this release. No sealed/QA payload was extracted.
Declared/source-native language labels were retained; unknown was not relabelled.

## Execution and preservation

Two sequential passes used `extract_file` through the existing native child worker
and `tools.extraction_campaign.run.run_one`. Native parsers, production runtime,
frozen releases, historical baselines and Gold were unchanged.
Each document used a fresh process, Windows job limits and default `ExtractionLimits`.
Budgets per document: 120 seconds wall, 90 seconds CPU, 2 GiB sampled worker-tree
RSS, 3 GiB OS commit, 256 MiB native JSON output and 512 MiB scratch.
The runner is sequential; no models, OCR, formula execution, downloads or cloud work.

All **398 complete `ExtractionResult` captures**, including failed native results,
remain in ignored local output with emitted schema version `1.1` and unchanged fields.
Text, blocks, tables/cells, spans, formulas, caches, actual locators, warnings and
errors were serialized by the existing worker and retained as emitted.
Missing structure was not inferred. Opaque document/family manifests, per-document
receipts, configuration/dependency/Git fingerprints and completion artifact hashes
are saved privately. The verifier rereads captures and reconstructs observations.
A crash/timeout/incomplete worker is accounted as a failed observation without
inventing an `ExtractionResult`; incomplete or changed evidence cannot earn PASS.

| Pass | Attempted | Success | Needs review | Failed | Full captures |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 199 | 90 | 101 | 8 | 199 |
| 2 | 199 | 90 | 101 | 8 | 199 |

No operational timeouts, worker crashes, output-limit, cleanup or resource-control
failures occurred. Native parser failures remain in all 199-document denominators.

### Format and language breakdown

The following status counts agree in both passes.

| Format | Attempted per pass | Success | Needs review | Failed |
| --- | ---: | ---: | ---: | ---: |
| docx | 71 | 15 | 55 | 1 |
| pdf | 51 | 47 | 4 | 0 |
| xlsx | 77 | 28 | 42 | 7 |

| Language label | Attempted per pass | Success | Needs review | Failed |
| --- | ---: | ---: | ---: | ---: |
| cy | 2 | 0 | 2 | 0 |
| en | 94 | 62 | 32 | 0 |
| kk | 18 | 4 | 12 | 2 |
| mixed | 7 | 0 | 6 | 1 |
| ru | 26 | 7 | 18 | 1 |
| unknown | 52 | 17 | 31 | 4 |

### Native errors and structural observations

| Error category | Documents per pass |
| --- | ---: |
| extraction_failed | 1 |
| limit_exceeded | 2 |
| unsupported_format | 5 |

Five XLSX returned `unsupported_format`, two XLSX returned `limit_exceeded`,
and one DOCX returned `extraction_failed`. No parser fix was attempted.
Code inspection: the XLSX parser explicitly rejects chart/dialog sheets;
the exception behind the generic DOCX category and exact limit triggers were
not independently diagnosed in this run.

| Emitted structure | Count per pass |
| --- | ---: |
| cell_locators | 510306 |
| formula_cached_value_null | 0 |
| formula_cells | 6893 |
| merged_ranges | 2641 |
| note_references | 21 |
| page_locators | 393 |
| sheets | 396 |
| spanned_table_cells | 1708 |
| spreadsheet_cells | 510306 |
| spreadsheet_tables | 23 |
| table_cells | 8225 |
| tables | 436 |
| text_blocks | 8226 |
| xml_locators | 8269 |

Counts describe emitted representation, not source completeness or fidelity.
`formula_cached_value_null` only counts nulls in emitted formula cells; it does
not establish raw-XML MISSING/EMPTY distinctions or correctness of cached values.
Page/XML/cell locator counts are populated fields, not reviewed locator accuracy.
No table or semantic relationships were reconstructed from PDF text.

| Warning code | Documents per pass | Emitted occurrence count per pass |
| --- | ---: | ---: |
| ambiguous_spreadsheet_structure | 5 | 5 |
| ancillary_provenance_unreviewed | 41 | 41 |
| drawings_not_extracted | 32 | 159 |
| footnote_provenance_unreviewed | 4 | 4 |
| formula_definition_unavailable | 9 | 3885 |
| insufficient_text | 4 | 7 |
| nested_tables_not_extracted | 5 | 11 |
| pdf_table_structure_not_preserved | 51 | 51 |
| spreadsheet_comments_not_extracted | 1 | 1 |
| spreadsheet_drawings_not_extracted | 35 | 47 |
| spreadsheet_error_value | 2 | 63 |
| text_boxes_not_extracted | 5 | 22 |
| unsupported_body_content_not_extracted | 45 | 653 |

Warnings retain their emitted severity and source locators in private captures.
Documents can have multiple warnings; occurrence totals are not quality scores.

## Runtime and memory

All 199 receipts per pass have measured runtime and RSS. P50/P95 use nearest-rank
quantiles across all attempted documents, including native failures.
Time includes fresh child startup, imports, environment/source checks, extraction,
serialization and cleanup; controller validation/aggregation is excluded.
RSS is sampled every 50 ms for the actual worker plus descendants after gating;
it excludes the venv launcher and controller and can miss brief peaks.
Windows commit limits are separate from measured RSS. OS caches were not reset.
This was a normal workstation, not an isolated performance experiment; focused
test execution overlapped early pass-1 documents. No speedup or SLO is claimed.

| Pass | P50 s | P95 s | Sum of document wall s | Peak RSS bytes | RSS P50 bytes | RSS P95 bytes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 3.032000 | 6.235000 | 672.112000 | 754634752 | 113999872 | 177631232 |
| 2 | 2.500000 | 4.375000 | 557.860000 | 754708480 | 113963008 | 179490816 |

| Pass / format | P50 s | P95 s | Peak RSS bytes |
| --- | ---: | ---: | ---: |
| 1 / docx | 3.015000 | 4.235000 | 171806720 |
| 1 / pdf | 3.062000 | 5.922000 | 126468096 |
| 1 / xlsx | 3.047000 | 7.468000 | 754634752 |
| 2 / docx | 2.453000 | 3.078000 | 170770432 |
| 2 / pdf | 2.703000 | 4.328000 | 125718528 |
| 2 / xlsx | 2.438000 | 5.859000 | 754708480 |

Hardware: AMD64, 8 physical / 16 logical CPUs, 16541597696 bytes RAM.
Platform: `Windows-11-10.0.26300-SP0`. Python: `3.12.3 (tags/v3.12.3:f6650f9, Apr  9 2024, 14:05:25) [MSC v.1938 64 bit (AMD64)]`.

## Reproducibility and fingerprints

All 199 identities, source SHA/size/format, admission metadata, statuses, warning/error
fields, capture schemas, full JSON content hashes, structural hashes and raw capture
byte hashes agree across passes. **Zero mismatches.** Runtime/RSS and process receipts
are preserved separately and excluded from deterministic comparison.

- Git HEAD: `fa2ae49f2ba53386b0ba54d1585d585cc3e4e934` on `main`, with existing local changes recorded.
- Readiness release: `f480f4fad5b46eaf037b67d7ca77db2e37f93f1aa0172405fd7f493d44489b55`.
- Configuration fingerprint: `680f07ba9f6e37c4c53efaf26bf2a9803ea7922ef43ba78cc4fe2c1a932bb2ea`.
- Registered opaque manifest fingerprint: `5a404daca01639cd7d0710283ad321f19c9204f1c5a2e2affea8c0efba9da061`.
- Completed evidence fingerprint: `a1ea7e53acedb2bfc1dde7e6db434ffb8dc02b20b2fb71c2631dde53155d3dab`.
- Native parser code SHA-256: `71e159b36debeaa6b30b5a4d8caa429b388a71b3b5e02cd438e94004526c03c0`.

All installed distribution versions, executable hash, relevant code hashes, native
defaults, Git diff fingerprint and resource configuration are in the private protocol.
Native dependency versions: `pypdf==6.20.0`, `python-docx==1.2.0`, `openpyxl==3.1.5`, `lxml==6.1.3`, `pydantic==2.14.0`, `psutil==7.1.0`.

## Verification

Executed from repository root (output locations below contain no source names):

```powershell
.venv/Scripts/python.exe -X utf8 -m tools.extraction_quality.readiness_release verify --output evaluation-output/extraction-readiness-continuation-20261023-v2
.venv/Scripts/python.exe -X utf8 -m tools.extraction_quality.native_dev_baseline run --output evaluation-output/extraction-native-dev-baseline-20261027/run-1
.venv/Scripts/python.exe -X utf8 -m tools.extraction_quality.native_dev_baseline verify --output evaluation-output/extraction-native-dev-baseline-20261027/run-1
.venv/Scripts/python.exe -m pytest tests/unit/test_native_dev_baseline.py -q --basetemp evaluation-output/ex01-tests-completion --junitxml evaluation-output/ex01-tests-completion.xml
.venv/Scripts/python.exe -m pytest tests/unit/test_native_dev_baseline.py tests/unit/test_readiness_release.py tests/unit/test_readiness_partitions.py tests/unit/test_extraction.py tests/unit/test_extraction_v2.py -q --basetemp evaluation-output/ex01-tests-final --junitxml evaluation-output/ex01-tests-final.xml
.venv/Scripts/ruff.exe check tools/extraction_quality/native_dev_baseline.py tests/unit/test_native_dev_baseline.py
.venv/Scripts/ruff.exe format --check tools/extraction_quality/native_dev_baseline.py tests/unit/test_native_dev_baseline.py
git diff --check
git diff --cached --check
git status --short
```

Results: readiness integrity PASS; both real passes and standalone saved-evidence
verification PASS; focused tests **30 passed**; final related tests **109 passed,
1 skipped**; Ruff check/format and diff checks passed. The skip requires Windows
symlink privilege. Tests cover admission, TEST/QA/rights exclusion, missing/modified
originals, incomplete outputs, failure denominators, private destinations, complete
artifact verification, tampering and deterministic comparison; genuine child probes
exercise crash, timeout, output and commit-memory failure handling.
Initial Ruff violations were fixed. An initial repeat of resource-probe tests had
four failures from reused test destinations; unique private probe directories fixed
that test defect. The corrected preflight had 105 passed / 1 skipped, and subsequent
focused and final suites passed. No failed corpus pass was discarded or replaced.

The run and standalone verify commands both exited 0 and returned:

```json
{"accounted_per_pass":[199,199],"attempted_per_pass":[199,199],"execution":"PASS","fingerprint":"a1ea7e53acedb2bfc1dde7e6db434ffb8dc02b20b2fb71c2631dde53155d3dab","quality":"NOT_EVALUATED","reproducibility":{"compared":199,"configuration_agrees":true,"mismatches":{},"reproducible":true}}
```

Additional `git diff --no-index --check -- NUL <file>` checks covered each of the
three untracked task files. They exited 0 with only Git's LF-to-CRLF notices.
The report privacy check found zero registered-original filenames and 101 opaque
family rows. Local reporting preparation required an import-path correction;
it did not change or rerun the completed extraction evidence.

## Remaining boundaries and Git

Native errors and warnings are observed baseline limitations. Independent semantic
quality, source completeness, reading order, table relationships, locator accuracy,
display values, OCR CER/WER and release acceptance are NOT_EVALUATED.
Frozen family isolation covers declared/exact/normalized/template/translation links;
unreviewed cross-family semantic completeness remains unproved, as in readiness v2.
Runtime service/tenant ACL, retry/delete/reindex and production gates were outside this
standalone extraction task. No parser, production, Gold or frozen-input changes.
**COMMIT: Not created; review required.** Only runner, focused tests and this report
were added as public task files; pre-existing unrelated changes were preserved.

## Family breakdown

101 declared eligible families. Every family below has identical attempted and
status counts in both passes; each failed/needs-review document remains included.
Family IDs are opaque hashes, not source names. Family-size distribution:
61 single-document families; 20 with two documents; 12 with three; one with four;
three with five; and one each with six, eight, nine and twenty documents.

| Opaque family | Attempted per pass | Success | Needs review | Failed |
| --- | ---: | ---: | ---: | ---: |
| nf-07501e518208b29dc93b085d | 3 | 2 | 0 | 1 |
| nf-092547f10fa355858ace7e43 | 1 | 1 | 0 | 0 |
| nf-0b8e6e36c80870d8a0694655 | 1 | 1 | 0 | 0 |
| nf-0f14ed13501854325c4d7705 | 1 | 1 | 0 | 0 |
| nf-129e1d0fc5838dedc75a2b60 | 3 | 2 | 1 | 0 |
| nf-12ae30ad435a2f6f42040250 | 1 | 1 | 0 | 0 |
| nf-12d560d58f02e9f37f8aa2aa | 3 | 3 | 0 | 0 |
| nf-13ea1d3cfecedf8fe1bdcc7c | 1 | 1 | 0 | 0 |
| nf-168ce97048662c8e400fcffd | 1 | 1 | 0 | 0 |
| nf-1b5df6681040b67b822fce54 | 3 | 0 | 3 | 0 |
| nf-1b8f3b2cbf2984baea860e57 | 1 | 0 | 1 | 0 |
| nf-1da5b12269c915a4d7a29d7b | 1 | 0 | 1 | 0 |
| nf-1df0d2e2392cbc7cfe8e49b9 | 1 | 1 | 0 | 0 |
| nf-26d42e345130e73d02c9dc48 | 1 | 0 | 1 | 0 |
| nf-2849967108c83b9b1fa02c3a | 1 | 1 | 0 | 0 |
| nf-2977b65c27213c5306ef6db8 | 1 | 1 | 0 | 0 |
| nf-2a9f9ab8982928ccece5741d | 1 | 1 | 0 | 0 |
| nf-2cea53b3fc25c5ac3e8b26a1 | 4 | 0 | 4 | 0 |
| nf-2f8b36634cce4d3f92010740 | 1 | 1 | 0 | 0 |
| nf-30470485582bed7ac2e6444b | 2 | 0 | 1 | 1 |
| nf-30f6b40aa9887bcda9230fb6 | 1 | 0 | 1 | 0 |
| nf-33befc404aa733eac0353a47 | 2 | 0 | 2 | 0 |
| nf-3653cdabb38e7e72a1b2e0b2 | 2 | 0 | 2 | 0 |
| nf-36cd2b939d178f158f24fb3b | 3 | 0 | 3 | 0 |
| nf-36f695142170b80ae3964d04 | 1 | 1 | 0 | 0 |
| nf-3d2f8df7279bca565319343c | 2 | 2 | 0 | 0 |
| nf-3f54541a61f0904daed94817 | 1 | 1 | 0 | 0 |
| nf-433703b5df86f8b88dc1b78f | 1 | 1 | 0 | 0 |
| nf-4377e16a86f5027526557057 | 1 | 0 | 0 | 1 |
| nf-455b3d68234f59007a8785f0 | 1 | 1 | 0 | 0 |
| nf-489ffdeca08ca05f6e8ebb98 | 1 | 0 | 1 | 0 |
| nf-493edcb5266b19d010177eec | 1 | 1 | 0 | 0 |
| nf-4bf324b3ec21314232effea0 | 9 | 1 | 7 | 1 |
| nf-4e2a4fdf5d8e766e56f47f17 | 1 | 1 | 0 | 0 |
| nf-502e0f629496b83187b8abef | 2 | 1 | 1 | 0 |
| nf-50c30dd4c181f43b12fe9770 | 3 | 2 | 1 | 0 |
| nf-599e606679fc9c10fcde1499 | 3 | 0 | 3 | 0 |
| nf-5f19a204fcf8b761be43aae0 | 1 | 0 | 1 | 0 |
| nf-6025a9da6f0393267b58ed13 | 5 | 3 | 2 | 0 |
| nf-60caba2ec3329e8c70f3ef92 | 2 | 1 | 1 | 0 |
| nf-61f0cb8e5b34ba1c0cc893db | 1 | 1 | 0 | 0 |
| nf-652ced3a3240b5b1d70a2db1 | 2 | 0 | 1 | 1 |
| nf-687ad5ac613af1e30c854410 | 3 | 0 | 1 | 2 |
| nf-6a3efd1616cc68f32b2f92a5 | 1 | 1 | 0 | 0 |
| nf-6d3a5c4eacbe765fec15a55a | 2 | 0 | 2 | 0 |
| nf-6e5b6c89d87788da61dd398a | 5 | 0 | 5 | 0 |
| nf-6eab013e59cfafac14a32fcd | 1 | 0 | 1 | 0 |
| nf-7381a21a1406363c065c1e43 | 3 | 3 | 0 | 0 |
| nf-766555327d180584f0add3d9 | 2 | 1 | 1 | 0 |
| nf-7c4521e901efd48557d8a610 | 1 | 0 | 1 | 0 |
| nf-7c5deba28a204f047660b66f | 1 | 0 | 1 | 0 |
| nf-7ea0eec392facb7574df0f11 | 1 | 1 | 0 | 0 |
| nf-81e53c6de9f40e57ef3fb3a1 | 1 | 0 | 1 | 0 |
| nf-86304d3ed06a2f4e96220c14 | 3 | 0 | 3 | 0 |
| nf-8c52950922f33aff32a9ba0d | 1 | 1 | 0 | 0 |
| nf-94e88436db8c027ffdcbc9c7 | 1 | 1 | 0 | 0 |
| nf-9557f6ab77235283a8f41a0a | 5 | 0 | 5 | 0 |
| nf-9988fb55c2d8d130f41827b2 | 1 | 0 | 1 | 0 |
| nf-9a2d729b5632d4106141b0ac | 8 | 4 | 4 | 0 |
| nf-9b980d249ec3557a66d01ab2 | 1 | 1 | 0 | 0 |
| nf-9dc8c3bdba18ceb7cbe9e4be | 1 | 0 | 1 | 0 |
| nf-a135d9d245dfde976bfc6ae3 | 2 | 0 | 2 | 0 |
| nf-a720aeb00a3d80ea5db64300 | 1 | 1 | 0 | 0 |
| nf-aa3b915add3d3e9d964c0464 | 1 | 0 | 1 | 0 |
| nf-aa5dd1da1b03f54d7ea7a714 | 1 | 1 | 0 | 0 |
| nf-afb2e6fe7942afa16f1cc580 | 2 | 1 | 1 | 0 |
| nf-b2565e686558de1617973e0f | 1 | 1 | 0 | 0 |
| nf-b272dcc3aa66d10359561854 | 1 | 1 | 0 | 0 |
| nf-b38fa4c5affa3296f1517a81 | 1 | 1 | 0 | 0 |
| nf-b6a20526932024f5d52489c8 | 20 | 7 | 13 | 0 |
| nf-b8e3ae6b1ed61b0fc681dfb7 | 1 | 1 | 0 | 0 |
| nf-be41c0d660d47ed13380a893 | 1 | 1 | 0 | 0 |
| nf-bf3987b10084dc365425798c | 1 | 1 | 0 | 0 |
| nf-c11c18343ea0234bcf38e269 | 2 | 0 | 2 | 0 |
| nf-c469223e679f731870afb64f | 1 | 0 | 1 | 0 |
| nf-c8cbb44623b007dcd047d3c5 | 3 | 0 | 3 | 0 |
| nf-cc0608c01f8cdea2e9dadd03 | 1 | 1 | 0 | 0 |
| nf-cff8239667263abe8287d20f | 2 | 1 | 0 | 1 |
| nf-d2c5b5969a765ec1932a60ac | 2 | 2 | 0 | 0 |
| nf-d32dcd506a7919f52f5e1738 | 1 | 1 | 0 | 0 |
| nf-d35290001e650db1c1fcb562 | 1 | 0 | 1 | 0 |
| nf-d57570b12697b831635fe90f | 1 | 0 | 1 | 0 |
| nf-d602aba11d9f26440e21f770 | 2 | 2 | 0 | 0 |
| nf-da64d2527ce11bae2b892851 | 2 | 1 | 1 | 0 |
| nf-dabd17e94b263cfcc5fa757e | 1 | 1 | 0 | 0 |
| nf-e04a9c386aebdfc6b5ae79d7 | 1 | 0 | 1 | 0 |
| nf-e1d64d2abe8c252545247dcd | 1 | 1 | 0 | 0 |
| nf-e3c3e11e97889827a6f71f05 | 1 | 0 | 1 | 0 |
| nf-e509113e95513fd9d040fba4 | 1 | 1 | 0 | 0 |
| nf-e529d764b7c2f1b5463e0929 | 3 | 1 | 2 | 0 |
| nf-e7826cf93626664715cfe730 | 1 | 1 | 0 | 0 |
| nf-e9b6efa6646ba4c44d2b7d2e | 1 | 0 | 1 | 0 |
| nf-eaf98aa57949f57f7bfc1a8e | 2 | 0 | 2 | 0 |
| nf-eb2e093b7633a269bbef5330 | 1 | 1 | 0 | 0 |
| nf-f14a8cd7ba267df96d9fa8bd | 2 | 1 | 1 | 0 |
| nf-f698ed0df23ff0016fcf8bf2 | 1 | 1 | 0 | 0 |
| nf-fc83e91818c51f7845d80673 | 2 | 2 | 0 | 0 |
| nf-fd01ccb8488facf8ccfbd318 | 1 | 1 | 0 | 0 |
| nf-fd303975a977ed2b2a71d191 | 6 | 6 | 0 | 0 |
| nf-fda2bce65412991a1e3b4217 | 2 | 0 | 2 | 0 |
| nf-fe878246d75a3a16854fbcb4 | 1 | 1 | 0 | 0 |
