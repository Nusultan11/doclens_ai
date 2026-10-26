# Blind review input/session lifecycle — 26 October 2026

Scope: `blind_review_batch.py`, its focused tests and this report. Branch `main`,
starting HEAD `a7afbfe1ff4c19bbd1e424e11ab4d7f8737fd26e`. No commit before review.
STATUS: PASS for this lifecycle fix and the verification below. Semantic quality
and independent human Gold remain NOT_EVALUATED.

The [original batch report](blind_extraction_review_batch_20261026.md),
[ML-DATA](../../DocLens_AI_ML_Quality_Strategy.md#ML-DATA),
[QG-00/QG-01](../../DocLens_AI_Project_Goals_and_Quality_Policy-1.md#QUALITY-GATES)
and existing PDF Workbench resume/binding contracts govern this change.

Reproduction: a synthetic Workbench accepted an unsigned draft save and page
inspection update. Reconstructing frozen inputs then failed with
`ValueError: PDF workspace is no longer a pristine blind draft`. The regression
test failed against the previous implementation before the fix. Both the
pristine-state requirement and the protected hash of mutable `workbench.json`
coupled input integrity to reviewer progress. The active packager code hash also
prevented verification of historical inputs after a code update.

The revised lifecycle has three distinct operations:

- `prepare`: require an intact packet, qualified originals and a pristine blind
  workspace at admission, then freeze blank original-only inputs. No existing
  workspace is initialized, reset or overwritten.
- `verify`: reconstruct blank inputs from immutable packet/source/rights/family
  bindings and compare exact artifact inventory, bytes and hashes. Do not read,
  hash, resume or require the mutable workspace. This verdict concerns inputs.
- `verify-session`: first verify inputs, then use existing Workbench resume,
  source/binding, locator, seal/snapshot and review validators for the separate
  mutable workspace. Reject unsealed completed-review claims, declared prior
  prediction/legacy exposure and machine proposal sidecars. Report resumability;
  review acceptance remains NOT_EVALUATED. Mutable and frozen directories may
  not overlap.

Existing `preflight`, rights eligibility, source assets, connected-family rules,
source pages, blank worksheets and Workbench resume validation are reused.
The immutable packet adapter retains `Workbench._verify_bundle`'s exact inventory,
source identity, completion marker and digest checks without resuming live state.
No Workbench implementation, production parser or Gold contract was modified.

New outputs use **`blind-extraction-review-batch-2`** and pin immutable PDF packet
manifest/completion records instead of a mutable workspace file. Selection,
Office worksheet version fields and instructions identify the new contract.

The historical **directory v3** retains stored contract version 1. Verification
reconstructs its original pristine workspace digest from immutable inputs and
checks the recorded producer hash against the accepted version-1 implementation
(`a29e64153abd5043d6cf2ad6353f0d4b90ba454e48157ead4fc4021834ed5eb0`).
These two historical provenance pins are not compared to mutable workspace or
active code bytes. They are not removed or replaced. All other original pins and
strict reconstruction checks still apply. No legacy code is executed, no v3
manifest is resealed, and unknown/relabelled producer or initial-workspace pins
are rejected.

Historical v3 fingerprint remains:
`cd6db1ad5a80c11d6a2ce1135cb1bf00eee19eb89af53a190613d8d451cf80c9`.
The original batch report and v3/reproduction artifacts remain unchanged.

Commands executed from the repository root:

```powershell
$env:PYTHONPATH=(Get-Location).Path
# Before implementation: expected failure, one regression failed.
.venv/Scripts/python.exe -B -m pytest tests/unit/test_blind_review_batch.py::test_frozen_pdf_inputs_survive_valid_annotation -q --tb=short -p no:cacheprovider --basetemp=evaluation-output/blind-lifecycle-repro
# Final lifecycle + existing PDF contracts; HTTP tests require local loopback.
.venv/Scripts/python.exe -B -m pytest tests/unit/test_blind_review_batch.py tests/unit/test_pdf_review_eligibility.py tests/unit/test_pdf_table_review_packet.py tests/unit/test_pdf_review_workbench.py tests/unit/test_ml28_review.py -q --tb=short --strict-config --strict-markers -p no:cacheprovider --basetemp=evaluation-output/blind-lifecycle-tests-final --junitxml=evaluation-output/blind-lifecycle-tests-final.xml
.venv/Scripts/python.exe -B -m tools.extraction_quality.blind_review_batch verify --output evaluation-output/blind-extraction-review-20261026-v3
.venv/Scripts/python.exe -B evaluation-output/blind-lifecycle-20261026/verify_lifecycle.py
.venv/Scripts/python.exe -m ruff check tools/extraction_quality/blind_review_batch.py tests/unit/test_blind_review_batch.py
.venv/Scripts/python.exe -m ruff format --check tools/extraction_quality/blind_review_batch.py tests/unit/test_blind_review_batch.py
git diff --check
git diff --stat
git diff --cached --stat
git status --short
```

Coverage includes valid partial/inspected/sealed/revealed synthetic sessions;
changed RAW, rights, family, packet and frozen PDF/Office locators; forged review
fields and unsealed completion; prediction/legacy leakage; wrong session binding;
missing/truncated session JSON; and interrupted atomic save retaining the last
valid session. Frozen inputs remain valid when mutable work is missing or corrupt,
while session validation fails. Existing wrong-SHA, family-isolation, hidden
exclusion, duplicate JSON and deterministic reproduction tests remain in place.

The private audit uses a separate copy of the existing workspace for an unsigned
diagnostic draft save. It adds no human identity, inspection attestation, signature
or Gold. It verifies v3 with guards prohibiting any read/hash of live workspace
state, builds two new contract-2 copies, checks deterministic bytes, and tests
interrupted mutable state separately. Originals, rights evidence and historical
artifacts remain local and unmodified.

Final results: **165 passed, zero failed/skipped, 100.94 seconds**. Ruff check,
format check and `git diff --check` passed; staged diff is empty. The earlier
expanded focused run passed 59 tests before the final two negative cases were
added. The reproduction failure above is expected pre-fix evidence, not an
unresolved failure. The final existing HTTP tests ran with local loopback access.

The audit verified the unchanged v3 fingerprint above and **30 preservation
hashes**, covering both historical v3 copies, the original report, original live
workspace and four unrelated evaluation reports. Changed-RAW/rights and Gold
protection is also enforced through the recursively verified readiness release
and PDF preflight. The original Kaggle file remains deleted and unstaged.

Two new contract-2 copies under ignored
`evaluation-output/blind-extraction-review-20261026-lifecycle-v2/{batch,replica}`
have **12 byte-identical files**, including their manifests, and fingerprint
`e5f1b6068df3738539e11917f05ffe8fbf93ec4c4c0ec496638e7f49590ab274`.
The historical v3 verifier succeeded while guards prohibited live-workspace
reads/hashing. The copied unsigned session remained RESUMABLE after a draft save;
truncated session state was BLOCKED as expected while input verification passed.
No human reviews were created. Private evidence is in
`evaluation-output/blind-lifecycle-20261026/{before,verification}.json` and
`evaluation-output/blind-lifecycle-tests-final.xml`.

Remaining boundaries: actual human review and adjudication are still required.
Schema/resumability checks do not authenticate reviewer identity or establish
semantic quality, independent Gold or production readiness. Preparation after
annotation has begun remains intentionally blocked; verify the already frozen
batch and resume the existing session instead.

COMMIT: Not created; review required. Unrelated Kaggle deletion and four existing
`docs/evaluation` files are untouched and unstaged.

Final `git status --short`:

```text
 M tests/unit/test_blind_review_batch.py
 M tools/extraction_quality/blind_review_batch.py
 D tools/kaggle_gpu/extraction_remote.py
?? docs/eda/blind_review_lifecycle_20261026.md
?? docs/evaluation/final_qg_qualification_20261024.md
?? docs/evaluation/final_qg_qualification_20261024_evidence.json
?? docs/evaluation/qg_qualification_20261024.md
?? docs/evaluation/qg_qualification_20261024_evidence.json
```
