# RAG Answer Gold v1 review packet

## ML-5 finalization decision on 2026-10-16

PASS. The human approval gate and strict approved-Gold validation are complete for 20 real records.
The user explicitly confirmed review and approval of all 20 proposed RAG Answer Gold records on
2026-10-16 and supplied a separate reviewed snapshot. Exactly one human reviewer is attested;
there is no claim of independent second-reviewer agreement, adjudication or a signed review
document. The three negative judgments remain document-scoped. No reviewer identity is published.

The supplied reviewed file differs from the frozen draft in exactly two fields on every record:
reviewer_status changes from draft to reviewed and reviewer_count from 0 to 1. Every other field
and value is identical, including question text, reference/accepted answers, answerability,
categories, source SHA references, families, splits, quotations, locators, offsets and required
citation IDs. No labels were rewritten or repaired. No reviewed_on field was added: the unchanged
RagGoldExample schema has no such field.

The approved snapshot was created privately at
`local-evaluation/rag_gold_v1_approved.jsonl` using filesystem copy with overwrite disabled,
equivalent to exclusive destination creation. It did not exist before creation. The reviewed input
was read directly from the supplied attachment because a repository-local reviewed-input copy was
absent; no extra input copy was created. The approved file is byte-for-byte identical to the reviewed
input and was validated again with unchanged load_rag_gold and the committed Corpus v1 manifest.
It remains Git-ignored. Existing candidate and Retrieval/Extraction Gold snapshots were not changed.

## Frozen approved identities

The authoritative normalized identity is load_rag_gold(...).fingerprint, not a hash of the raw
JSON records. The prior expected normalized value was erroneous; it was the raw-record hash.
The user explicitly corrected that expectation before finalization. No schema, validator,
SourceLocation or hashing implementation changed.

Verified normalization explanation: validated model_dump(mode="json") materializes missing nullable
SourceLocation fields as null on all 28 anchors. Removing only those newly materialized null locator
keys reconstructs the original raw records exactly; no other value differs. The raw JSON hash below
is informational only and must not replace the strict-loader identity. The draft's previous
normalized fingerprint in the historical section likewise refers to raw draft JSON, not approved
Gold or the strict-loader identity.

| Identity | SHA-256 / fingerprint |
| --- | --- |
| Draft file bytes | `7eb3677883a8c3917ebb0692866058de22e20791b0e2426f352ed6b4b0374a54` |
| Reviewed input bytes | `a818104a22833e174ceef572df8c699b81e93a5fd61d90092f33705ad61d7fa0` |
| Approved snapshot bytes | `a818104a22833e174ceef572df8c699b81e93a5fd61d90092f33705ad61d7fa0` |
| Authoritative strict-loader normalized Gold | `66e84c335da8c6fd51468bed623e24ed7dc276e8dfc051f2a0261274105f00ee` |
| Raw reviewed JSON, informational only | `4bfd0a91bd64552798995df01d81ae5d702fcc0f571600083df2775e54e6e656` |
| Committed manifest, working-file bytes | `c3a91af4bf789400f23821a30c6468040334bdd65135460b96dc21bb64d335c0` |
| Frozen 90-source identity map | `d32e9f9b2186d6973b59a1069df83d5d229a205ecac8d555091f6734053d47f8` |
| Unchanged question selection | `33e9ddf200234462b10ab0ad4a7edae257739ec56789f13c30912b1d65ae1d6b` |
| Unchanged canonical unit/span identity | `3ddc83af0101ac577b5774cc21b669e2e2b25a0d6e9934e029570f2b7eeaebcb` |

Strict validation is reproducible across repeated loads of the reviewed and approved files;
validating reversed model-record order produces the same authoritative fingerprint.

## Final reviewed-label coverage

- Exactly 20 unique reviewed real records: 17 positive, three negative; 15 dev and five test.
- All 20 have reviewer_status=reviewed, reviewer_count=1, synthetic_fixture=false and the unchanged
  corpus-v1-rag-gold-v1 dataset revision.
