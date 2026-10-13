# Retrieval Gold v1 protocol

## Status and scope

This protocol defines the offline retrieval-evaluation contract that must precede embeddings,
Qdrant, production retrieval, reranking, or answer generation. It validates labels and scores
already-produced ranked results; it does not retrieve documents itself.

No real manually reviewed retrieval Gold dataset is committed. Corpus v1 is an extraction and
chunking corpus, not a question-answer relevance dataset. The committed
`synthetic_retrieval_gold_fixture.jsonl` exists only for automated contract and metric tests. Its
English, Russian, and Kazakh strings are artificial and provide no evidence of language coverage or
retrieval quality. Corpus v1 is English-dominant (88 English and 2 Welsh documents); verified Russian
and Kazakh evaluation examples remain an annotation gate.

Real annotation snapshots belong under ignored `local-evaluation/`, with access controls appropriate
to their content. Do not commit source documents, extracted text, private questions, reviewer
identities, predictions, or reports containing sensitive data.

## Versioned JSONL contract

Each line is one strict JSON object. Unknown or missing fields are rejected.

- `schema_version`: `1.0`.
- `question_id`: stable opaque identifier, independent of database UUIDs.
- `dataset_revision`: `corpus-v1-retrieval-gold-v1` for a future real Corpus v1 snapshot, or
  `synthetic-retrieval-gold-v1` for the test fixture.
- `synthetic_fixture`: must agree with the dataset revision.
- `document_family_id`: human-assigned near-duplicate/version family used for splitting.
- `language`: `en`, `ru`, or `kk`.
- `question`: the reviewed question text.
- `category`: `fact`, `number`, `table`, `identifier`, `version`, or `unanswerable`.
- `answerable`: whether verified positive evidence exists.
- `source_document_sha256`: immutable source-byte identity. Corpus v1 references must occur in the
  committed manifest.
- `evidence`: zero or more verified source anchors.
- `split`: `dev` or held-out `test`.
- `review_status`: `draft`, `reviewed`, or `adjudicated`.
- `reviewer_count`: count only; reviewer identities do not belong in the snapshot.
- `adjudication_state`: `not_required`, `pending`, or `resolved`.

Strict Gold validation rejects drafts, pending/contradictory review states, duplicate question IDs,
mixed or unknown revisions, invalid SHA-256 values, unsupported labels, answerable questions without
evidence, unanswerable questions with evidence, and any document family appearing in both splits.
Duplicate JSON fields, repeated evidence locations under different IDs, and a source hash assigned
to multiple families are rejected. Drafts cannot be scored by bypassing the review gate.
Exact hashes detect byte equality; annotators must still assign document families because hashes do
not detect near duplicates or versions.

## Evidence anchors and matching

An evidence anchor contains a stable `evidence_id`, source SHA-256, `document_format`, structural
`locator`, and optional normalized `source_start`/`source_end`. Locators mirror the extraction and
chunking contracts:

- PDF: positive `page_number`, with optional `block_index`.
- DOCX: `block_index`; table evidence may add `table_index`, `row_index`, and `column_index`.
- XLSX: `sheet_index` plus `cell_coordinate` (a cell or range) or `table_index`; sheet name and
  row/column indexes may be retained when available.

Ranked results carry one or more source anchors for each ranked chunk. Matching uses SHA-256, format,
and every locator field specified by Gold. Extra returned locator detail is allowed. If Gold specifies
a source span, the returned span must contain it. `ProcessingRun`, canonical chunk, Qdrant point, and
other runtime UUIDs never participate in matching, so a database re-import does not invalidate Gold.
Unresolved or malformed anchors never count as matches.

## Annotation workflow

1. Freeze and verify Corpus v1 bytes against `docs/eda/corpus_v1_manifest.csv`.
2. Group byte-identical, near-duplicate, and version-related documents under an explicit stable
   document-family ID before splitting.
