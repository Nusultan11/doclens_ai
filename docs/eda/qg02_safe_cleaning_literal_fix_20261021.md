# QG-02 scoped XLSX literal-preservation correction

Engineering result: PASS for the reproduced defect and synthetic regression scope.
Starting branch/HEAD: `main`, `2674873dfbcfa4d46eced3e46313c6161d867dbb`.
The pre-existing untracked independent engineering audit is excluded from this step.
No full QG-02 qualification or independent quality verdict is issued.

## Contract and reproduced failure

[QG-02](../../DocLens_AI_Project_Goals_and_Quality_Policy-1.md#QUALITY-GATES)
forbids silent factual correction and unverifiable remapping.
[ML-CHUNK](../../DocLens_AI_ML_Quality_Strategy.md#ML-CHUNK) requires versioned
transforms and preservation of literals, formulas and genuine provenance;
[ML-DATA](../../DocLens_AI_ML_Quality_Strategy.md#ML-DATA) keeps synthetic probes
distinct from reviewed Gold. The data-quality and ingestion-change skills were
applied to these boundaries only.

Existing cleaning is embedded in `chunking/core.py`. `_xlsx_cell_unit` applied
`_normalize_text` to the complete rendered cell. That prose transform replaces
CRLF and CR with LF and strips trailing whitespace. This also changes characters
inside stored values, cached values and quoted formula strings. For example,
the synthetic formula string `"not\r\nне\rжоқ"` became `"not\nне\nжоқ"`;
a stored value ` 0007\t\r\n ` lost its trailing characters. These are literal
changes, even though coverage of the already-normalized text appeared complete.

Before changing implementation, this command reproduced **12 failures**, with
37 other then-existing probes deselected (exit 1):

```powershell
.venv/Scripts/python.exe -B -m pytest tests/unit/test_safe_cleaning.py -k preserves_literal_line_endings -q --tb=short -p no:cacheprovider
```

## Correction and boundaries

The single transformation change retains the XLSX cell rendering verbatim instead
of passing it through prose normalization. Formula evaluation, cell wrappers,
metadata, chunk strategies and source-location construction are unchanged. The
default chunking version changes from `1.1` to `1.2`, so configuration fingerprints
and newly generated chunk identities distinguish this behavior. This also changes
default fingerprints for other formats, without changing their cleaning rules.
Explicit caller-supplied configuration versions remain caller-controlled.

Tests use only newly authored synthetic extraction objects and fixture-byte hashes;
they do not claim those hashes identify real XLSX archives. No extraction code,
indexing/publication code, historical report, corpus, Gold or private review
payload is modified. No dependency, model, network transfer or comparison is used.

The existing provenance basis is a **rendered source unit**, not a RAW-byte offset
or an XML/glyph offset. For the XLSX cases, every overlapping chunk is checked
against the exact preserved unit slice, then all intervals reconstruct that unit
without missing or conflicting character assignments. Generated wrapper characters
remain wrapper characters, with no new claim that they exist in the source file.
Missing document identity or source SHA emits no chunks/references. A changed
supplied SHA produces different chunk IDs; the cleaner accepts extraction results
and does not itself reread RAW bytes or authenticate a caller-supplied digest.

## Executed verification

Final targeted command: **100 passed**, exit 0, including 86 new synthetic probes
and 14 existing chunking tests:

```powershell
.venv/Scripts/python.exe -B -m pytest tests/unit/test_safe_cleaning.py tests/unit/test_chunking.py -q --tb=short -p no:cacheprovider
```

The probes cover CR/CRLF, trailing spaces/tabs, signs (including Unicode minus),
exact decimal separators/precision, leading zeros, dates, percentages, units,
identifiers, RU/KK/EN negation, formula strings and links. Both strategies and all
three XLSX literal fields are exercised. Repeated calls compare complete outcomes;
input objects and source identity/location are preserved. Negative checks cover
missing identities, changed source identity and changed configuration identity.
PDF/DOCX probes check unchanged factual tokens and explicitly normalized offsets.

Final broader command: **237 passed**, zero skipped/errors/failures, exit 0,
6.66 seconds. It includes source/provenance conflicts, forged evidence, extraction
gates, ingestion failures and processing identities from the existing suites:

```powershell
.venv/Scripts/python.exe -B -m pytest tests/unit/test_safe_cleaning.py tests/unit/test_chunking.py tests/unit/test_ingestion.py tests/unit/test_processing_state.py tests/unit/test_retrieval_eval.py tests/unit/test_evidence_regressions.py tests/unit/test_ml28_evidence.py -q --tb=short --strict-config --strict-markers -p no:cacheprovider --basetemp=evaluation-output/qg02-safe-cleaning-20261021/tests-final --junitxml=evaluation-output/qg02-safe-cleaning-20261021/tests-final.xml
.venv/Scripts/ruff.exe check src tests tools alembic
.venv/Scripts/ruff.exe format --check tests/unit/test_safe_cleaning.py
git diff --check
git diff --cached --check
```

Ruff and diff checks pass. The first restricted broader run stalled while executing
async ingestion probes and was interrupted; the final complete run above used
approved local process/socket support. Two exploratory restricted filesystem walks
also stalled and were stopped. They produced no integrity verdict.

The completed read-only integrity check reused the existing pre-step protected
SHA-256 ledger with this check (the local result also records the baseline path):

```powershell
@'
import hashlib, json
from pathlib import Path
baseline = Path('evaluation-output/qg00-annotation-rights-20261021/tracked-assisted-reproduction-20261021/protected-before.json')
records = json.loads(baseline.read_text())
for name, expected in records.items():
    with Path(name).open('rb') as handle:
        assert hashlib.file_digest(handle, 'sha256').hexdigest() == expected, name
print(len(records), 'protected files unchanged')
'@ | .venv/Scripts/python.exe -B -
```

**5,817 files checked; zero missing/changed**. Its scoped result is saved locally at
`evaluation-output/qg02-safe-cleaning-20261021/integrity.json`.
The final staged-file whitelist contains only `chunking/core.py`,
`chunking/models.py`, `tests/unit/test_safe_cleaning.py` and this report;
`git diff --cached --name-only` and the full staged diff were inspected. No RAW,
Gold, annotations, generated output, private source content or the old audit is
staged. Git action is one Conventional Commit; no push.

## Remaining evidence

Independent multilingual/format evaluation and full QG-02 qualification remain
outstanding. PDF/DOCX original-to-normalized remapping evidence is not established
by these token-preservation probes. Real persistence/indexing/service integration
was not run: this change touches no publication or persistence boundary. Historical
records are not rebuilt or relabeled, and synthetic fixtures never become Gold.