- Question formats: PDF 7, DOCX 7, XLSX 6. Fifteen unique original sources: five per format.
- Categories: number 6, table 4, identifier 3, version 2, fact 2, unanswerable 3.
- Language: EN 20; RU 0; KK 0. All three negatives are dev, with no held-out test negatives.
- All 90 original files passed existing verify_corpus hash, size and format verification. All 15
  selected original sources remain canonical-extraction success eligible.
- All 28 positive evidence anchors match exact normalized source-unit slices with valid unique
  locators, source identities and exclusive source bounds. Required citations resolve to existing
  anchors. Positive reference answers remain unchanged and nonblank; negative answers and positive
  evidence remain absent.
- Existing strict schema and duplicate-key guards reject unknown fields and duplicate keys;
  top-level and nested duplicate probes both failed closed. No shared source or family crosses
  splits. Approved corpus references and the parent Retrieval Gold identity remain valid.

## Finalization verification actually executed

The tracked baseline was clean. Its only visible untracked task file was this existing review
packet, and the relevant private JSONL inputs were ignored. Checks ran before approved creation and
again after it, without printing private text or writing an acquisition/validation framework.
The private approved snapshot is the only new runtime data file from this finalization.

```text
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/unit/test_retrieval_eval.py tests/unit/test_rag_gold.py
49 passed in 1.96s; exit 0.
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/unit
557 passed, 1 skipped in 16.93s; exit 0.
Skip: tests/unit/test_data_quality_gate.py:432, Windows symlink privilege unavailable.
.venv/Scripts/python.exe -m ruff check src tests alembic
All checks passed.
git diff --check
PASS.
git check-ignore local-evaluation/rag_gold_v1_candidates.jsonl local-evaluation/rag_gold_v1_approved.jsonl
Both private files ignored.
```

Both pytest commands were executed in the previously verified unrestricted local Windows runtime,
through subprocess.run wrappers with 45-second focused / 150-second full-unit timeouts. No tests
or system settings were changed to bypass the known sandbox socketpair restriction. The earlier
sandbox trace and Linux repeat are preserved below as history, not represented as fresh runs.

Read-only validation via `.venv/Scripts/python.exe -` used the existing strict load_rag_gold,
strict_json, manifest/corpus verifier and extraction/source-unit contracts. It verified both input
byte pins, exactly 20 metadata-only differences, all schema/review/answer/evidence rules, counts,
all 90 originals, all 15 selected sources, 28 exact spans, family/source split isolation, the
nullable-field normalization explanation and authoritative fingerprints before copying. After
exclusive byte-preserving creation the same checks ran again on the approved snapshot, including
reversed-order fingerprint invariance and preserved previous private-snapshot byte hashes.
No raw annotations, questions, answers or source quotations are included here.

Final staged-path and index-content inspection passed: exactly this sanitized Markdown was staged,
the staged text matched the inspected working file, and no private questions, answers, long source
excerpts, absolute document paths or credential patterns were found. git diff --cached --check
passed. The approved snapshot is ignored and is not staged; no private JSONL enters the commit.

## Scope and remaining evaluation limitations

This freezes human-reviewed answer labels, not measured model quality. No LLM generation,
prompt tuning, Docling execution, fine-tuning or RAG quality benchmark was run. Production RAG,
retrieval/indexing behavior, schemas, validators, tests and dependencies remain unchanged.

Limitations persist: English-only labels; no reviewed RU/KK answers; no held-out test negatives;
only three document-scoped negatives; small purposive sample; previously observed test questions
are not fresh blind evaluation; one reviewer rather than adjudicated agreement; no human review of
real generated outputs; no demonstrated end-to-end RAG quality. Source checks and structural
citation validity do not alone establish semantic support of a generated answer.

## Historical preparation record