3. Assign whole families to dev or test; never move individual family members across the boundary.
4. Draft answerable and unanswerable questions without consulting retrieval output.
5. Verify each answerable label against the original rendered document and record the narrowest
   reliable locator/span. Verify that unanswerable questions have no supporting evidence in scope.
6. Have a human reviewer confirm question, answerability, category, source identity, and anchors.
   Resolve disagreements explicitly; only `reviewed/not_required` or
   `adjudicated/resolved` examples enter Gold.
7. Freeze JSONL as a new immutable dataset revision, preserve its fingerprint, and keep test labels
   held out from tuning.

Approval and completion of this workflow remain outstanding. The framework must not be used to claim
Russian, Kazakh, or overall retrieval quality until an approved snapshot exists.

## Ranked-results contract and metrics

Each results JSONL record contains `schema_version`, compatible `dataset_revision`, `question_id`, and
`results`. Each result has a unique positive `rank`, a non-empty list of evidence anchors, and optional
diagnostic `runtime_chunk_id` and trusted `workspace_id`. A record may supply
`authorized_workspace_id`; results outside it, or missing result scope, are security violations.

Quality metrics use these explicit denominators:

- Hit@k: answerable questions with at least one matched anchor / answerable questions.
- Recall@k: distinct matched Gold anchors / all Gold anchors on answerable questions.
- MRR: sum of reciprocal first relevant ranks / answerable questions.
- nDCG@10: binary gain at a result rank is 1 if it matches at least one previously unmatched Gold
  anchor, otherwise 0. DCG is `sum(gain_r / log2(r + 1))` for ranks 1..10. IDCG is
  `sum(1 / log2(r + 1))` for ranks 1..min(10, number of Gold anchors). Per-query DCG/IDCG is then
  averaged over answerable questions. This convention assumes one ideal result per Gold anchor;
  when a single chunk covers several anchors, Recall credits every anchor but nDCG credits one
  result. Document this grouping limitation when comparing chunking configurations.
- Missing-result rate: all Gold questions without any result / all Gold questions.
- Query coverage: all Gold questions with at least one result / all Gold questions.

Unanswerable questions are excluded from Hit, Recall, MRR, and nDCG denominators and reported
separately. Per-language, per-category, and per-split metrics use the same rules. Workspace violations
are a separate hard security result and are never averaged into quality scores.
The security report records scoped and unchecked query counts; no scoped queries means
`not_evaluated`, not a pass. A partial scope check does not establish whole-dataset isolation.
Use `--require-workspace-scope` to require trusted scope metadata for every query, including explicit
empty-result records. Missing scope on a returned result is a violation. CLI evaluation writes the
report and returns exit code 1 on security violations; malformed inputs return exit code 2.

## Offline CLI

```bash
python -m doclens_ai.evaluation validate \
  --gold docs/evaluation/synthetic_retrieval_gold_fixture.jsonl \
  --json-output evaluation-output/validation.json

python -m doclens_ai.evaluation evaluate \
  --gold local-evaluation/retrieval_gold_v1.jsonl \
  --corpus-manifest docs/eda/corpus_v1_manifest.csv \
  --results local-evaluation/ranked_results.jsonl \
  --json-output evaluation-output/report.json
```

The CLI requires only local JSONL/CSV files. Reports contain aggregate metrics, question IDs only for
security violations, and deterministic content-derived fingerprints. They do not contain question
text, retrieved text, source paths, filenames, credentials, or runtime chunk UUIDs.

## Synthetic verification

The unit-test ranking fixture supplies results for three of the four synthetic queries. There are
three answerable queries and four positive evidence anchors. Tested values are Hit@5/10 = 2/3,
Recall@5 = 2/4, Recall@10 = 3/4, MRR = 0.5, nDCG@10 = 0.535086748018,
missing-result rate = 1/4, and query coverage = 3/4. One deliberately incorrect workspace produces
a separate security failure. Repeated reports and CLI JSON outputs are byte-identical; changing
runtime chunk IDs does not change the fingerprints. No real retrieval quality has been measured.
