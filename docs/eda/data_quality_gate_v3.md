# Data Quality & Gold Readiness Gate v3

## Decision and scope

**PASS: frozen inputs are structurally ready for the next narrowly scoped paired PDF
extraction benchmark.** This is not production-ingestion approval, a parser improvement,
independent human re-review, whole-corpus fidelity, or retrieval-quality certification.
Both actual local runs passed; neither had integrity findings or missing inputs.

Baseline checkout: `b34cd6976d17df3ad28f8f103ac2eb0155372984`.
Only a new offline CLI, synthetic regression tests and this sanitized report are added.
Existing validators, parser, chunking, indexing, retrieval, Gold and originals are unchanged.
No new dependencies, services, models, training or tuning were used.

The data-quality workflow determined explicit grain, complete denominators, reference-integrity
checks and separate automatic/human assertions. Extraction-benchmark instructions determined
frozen identity checks, unchanged labels and conservative interpretation. The explicitly requested
CLI/Markdown artifacts replace the general analytics skill's optional notebook/visual surfaces;
no additional notebook, dashboard or publication is in scope.

## Reproducible audit contract

Run `python -m doclens_ai.eda.data_quality_gate` from the repository root in the existing
development environment with extraction dependencies. Defaults select the frozen corpus manifest,
local corpus, approved combined eleven-document Extraction Gold and reviewed Retrieval Gold.
There is no CLI synthetic opt-in or alternate-contract bypass. Unit fixtures are explicitly
synthetic, use a separate programmatic test contract and never establish real-corpus readiness.

The CLI reuses:

- `fidelity_eval._read_sources` and `verify_corpus` for manifest/source integrity;
- `fidelity_gold.load_gold` and `evaluation.gold.load_gold_jsonl` for strict Gold contracts;
- the retrieval loader's JSON duplicate-key guard also before Fidelity Gold validation;
- unchanged extraction and `score_record` for baseline status/evidence counters;
- the existing chunking source-unit builder for normalized Retrieval Gold span bounds.

The gate checks frozen manifest/Gold fingerprints, exactly 30 sources per format, identities,
duplicate hashes, presence, size, extension/MIME consistency, strict review states, source
references, supported locator geometry/span bounds and declared family/source split isolation.
Corpus matching is by bytes, not filenames. Unknown bytes are reported as unexpected-or-changed
files plus missing frozen identities; the audit cannot infer which unknown file replaced which
source. The authoritative corpus verifier still makes the final integrity decision.

Extraction runs serially with unchanged limits; third-party logs, warnings and exceptions are
contained. Input hashes and corpus integrity are rechecked afterwards, as is code/environment
identity. A missing required input produces BLOCKED/NOT_EVALUATED, never an empty or fixture PASS.
Invalid/changed inputs, unsupported composition or invalid supported locators produce FIX.
Failed extraction remains in the denominator and prevents PASS. `needs_review` remains visible
but does not invalidate a deliberately difficult offline benchmark population.

Outputs are new directories below ignored `evaluation-output/`: deterministic `metrics.json`
and human-readable `aggregate.md`. Existing outputs, nesting inside inputs and symlink escapes
are rejected. Reports omit runtime timings, timestamps, Git HEAD and machine paths; changing
the output directory or creating the completion commit does not change the audit fingerprint.
They contain only aggregate counters, fixed descriptions, configuration and fingerprints.

## Corpus-wide counts

All 90 originals were present and byte/size/format-matched. Manifest identities and hashes were
unique: zero duplicate IDs, manifest hashes or local file hashes; zero missing/changed identities,
unexpected/changed files, extension/size mismatches or corpus symlinks.

| Format | Frozen denominator / audited | Success / eligible by status | Needs review / excluded by status | Failed |
| --- | ---: | ---: | ---: | ---: |
| PDF | 30 / 30 | 27 | 3 | 0 |
| DOCX | 30 / 30 | 14 | 16 | 0 |
| XLSX | 30 / 30 | 15 | 15 | 0 |
| All | 90 / 90 | 56 | 34 | 0 |

Eligibility is only the unchanged `success` extraction-status gate, not proof that ingestion,
chunks or retrieval will succeed. All 34 excluded sources remain in the 90-document audit and
status denominator. No source was silently dropped to improve coverage or reported fidelity.

## Gold coverage and automatic checks

Extraction Gold contains 11 real reviewed records: PDF/DOCX/XLSX = 4/3/4, leaving 79 corpus
sources without Extraction Gold. All records attest original-document review with one reviewer.
There are 55 anchors, 22 partial-order pairs, 32 table-cell checks, 15 relationships and 13
stored-value/formula/cache checks. No split exists in the Fidelity schema: its split check is
NOT_APPLICABLE, not an invented dev/test assignment.

