# RAG Gold v1 protocol

Retrieval Gold evidence/relevance is insufficient to label generated answers. Do not relabel the
existing 48 reviewed English retrieval questions as reviewed RAG answers. No real answer Gold was
available for this step. Private JSONL belongs in ignored `local-evaluation/`, never Git.

## Frozen strict contract

Schema `rag-gold-1.0`; dataset revision `corpus-v1-rag-gold-v1` for real approved Corpus v1 or
`synthetic-rag-gold-v1` for mechanics fixtures. Each record has exactly:

- `schema_version`, `dataset_revision`, `synthetic_fixture`;
- opaque `question_id`, `document_family_id`, `split` (`dev`/`test`);
- `language` (`en`/`ru`/`kk`), `category` (fact/number/table/identifier/version/unanswerable);
- private `question`, strict boolean `answerable`;
- `source_document_sha256` (unique reviewed source identities, including negative judgment scope);
- `accepted_answers`, optional nullable `reference_answer` (both keys required);
- `evidence`, `required_citation_refs`;
- `reviewer_status`, `reviewer_count`.

Positive labels require accepted variants or a verified reference answer, nonempty evidence and
required citation references naming existing anchors. A negative requires no reference/accepted
answers, evidence or required citation references and category unanswerable. Each evidence anchor
has `evidence_id`, `document_sha256`, `document_format`, authoritative-format `locator`, normalized
`source_start`/`source_end` (exclusive), and a nonblank `verified_quote`. PDF needs a page, DOCX a
block, XLSX sheet index and cell/range/table. Offsets refer to extraction source units, not raw file
bytes or concatenated chunks. Questions/answers/quotes/worksheet names are private data.

Real records require reviewed status and at least one reviewer, or adjudicated status and at least
two. Draft/unreviewed/missing-answer/unsupported-reference labels are rejected. Approved manifest
source identity validation is mandatory. Review-status declarations are not automatic proof of
human work: the operator must provide genuine signed-off annotations and retain private review
provenance. Synthetic records use `fixture`, zero reviewers and explicit synthetic revision;
they cannot be presented as human-reviewed real annotations.

Families and every shared source SHA remain in one family/split, including cross-version and
multi-document questions. Questions are unique, revisions cannot mix. The whole normalized dataset
is SHA-256 fingerprinted, independent of input row order. Only that fingerprint and aggregate
metrics enter reports. Do not tune prompts/context budgets against held-out test labels.

## Human acquisition and verification

1. Verify approved corpus hashes, permissions and current extraction eligibility. Select diverse
   source formats, tables/numbers/identifiers, versions, languages and negative/ambiguous questions.
2. Review originals AND canonical normalized extraction. Confirm question answerability within a
   documented scope; record exact supporting quotes, source units/ranges and all required evidence.
3. Write concise verified reference answers and accepted variants, preserving numbers/units/version
   meaning. Do not use an unreviewed LLM answer to manufacture Gold. Check negative scope explicitly.
4. Independently review positives/negatives and adjudicate disagreement; preserve private reviewer
   identity/approval records. Validate family links and dev/test separation, then freeze revision/hash.
5. Run generation with fixed retrieval corpus/runtime/prompt/settings. Review the ACTUAL delivered
   answers, not just Gold or citations. Judge answer correctness, citation source support and every
   unsupported claim. Record uncertainty and all unreviewed outputs as NOT EVALUATED.

Optional private output review JSONL uses `OutputReview`: opaque question ID, dataset/experiment/output
fingerprints, reviewer status reviewed/adjudicated, boolean `answer_correct`, `supported_citations`,
`unsupported_claims`, `total_claims`. Fingerprints bind labels to the exact generated response
(excluding random request ID); counts cannot exceed delivered citations/claims. Generate those
fingerprints in the private review workflow using `output_fingerprint`, without committing output
text. Reusing labels across different model outputs/configurations is rejected. The runner accepts
`--reviews` only for real Gold. It does not manufacture reviews, export private answers or provide
a review UI in this step.

## Measurement interpretation

Normalized casefolded/whitespace-collapsed exact answer match is a restrictive lexical measure,
not semantic correctness. Accepted variants may require many legitimate phrasings; reference-only
match can undercount valid answers. Valid delivered citation/quote reference rates measure backend
gates, not factual grounding. Required-anchor coverage compares source SHA/format/locator/range and
verified quote within a delivered citation, not semantic implication. Human reviewed correctness,
source support and unsupported-claim rates have denominators limited to bound reviewed outputs.
Failure is not a successful refusal or a true negative: failures are counted separately, excluded
from answerability confusion, and included in latency. Precision/recall zero denominators are null.
Report dependency/model/retrieval failures, invalid model outputs, actual retrieval-empty counts,
refusal reasons and latency P50/P95 with startup separated. Never generalize EN-only results to RU/KK.
