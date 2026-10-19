# DocLens ML and RAG quality strategy

AVAILABLE LOCAL EDITORIAL SPECIFICATION, reconstructed 19 October 2026 from
architecture v3 §§8, 10–15, 23, the reconstruction brief and project skills.
Not a recovered historical original. Owns ML methodology; acceptance belongs to
[Quality Policy](DocLens_AI_Project_Goals_and_Quality_Policy-1.md#QUALITY-GATES).
Extraction methods belong to [Extraction Strategy](DocLens_AI_Extraction_Strategy.md);
GPU mechanics belong to [GPU Playbook](DocLens_AI_Kaggle_GPU_Playbook.md).

<a id="ML-DATA"></a>
## [ML-DATA] Data and reviewed Gold

Verify legal provenance, permitted use/transfer/annotation, sensitivity, immutable
RAW SHA-256/size/version manifests and source identities. EDA precedes model work:
report formats/languages/sizes, corrupt/unsupported sources, missingness, exact
duplicates, near-duplicates, versions and families. Do not discard meaningful
versions or infer rights from a matching hash. Private source/Gold stays local
unless explicitly authorized for a defined transfer.

Maintain distinct human-reviewed Extraction, Retrieval and Answer Gold. Draft
machine labels remain unreviewed until attested against originals; record reviewer,
adjudication, revision and unresolved judgments. Keep training separate from
evaluation. Split train/dev/sealed-test by family, including translations,
versions and near-duplicates. Record seed/split revision and review decisions.
No sealed-test tuning; exposed tests cannot be relabeled fresh blind evaluation.
Report RU/KK/EN, format and difficult/negative coverage under the quality policy.

<a id="ML-CHUNK"></a>
## [ML-CHUNK] Chunk evidence

Use the frozen structure-aware character baseline as comparator; architecture §8
records 1200 characters/120 overlap at its snapshot. These are baseline parameters,
not token budgets or proven optima; verify actual configuration for a new run.
Preserve facts, negation, identifiers, units, header/value links, table rows and
genuine locators. Token-aware and table/row-aware variants are candidates.

Measure complete Gold evidence-in-chunk, broken rows/relationships, duplicate
overlap, length/token distribution, latency and index size on fixed extraction/Gold.
Separate extraction loss from chunking loss. A relevant chunk ID alone does not
prove its text retains the complete supporting fact. Preserve deterministic
identity and configuration lineage under the architecture's persistence contract.

<a id="ML-RETRIEVAL"></a>
## [ML-RETRIEVAL] Embeddings and ranking

Repository baseline: `intfloat/multilingual-e5-small`, revision
`614241f622f53c4eeff9890bdc4f31cfecc418b3`, 384-dimensional normalized dense vectors.
The provider in `src/doclens_ai/dense_baseline/embeddings.py` defines artifact hashes
and configuration. Query/passage instructions, tokenizer, normalization and runtime
must match the indexed space. Verify loaded bytes; a model name is not provenance.
BM25 remains an offline lexical comparator; production lexical/hybrid integration
is not established. E5 is not a demonstrated general improvement over BM25.

Evaluate Hit/Recall@5,@10, MRR and nDCG@10 with documented ranking horizon/ties,
full attempted coverage and eligible denominators. Include numeric, multilingual,
cross-lingual, table and negative cases. Gold selects scoring/splits, never backend
candidate filters or context. Scope comparisons to identical authorized corpora
and upstream representations; do not conflate bounded production top-k with old
offline full-pool scores. Test tenant/freshness safety under architecture §§9–10, 16.
New embeddings/hybrid/rerankers require measured error analysis, complementary or
ranking need, paired gains and acceptable latency/resources before advancement.

<a id="ML-EVIDENCE"></a>
## [ML-EVIDENCE] Selection and packing

Trace complete reviewed evidence through discovery, retrieved chunk contents,
selection, deduplication and truncation into the actual serialized context.
Measure evidence-in-context and retrieved-to-packed survival, table/header/unit
retention, lost anchors, budget utilization and latency. Keep retrieved candidate
pools and generator fixed for packing A/B. Character caps are not tokenizer limits;
validate measured token use and output reserve against the selected model window.
The current runtime's score-order/prefix packing is a baseline, not proven optimal.
Never retrieve extra evidence using Gold labels to improve measured packing.

<a id="ML-GENERATION"></a>
## [ML-GENERATION] Grounded answers and refusal

Apply [truthful-answer requirements](DocLens_AI_Project_Goals_and_Quality_Policy-1.md#TRUTHFUL-LLM).
Evaluate factual correctness, groundedness, semantic citation support precision/recall,
unsupported claims and refusal precision/recall/F1 using independent reviewed
Answer Gold. Separate runtime/HTTP success, JSON/schema validity, source IDs,
quotes/offsets/coverage, semantic support and production release counts.
Invalid output is a contract failure, not a correct refusal; exact quotes do not
prove entailment. AI-assisted diagnostics are not independent human semantic review.

Include negation, wrong entity, conflicting sources, no-evidence, document injection,
cross-lingual and numeric probes. A document-scoped negative does not establish
workspace-wide unanswerability. Reauthorize all packed evidence after inference;
respect the architecture's residual final-check-to-delivery race. No external
sensitive inference without explicit authorization. Rejected model/configurations
remain rejected in their measured scope; no automatic validator weakening or
offline-binder production integration. Historical outcomes remain in primary reports.

<a id="ML-FINETUNE"></a>
## [ML-FINETUNE] Optional training

Do not train to memorize private document contents. LoRA/QLoRA needs evidence that
retrieval/context provide correct support while the base generator systematically
fails, plus error analysis and a separately authorized experiment. Require lawful,
reviewed SFT data excluding evaluation families, frozen base-model/configuration,
untuned held-out quality/safety checks and resource budgets. Public QA datasets are
not automatically document-RAG Gold or approved training data. No specific model,
rank, quantization or training sweep is selected by this strategy.

<a id="ML-EXPERIMENT"></a>
## [ML-EXPERIMENT] Reproducibility and decisions

Before execution, register one hypothesis/failure category and changed variable,
champion/candidate, immutable cohort/Gold/family splits, metrics/approved thresholds,
guardrails, stopping rules, resource budgets and comparison scope. Freeze Git SHA,
source/model artifact hashes, revisions, parser/chunker/prompt/packing configuration,
dependencies, seeds, hardware and concurrency. Freeze other stages or disclose
unavoidable differences. Use stage skills for execution and scoring details.

Retain every failed/needs_review attempt and excluded observation with reason;
report population coverage and conditional eligible quality separately. Unknown
measurements are not invented zeros. Pair comparable observations; reproduce new
comparisons and compare deterministic fields while retaining actual timings.
Report per-split/language/format/difficulty metrics, sample sizes and uncertainty,
P50/P95 latency, cold/startup versus steady inference, peak RAM/VRAM and failures.
State units, sampling/process-tree scope and missing resource observations.

PROMOTE means advancement only within the registered experimental scope;
REJECT follows failed guardrails, critical evidence/security regression or unsafe
accepted answers; INCONCLUSIVE means insufficient defensible comparative evidence.
Missing essential execution inputs means task BLOCKED. Gate verdicts are owned by
the quality policy; a completed experiment is not a release PASS. Production rollout
requires separate authorization, independent quality/security/operational gates,
rollback and recovery evidence. Do not automatically start the next experiment.