Of 68 locator checks (55 anchors plus 13 cell checks, not unique locations), 63 resolve to
supported source-unit geometry, zero are invalid and five are NOT_EVALUATED: four PDF spatial
table locators plus one DOCX ancillary locator. Of 15 relationships, 13 have supported units,
zero are invalid and two PDF spatial relationships remain NOT_EVALUATED automatically.
Those unsupported assertions retain the supplied human review; the gate does not fabricate
an independent PDF table inventory or treat missing parser structure as invalid human labels.

Retrieval Gold contains 48 reviewed questions, 45 answerable and three unanswerable, covering
15 sources and 14 declared families. Splits: 36 dev / 12 test. Zero declared family crossings
or identical-source crossings occur. All 80 evidence anchors resolve to supported source units
and bounded optional spans; zero invalid or unevaluated Retrieval Gold locators were found.

| Retrieval population | Reviewed sources | Questions | Evidence anchors |
| --- | ---: | ---: | ---: |
| PDF | 5 | 16 | 15 |
| DOCX | 5 | 17 | 18 |
| XLSX | 5 | 15 | 47 |
| All | 15 | 48 | 80 |

Seventy-five corpus sources have no Retrieval Gold coverage. Split validation concerns the
declared families, not the completeness of near-duplicate/version grouping. Unanswerability
and relevance are human assertions, not consequences of a valid locator or hash.

During implementation a raw-field versus normalized-source-unit span mismatch was detected.
The gate was corrected to reuse the existing builder, including DOCX table/XLSX metadata
prefixes; a regression test fixes that contract. No Gold span or label was changed to fit it.

## Preserved baseline failures

Unchanged `score_record` reproduces the prior combined control report:

| Selected reviewed metric | Passed / evaluated |
| --- | ---: |
| Required-text recall | 45 / 55 |
| Reading order | 16 / 22 |
| Table cells/spans | 28 / 32 |
| Table relationships | 13 / 15 |
| Provenance | 54 / 68 |
| Stored values, formulas, caches (each) | 13 / 13 |

Ten required anchors remain missing. Source-unit geometry resolution is not the stricter
text/provenance score: an existing page can contain a missing or wrongly located required
anchor. Displayed-value fidelity is NOT_EVALUATED (null score, no labels), not 0% or 100%.
Formula/cache equality includes reviewed null expectations and historical stored results;
no formulas were executed and no calculation correctness is established.

Only one reviewed PDF source has table labels. The independent PDF control is narrative;
it does not establish table-reconstruction generalization. Keep the known missing text,
table/provenance failures and all independent controls in the next paired comparison.
The same Gold and corpus must be used in both arms; held-out test labels are not tuning data.

## Fingerprints and environment

| Identity | SHA-256 / normalized fingerprint |
| --- | --- |
| Frozen manifest bytes | `c3a91af4bf789400f23821a30c6468040334bdd65135460b96dc21bb64d335c0` |
| Corpus identity map | `d32e9f9b2186d6973b59a1069df83d5d229a205ecac8d555091f6734053d47f8` |
| Extraction Gold normalized | `896ce2c0e99b74683a8b15869c7ab72b94a27dd06fce66896db4ec8652c75b6c` |
| Extraction Gold file bytes | `30cfdcf31f1036f1e6f813fad34266fa347b5368ee140be7304eb942f0e0d353` |
| Retrieval Gold normalized | `d6167fcf93d5cbce122e4bc444b478b23a0f02f3556364f1e3be58ad02f1bc94` |
| Retrieval Gold file bytes | `e166af3010ac821513380c8f9ce509bb6b84c8305f3f2afa1e1c77b978510118` |
| Gate Python source | `abf589a4343c05a09ad556ebac5718e513dd817528e790715eb1dce042a0e60f` |
| Gate unit-test source | `400866a7673fab0e470193a0887d9fd4ac1a7f44b3b2b8439acb14c081c8a937` |
| Parser source | `151186e13dfd0407ade2276217d6a0d07db39e9634cbf676fc34d42cf88a44c8` |
| Fidelity evaluator / corpus validator | `59bc64a98c58c8e2561af5fc8d50955e1c99f2ea7fc32d549ce8e5ebf069b31c` |
| Fidelity Gold validator | `4065b83b27c76fc7d6b615b393ad767d30415b43fa5dca83c31c859b748b07af` |
| Retrieval Gold validator | `b7083c69d1f9f16dae2cabd51ed3161ec79110c91e2ef1aafa19e32513d31ad4` |
| Retrieval source-unit builder | `6a6f8f4feac9076a27ed178e00049c85c27afb89a077cb22658e6c2350ca6a80` |
| Both final audit fingerprints | `b8b10368a897bd45b066ec3b6eb9384484da0a6d869e23bc88656041160d9e75` |
| Both metrics.json byte hashes | `59488d623e742e7d6fc078d88a313b971e24dbcc2344ac279bdf72e1e2fe64e8` |
| Both aggregate.md byte hashes | `7ca9a0f5898be97eddc58e5479872515cfe63801d8b7251e09799ec092b67bde` |