The following sections preserve the source-validation history, per-question review requirements
and async-test diagnosis from preparation. Any historical pending-approval wording refers to the
earlier draft stage and is superseded by the passed approval gate and frozen identities above.

## Historical draft preparation decision

Preparation passed after the ML-5 correction. At that time Gold was BLOCKED_AWAITING_HUMAN_REVIEW.
There were 17 complete, concise source-grounded draft reference answers, zero unresolved positive
answers, and three source-scoped negative cases. The preparation candidate remains unchanged with
reviewer_status=draft, reviewer_count=0, synthetic_fixture=false and the real dataset revision.
The separate supplied reviewed input and frozen approved snapshot now carry reviewed/1 metadata.

This supersedes the earlier partial preparation: reference_answer no longer contains concatenated
evidence slices. Only those 17 fields changed in the private candidate. Questions, accepted_answers,
source identities, family/split assignments, evidence quotations, locators, offsets, required
citation references and reviewer metadata are unchanged. The negative records remain unchanged.
No production code, tests, approved Gold, corpus bytes, dependencies or system settings changed.
No generation, candidate inference, prompt optimization or model-quality benchmark was executed.

## Frozen selection and coverage

The fixed question IDs below are unchanged: 20 of the existing 48 reviewed Retrieval Gold questions.
Selection remains purposive and deterministic, independent of retrieval scores or generator outcomes.
Five positive DOCX, six positive PDF and six positive XLSX cases, plus the same three dev negatives,
give seven DOCX, seven PDF and six XLSX cases. Fifteen unique original sources are covered, five per
format. Dev/test is 15/5; positive/negative is 17/3. Categories: number 6, table 4, identifier 3,
version 2, fact 2, unanswerable 3. All questions are EN; RU/KK coverage is absent.

All 90 originals passed the existing strict manifest SHA-256, size and format checks. The 15 selected
unique sources all have current canonical extraction status success. Source identity references,
declared families and splits remain exactly those of reviewed Retrieval Gold. No family or shared
source crosses dev/test. There are no held-out test negatives; none were fabricated. Previously
observed test questions/results are not fresh blind evaluation and must not be used for model tuning.

## Source-grounded preparation method

The original document, not a generated response or Docling output, was the evidence authority.
The question and each quoted span were checked in the canonical units and independently against
the relevant original representation:

- PDF: Poppler rendered six complete pages across five originals directly to memory. This included
  both pages of the correction document, the process diagram, letter, cover and the complete
  one-page procedural negative source. No page images or extracted content were saved as artifacts.
- DOCX: original OOXML body blocks and the relevant table rows/cells were inspected, including
  surrounding context and original block ordering. The two negative originals were inspected in
  full, with ancillary-part and embedded-object checks. No Word-rendered layout fidelity is claimed.
- XLSX: original workbook relationships, shared strings, sheet XML, row/column coordinates, merged
  ranges and surrounding headings were read independently of canonical serialization. Stored cell
  values and any formula tags were distinguished. The 17 selected XLSX evidence entries have no
  formula tags; no formulas were executed or cached/displayed results invented. Spreadsheet
  application rendering was not used to assert displayed formatting.

The revised references state only the requested fact, number, role, identifier, classification,
period or version distinction. They omit canonical scaffolding and unrelated surrounding text.
Accepted variants remain empty rather than inventing paraphrases; each reference is a proposal for
human review. A short answer can naturally repeat a source field or identifier without becoming a
quote container. Positive answers were not copied from a generator's output or derived from ranking
scores. These editorial source checks do not constitute human approval or reviewed output scoring.

Each of the 28 evidence entries was rechecked against a uniquely located canonical source unit:
exact source SHA and format, valid locator, bounded zero-based exclusive start/end, and exact slice
equality with verified_quote. Offsets are not raw-file or chunk offsets. Required citation IDs are
unique, refer to existing evidence, and are unchanged. Semantic support was checked in original
context, not inferred from valid locator syntax.

## Per-question human-review requirements

