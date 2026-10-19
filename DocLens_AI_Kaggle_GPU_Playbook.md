# DocLens AI — Kaggle GPU playbook v4

19.10.2026. Владелец только временного явно разрешённого GPU execution.
[ML protocol](DocLens_AI_ML_Quality_Strategy.md#ML-EXPERIMENT) определяет experiment;
[Quality Policy](DocLens_AI_Project_Goals_and_Quality_Policy-1.md) — acceptance.
Документ не разрешает cloud run/transfer. Команды поддерживает
[runner guide](tools/kaggle_gpu/README.md), процедура —
[GPU skill](.agents/skills/doclens-kaggle-gpu/SKILL.md).

<a id="GPU-MODE"></a>
## Границы и preflight

Backend/API/DB/migrations/Docker остаются локальными; Kaggle не production hosting.
До submission определить workload authorization, hardware/concurrency, quotas/cost,
duration/storage/resource limits, allowed inputs/outputs/stopping rules.
Проверить actual account/CLI/runtime/devices; account IDs/remote connection не подразумеваются.

Staging — точный allowlist source/public assets с hashes; credentials вне Git/logs.
Private RAW/Gold/prompts/embeddings требуют explicit transfer scope, recipients,
privacy/retention review. Private visibility не заменяет authorization.
Проверить exact files/collaborators/visibility перед transfer; repository glob и
production mount запрещены.

<a id="GPU-A"></a>
## Mode A: interactive

Official notebook либо supported verified editor connection; не предполагать remote
VS Code и не открывать unauthenticated server/tunnel. Сохранить final code/cell order,
input/model/config/source revisions, dependencies/seeds/device placement.
Clean restart/run frozen workflow; out-of-order state не воспроизводим.
Экспортировать sanitized logs/JSON/CSV с run identity/failures.

<a id="GPU-B"></a>
## Mode B: versioned CLI

Использовать runner guide, сверив `kaggle --version` и subcommand help.
Только разрешённые notebook IDs; frozen staged hashes/metadata/model bytes/inputs.
Зафиксировать submission/version ID, дождаться terminal status, получить именно его
logs/artifacts; stale/mismatched outputs отклонять. Сохранить failed submissions,
queue/startup/inference time/errors. Bounded retries без overlapping submissions
или selective retries вне preregistered protocol. Cleanup только owned temporary
resources после сохранения evidence, не shared datasets/source originals.

<a id="GPU-GATE"></a>
## CUDA, provenance и результат

Записать actual devices/model/count/placement/offload, driver/CUDA/framework,
loaded artifact hashes/revisions/runtime/config/input identities.
Доказать actual CUDA computation/model-layer offload; enumeration/allocation,
download/submission/HTTP 200 не доказывают inference. Silent CPU/model fallback запрещён.
Две T4 не образуют автоматически единое 32 GB VRAM address space.

Измерять cold load/startup отдельно от steady/total; P50/P95 при достаточной выборке,
peak device VRAM/host RAM с units/sampling/process scope/concurrency/timeouts/failures.
Unavailable measurements — UNKNOWN/NOT_EVALUATED. Execution PASS требует completed
workload, matching provenance/CUDA, inspected logs/expected valid artifacts;
missing essential provenance/runtime блокирует PASS. JSON/CSV отдельно показывают
execution/stage quality. GPU execution не даёт model promotion/production authorization.