Code hashes normalize UTF-8 source newlines; input-file hashes are byte hashes. All code hashes,
extraction limits and dependency versions are retained in the ignored JSON. Python 3.12.3;
pypdf 6.20.0, python-docx 1.2.0, openpyxl 3.1.5, Pydantic 2.14.0. No latency/memory benchmark
was performed; no resource-performance comparison is claimed.

## Actual verification

Commands ran from the repository root:

```powershell
.venv/Scripts/python.exe -m ruff check src/doclens_ai/eda/data_quality_gate.py tests/unit/test_data_quality_gate.py
.venv/Scripts/python.exe -m ruff format --check src/doclens_ai/eda/data_quality_gate.py tests/unit/test_data_quality_gate.py
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/unit/test_data_quality_gate.py tests/unit/test_extraction_fidelity.py tests/unit/test_retrieval_eval.py tests/unit/test_chunking.py
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/unit
.venv/Scripts/python.exe -m doclens_ai.eda.data_quality_gate --output-dir evaluation-output/data-quality-gate-v3-verified-run1
.venv/Scripts/python.exe -m doclens_ai.eda.data_quality_gate --output-dir evaluation-output/data-quality-gate-v3-verified-run2
.venv/Scripts/python.exe -m doclens_ai.eda.data_quality_gate --retrieval-gold local-evaluation/data-quality-gate-v3-deliberately-absent.jsonl --output-dir evaluation-output/data-quality-gate-v3-missing-input-verified
# Missing-input probe: exit $LASTEXITCODE propagates the native CLI's exit code in PowerShell.
git diff --check
git status --short
```

Ruff and formatting: PASS. Targeted suites: **114 passed, 1 skipped**. Full unit suite:
**520 passed, 1 skipped**. The extra physical output-symlink test requires unavailable Windows
symlink privilege; it was explicitly skipped, not treated as verified. Actual corpus symlink
absence was checked without needing that privilege. The first sandboxed synthetic rename
probe was denied by Windows; fixture writer cleanup and the normal Windows test runtime
were used for the successful complete test runs. No real source was renamed or corrupted.

Both real audit commands returned PASS/exit 0. Python stdin assertions compared every report
field and the complete bytes of both output files: identical. The intentional missing-Gold
command returned BLOCKED/nonzero, with `retrieval_gold_unavailable` and NOT_EVALUATED Gold,
not a synthetic substitute. Synthetic tests separately verify changed bytes (including same
size), missing files, duplicate IDs/hashes, wrong suffixes, malformed/draft/foreign Gold,
duplicate JSON keys, locator/span bounds, table relationships, family/source leakage,
source mutation during audit, failure isolation, output confinement and deterministic output.

Additional stdin privacy assertions checked both real report pairs and the missing-input
report: no original filenames, private checkout paths, long private anchors/questions, or
forbidden content/path/locator/review-date keys. Approved manifest/Gold hashes remained
unchanged; the authoritative verifier rechecked all originals. Runtime outputs are ignored;
Git scope/privacy review must include only the three requested source/test/documentation files.

## Unverified properties and out-of-scope findings

- Original-document review is supplied human attestation, not independently established by
  the gate. No new approval, reviewer identity, date or annotation was generated.
- Near-duplicate absence, complete version-family assignment, semantic question/label accuracy,
  unanswerability and whole-document reading order remain NOT_EVALUATED.
- PDF spatial/table reconstruction, DOCX ancillary content, displayed spreadsheet fidelity,
  inter-reviewer agreement and whole-corpus extraction fidelity are not established.
- Corpus v1 is English-dominant public-sector data, not representative multilingual evidence.
  Existing source/license provenance is retained; no fresh online license/legal audit was run.
- The Retrieval protocol retains historical text describing review as outstanding; this gate
  validates the current private reviewed snapshot and does not silently rewrite that protocol.
- The standalone Fidelity Pydantic JSON entry point accepts duplicate JSON keys. This gate
  rejects them using the existing retrieval JSON guard; the standalone loader is unchanged
  because modifying its contract implementation is outside the permitted file scope.
- Existing helper APIs are reused without refactoring; changing their semantics or dependency
  versions requires rerunning the gate and freezing the next benchmark's new code identity.
- No PostgreSQL, Docker, production ingestion, index, retrieval or model-service E2E test was
  required or run for this read-only offline step. Logical limits are not hard CPU/RSS caps.

PASS therefore authorizes only preparing the controlled paired PDF benchmark on these exact
inputs with visible unsupported dimensions and controls. It does not erase known failures or
authorize production promotion, label modification or tuning against the test split.