Full questions, proposed answers, exact values and quotes remain only in the ignored candidate.
The checklist below is sanitized; use it beside each private record and its hash-verified original.
Every positive requires checking all answer assertions and all required citations, not just spelling.

| Question ID | Source | Format | Split | Category | Anchors | Required original-document review |
| --- | --- | --- | --- | --- | --- | --- |
| rgv1-q-001 | c1-0001 | DOCX | dev | identifier | 1 | Compare the entire application identifier, including prefix, slash and digits; do not substitute a land-register identifier. |
| rgv1-q-003 | c1-0001 | DOCX | dev | number | 1 | Verify the hearing time, meridiem and its association with the stated hearing date; not a publication date. |
| rgv1-q-008 | c1-0008 | DOCX | dev | table | 1 | Verify the requested inspection-date field in the facility table; do not invent a populated inspection date. |
| rgv1-q-010 | c1-0009 | DOCX | test | number | 1 | Preserve the strict greater-than boundary and currency; do not change it to greater-than-or-equal or a fee total. |
| rgv1-q-015 | c1-0014 | DOCX | dev | version | 1 | Associate each date with original versus revised statement; avoid reversing versions or using a consent date. |
| rgv1-q-016 | c1-0032 | PDF | dev | fact | 1 | Inspect the diagram's approval step; distinguish the approving role from the statistician performing verification. |
| rgv1-q-020 | c1-0034 | PDF | dev | version | 1 | Read both correction pages and the replacement paragraph; preserve the before/after duration and do not answer from superseded wording. |
| rgv1-q-021 | c1-0034 | PDF | dev | number | 1 | Check the extension month/year in the corrected paragraph, not the printing or correction date. |
| rgv1-q-022 | c1-0038 | PDF | test | fact | 1 | Verify addressee, role and organization in the letter address; do not confuse recipient with signatory. |
| rgv1-q-025 | c1-0048 | PDF | dev | number | 1 | Check the cover's closing date, not a publication year or another deadline elsewhere in the document. |
| rgv1-q-028 | c1-0053 | PDF | dev | identifier | 1 | Check the acronym expansion and plurality against the heading/body; add no interpretation of complaint outcomes. |
| rgv1-q-031 | c1-0062 | XLSX | test | identifier | 3 | Match the named vessel row to the registration column; preserve identifier digits without arithmetic or decimal suffixes. |
| rgv1-q-032 | c1-0062 | XLSX | test | table | 3 | Match the named vessel to the flag column in the same row, not port letters or another vessel. |
| rgv1-q-035 | c1-0063 | XLSX | dev | number | 5 | Verify region, both grade labels and entry rather than maximum column; retain stored text precision. Do not infer currency, pay frequency or resolve differing surrounding date headings. |
| rgv1-q-038 | c1-0065 | XLSX | dev | table | 3 | Verify the policy row and its classification cell together; the generic column heading alone is insufficient. Do not confuse a payment amount with table-scale budget figures. |
| rgv1-q-041 | c1-0066 | XLSX | dev | table | 2 | Verify the year and classification are vertically aligned in the same column; do not take the adjacent year. |
| rgv1-q-045 | c1-0086 | XLSX | test | number | 1 | Preserve the count of known groups and exclude the separately described unknown group; do not add them together. |
| rgv1-q-046 | c1-0001 | DOCX | dev | unanswerable | 0 | Confirm the entire notice is prospective and contains no post-hearing determination; do not infer what later happened. |
| rgv1-q-047 | c1-0003 | DOCX | dev | unanswerable | 0 | Confirm the applicant-name and signature fields are blank and distinguish template instructions from entered personal data. |
| rgv1-q-048 | c1-0053 | PDF | dev | unanswerable | 0 | Inspect the complete procedural source; generic stages and appeal rights are not an individual case ruling. |

## Actual negative review scope

These are source-scoped negative proposals, not corpus-wide or externally verified claims.
The answerable flags are inherited unchanged from Retrieval Gold; this task rechecked their scope
without adding unsupported negative evidence or enlarging source lists.

- rgv1-q-046: the full c1-0001 original body, all 13 paragraph/table-level blocks including blanks,
  was read. It is a prospective notice with attendance/application instructions rather than a later
  determination. Original package inspection found no tables, drawings, legacy pictures, embedded
  objects, simple fields, deleted runs or header/footer/notes/comment parts to supply an outcome.
  No later notice, external decision, linked/contact material or other corpus document was checked
  as part of this negative judgment.
- rgv1-q-047: the full c1-0003 original body, all 48 blocks including blanks, was read. Applicant
  name/signature fields and the receipt template contain no completed applicant name. There are no
  tables, drawings, legacy pictures, embedded objects, simple fields or deleted runs. The original
  footnote/endnote parts have zero nonblank text nodes. The scope is this uncompleted original only,
  not possible filled copies, external forms, document authorship metadata or any person's identity.
- rgv1-q-048: the complete one-page c1-0053 original was visually inspected, including all sections,
  footer and external-link area, and compared with its canonical source unit. It describes a generic
  complaint/appeal process, not a named individual's final outcome. External linked material and
  other case files were not fetched or reviewed. The claim is limited to this one-page source.

A human must independently confirm these scopes and labels. A missing search hit, extraction
eligibility flag or valid empty-negative schema was not used as proof of unanswerability.
No evidence anchors, accepted answers, reference answer or required citation IDs were added to
negative records. Their null reference answers are intentional and are not unresolved positives.

## Schema, identity and reproducibility verification

All 20 proposed records have exactly the existing RagGoldExample fields. Each field was validated
with its existing Pydantic annotation AND metadata constraints via TypeAdapter with strict=True;
nested evidence also passed the unchanged RagAnchor model. Positive/negative consistency, reference
membership/uniqueness, identity, manifest, family/split and span rules were checked separately without
inventing a permissive Gold loader or changing status/count. The unchanged full model rejects all
20 drafts specifically for absent human answer review, and load_rag_gold rejects the candidate.
No record was temporarily marked reviewed or fixture for validation.

Both a pre-edit byte inventory and post-edit checks confirm all approved Retrieval/Extraction Gold
and all other existing private JSONL snapshots are unchanged. Source/scoring/schema/chunking/test
files and pyproject.toml also retain their pre-task SHA-256 values. Only reference_answer differs in
the 17 positive candidate records; the other fields and all negative records are identical.

Previous draft file SHA-256:
`d2fb746368d5f5afd2bd506a3f9f0bf4a1a3f687769214145187323b402aa7a1`.
Previous normalized draft fingerprint:
`ec2d39fe32c4c64587098c312f59b40aa2c7835d09b4a70183bbdcc2768d0b68`.
The changed hashes below reflect the revised reference answers, not source/evidence/review changes.
Selection and canonical-unit/span fingerprints remain unchanged. JSONL file SHA hashes exact UTF-8
bytes; normalized fingerprints use sorted-key compact JSON with the existing fingerprint function.
The normalized draft hash is NOT an approved-Gold fingerprint.

```json
{
  "changed_reference_answers": 17,
  "corpus_fingerprint": "d32e9f9b2186d6973b59a1069df83d5d229a205ecac8d555091f6734053d47f8",
  "draft_normalized_fingerprint": "8502a62fc288566031fd2ab242c87e900042654b49eb39d922a5b0c8dbf4b523",
  "draft_sha256": "7eb3677883a8c3917ebb0692866058de22e20791b0e2426f352ed6b4b0374a54",
  "evidence_spans": 28,
  "manifest_sha256": "c3a91af4bf789400f23821a30c6468040334bdd65135460b96dc21bb64d335c0",
  "negative": 3,
  "positive_complete": 17,
  "question_count": 20,
  "retrieval_gold_fingerprint": "d6167fcf93d5cbce122e4bc444b478b23a0f02f3556364f1e3be58ad02f1bc94",
  "selected_sources_fingerprint": "a11609c3a6f1ee0ee72c29e591d97a04fb0d8f46ad5f431f780ac1e66757e768",
  "selection_fingerprint": "33e9ddf200234462b10ab0ad4a7edae257739ec56789f13c30912b1d65ae1d6b",
  "source_status_counts": {
    "success": 15
  },
  "unique_sources": 15,
  "unit_span_fingerprint": "3ddc83af0101ac577b5774cc21b669e2e2b25a0d6e9934e029570f2b7eeaebcb",
  "unresolved_positive": 0
}
```

## Async-test diagnosis and actual regression results

A bounded reproduction of the unchanged final async RAG Gold test timed out after 12 seconds in
the restricted Windows sandbox. faulthandler at five seconds showed
socket.socketpair -> socket.accept during asyncio ProactorEventLoop self-pipe construction,
before the test coroutine starts. An independent standard-library socket.socketpair child also
timed out after 12 seconds, with a traceback after eight seconds. Both owned children were terminated
by subprocess.run(timeout=12); no unrelated process was stopped.

The exact same minimal socket call outside the sandbox passed immediately (exit 0), and the full
unchanged Retrieval/RAG Gold suite outside the sandbox passed: 49 passed in 3.03s, exit 0.
This isolates the observed failure to the restricted execution context, not a demonstrated defect
in RAG code. The underlying sandbox/network implementation mechanism was not diagnosed; no global
Windows defect, firewall cause or dependency incompatibility is asserted. No policies, socket code,
event-loop selection, approvals or test assertions were changed to bypass the failure.

Linux was also checked using an existing local API image, no pull/build/download/install, with
network disabled, a read-only filesystem, tmpfs for test temporaries and narrow read-only mounts.
The image has existing runtime dependencies but no pytest. Existing host pytest packages were made
available read-only as a fallback sys.path entry after Linux packages; the anyio plugin was explicitly
enabled and both unchanged test files ran. No private originals or Gold were mounted.
The first run omitted the existing public synthetic fixture mount: 26 failed, 23 passed in 5.70s
due to that missing file. After adding that one fixture mount, the full repeat passed:
49 passed in 2.69s, exit 0. No tests or product code were altered to obtain this result.

Executed Windows commands (repository root; the first two use the normal sandbox and 12-second
subprocess bounds, the third uses the approved unrestricted local test runtime):

```powershell
@'
import faulthandler, subprocess, sys
code = 'import faulthandler,socket; faulthandler.dump_traceback_later(8); print("before socketpair",flush=True); a,b=socket.socketpair(); print("socketpair PASS",flush=True); a.close(); b.close()'
subprocess.run([sys.executable, '-c', code], timeout=12)
'@ | .venv/Scripts/python.exe -

@'
import subprocess, sys
subprocess.run([sys.executable, '-m', 'pytest', '-v', '-p', 'no:cacheprovider',
               '-o', 'faulthandler_timeout=5',
               'tests/unit/test_rag_gold.py::test_deterministic_metrics_are_sanitized_and_not_human_groundedness'],
               timeout=12)
'@ | .venv/Scripts/python.exe -

@'
import subprocess, sys
p = subprocess.run([sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
                    '-o', 'faulthandler_timeout=10',
                    'tests/unit/test_retrieval_eval.py', 'tests/unit/test_rag_gold.py'],
                    timeout=45)
print('EXIT:', p.returncode)
'@ | .venv/Scripts/python.exe -
```

The actual diagnostic wrappers caught TimeoutExpired and printed captured traceback/termination
status; the snippets show the same child invocations and enforced deadlines. The minimal socket
command was repeated outside the sandbox and returned socketpair PASS, exit 0.

Final Linux command, with the executed absolute repository prefix parameterized for portability:

```powershell
$repo = (Get-Location).Path
docker run --rm --pull=never --network none --read-only --tmpfs /tmp:rw,size=256m --workdir /workspace -e PYTHONDONTWRITEBYTECODE=1 -e PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 -e PYTHONPATH=/workspace/src:/workspace --mount "type=bind,source=$repo/src,target=/workspace/src,readonly" --mount "type=bind,source=$repo/tests,target=/workspace/tests,readonly" --mount "type=bind,source=$repo/pyproject.toml,target=/workspace/pyproject.toml,readonly" --mount "type=bind,source=$repo/docs/eda/corpus_v1_manifest.csv,target=/workspace/docs/eda/corpus_v1_manifest.csv,readonly" --mount "type=bind,source=$repo/docs/evaluation/synthetic_retrieval_gold_fixture.jsonl,target=/workspace/docs/evaluation/synthetic_retrieval_gold_fixture.jsonl,readonly" --mount "type=bind,source=$repo/.venv/Lib/site-packages,target=/hostsite,readonly" --entrypoint python doclens-search-1791968383266-smoke-api:latest -c "import sys; sys.path.append('/hostsite'); import pytest; raise SystemExit(pytest.main(['-q','-p','no:cacheprovider','-p','anyio.pytest_plugin','-o','faulthandler_timeout=15','tests/unit/test_retrieval_eval.py','tests/unit/test_rag_gold.py']))"
```

The normal sandbox's initial Docker daemon inventory was denied. Approved daemon access enabled
the isolated verification above; unrelated running containers were neither stopped nor modified.
The selected existing image ID was c31410788c87; Linux Python was 3.12.13, Windows Python 3.12.3.
These mechanics tests exercise an in-memory synthetic generator, not real generation or a
corpus/model benchmark. Source-based draft preparation and test verification are separate gates.

## Historical approval-gate requirements and privacy

Review every row above against the original and private candidate, including numerical boundaries,
all table associations, version semantics, absence of unsupported assertions and all negative
scopes. Record actual reviewer identity/approval privately. Only a genuinely reviewed separate
snapshot may later enter strict approved-Gold validation. Do not change metadata merely to silence
the draft rejection.

No private question, reference answer, accepted variant, quote, worksheet name, document filename,
absolute document path or reviewer identity is included in this shareable packet. The candidate
remained Git-ignored and nothing was staged at the preparation stage. That stage prohibited a
completion commit; the current finalization explicitly authorizes only this sanitized Markdown.
No new files were created during the correction stage; its changes were limited to the two
permitted existing files. The current finalization additionally creates the ignored approved snapshot.
Final checks executed:

```text
.venv/Scripts/python.exe -m ruff check src tests alembic
All checks passed.
git diff --check
PASS, no whitespace errors.
git diff --stat
Empty: no tracked production/test changes; the pre-existing packet remains untracked.
git diff --cached --name-only
Empty: nothing staged.
git check-ignore local-evaluation/rag_gold_v1_candidates.jsonl
Private candidate remains ignored.
git status --short
?? docs/evaluation/rag_gold_v1_review_packet.md
```

Read-only validation was executed twice via `.venv/Scripts/python.exe -` with identical metadata:
90 source identities/sizes/formats, 20 field-level schemas, 28 canonical spans, 20 strict draft-model
rejections, strict file-loader rejection, unchanged selection and all pre-existing approved bytes.
Exact before/after candidate comparison confirmed only the 17 positive reference_answer fields
changed. Privacy checks found no private questions, reference-answer excerpts, long source quotes,
absolute document paths or credential patterns in this packet. These ad-hoc checks are not added as
new scripts or a weaker replacement Gold loader; no Python source or test was changed.

Human approval was outstanding at the preparation stage and is now attested as described above.
Remaining limitations are no RU/KK or held-out-negative coverage, limited source-only negative
scopes, no native Office visual review and no model-quality or whole-corpus semantic assessment.
A structurally valid quote is not itself proof of an answer's meaning. Repository RAG,
PDF and spreadsheet read-only guidance informed these separate checks and limitations.
