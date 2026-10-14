"""Docker exclusion policy; optional real BuildKit probe uses synthetic files ONLY.

Run the probe separately: python tests/unit/test_dockerignore.py --verify-buildkit
Unit tests deliberately do not emulate Docker's matcher or require a Docker daemon.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PRIVATE_DIRECTORIES = (
    "local-corpus",
    "local-evaluation",
    "evaluation-output",
    "eda-output",
    ".eda-output",
    "reports/eda",
    "extraction-output",
    ".extraction-output",
    "chunking-output",
    ".chunking-output",
    "reports/extraction",
    "reports/chunking",
)
# ROOT-only names: never exclude the business-domain src/doclens_ai/models package.
MODEL_DIRECTORIES = (
    "models",
    "model-weights",
    "weights",
    "checkpoints",
    "hf-cache",
    ".huggingface",
)
MODEL_PATTERNS = (
    "**/.cache/huggingface",
    "**/*.safetensors",
    "**/*.gguf",
    "**/*.ggml",
    "**/*.ckpt",
    "**/*.pt",
    "**/*.pth",
    "**/*.onnx",
    "**/pytorch_model*.bin",
    "**/adapter_model*.bin",
)
TEMP_PATTERNS = (
    "tmp",
    "temp",
    ".tmp",
    "**/*.tmp",
    "**/*.bak",
    "**/*.log",
    "**/.DS_Store",
    "**/Thumbs.db",
)
REQUIRED_SENTINELS = (
    "pyproject.toml",
    "README.md",
    "alembic.ini",
    ".env.example",
    "src/doclens_ai/__init__.py",
    "src/doclens_ai/main.py",
    "src/doclens_ai/models/document.py",
    "src/doclens_ai/extraction/parsers.py",
    "src/doclens_ai/chunking/core.py",
    "src/doclens_ai/dense_baseline/embeddings.py",
    "alembic/env.py",
    "alembic/versions/0001_fixture.py",
    "src/doclens_ai/config.json",
    "src/doclens_ai/data/example.txt",
)
PRIVATE_SENTINELS = (
    *(f"{directory}/synthetic-only.txt" for directory in PRIVATE_DIRECTORIES),
    *(f"nested/project/{directory}/synthetic-only.txt" for directory in PRIVATE_DIRECTORIES),
    *(f"{directory}/synthetic-only.txt" for directory in MODEL_DIRECTORIES),
    "local-corpus/pdf/source.pdf",
    "local-corpus/docx/source.docx",
    "local-corpus/xlsx/source.xlsx",
    "local-evaluation/retrieval_gold_v1.jsonl",
    "local-evaluation/rag_gold_v1.jsonl",
    "evaluation-output/dense-v1-model/model.safetensors",
    "evaluation-output/extraction/extracted.txt",
    "evaluation-output/chunking/chunks.json",
    ".cache/huggingface/fixture/config.json",
    "nested/.cache/huggingface/fixture/tokenizer.json",
    "nested/artifacts/model.safetensors",
    "nested/artifacts/model.gguf",
    "nested/artifacts/model.ggml",
    "nested/artifacts/model.ckpt",
    "nested/artifacts/model.pt",
    "nested/artifacts/model.pth",
    "nested/artifacts/model.onnx",
    "nested/artifacts/pytorch_model.bin",
    "nested/artifacts/pytorch_model-00001-of-00002.bin",
    "nested/artifacts/adapter_model.bin",
    "tmp/fixture.txt",
    "temp/fixture.txt",
    ".tmp/fixture.txt",
    "nested/output.tmp",
    "nested/output.bak",
    "nested/output.log",
    "nested/.DS_Store",
    "nested/Thumbs.db",
    ".env",
    ".env.private",
    ".git/fixture.txt",
    ".venv/fixture.txt",
    "tests/fixture.py",
    "__pycache__/fixture.pyc",
)


def rules():
    return tuple(
        line.strip()
        for line in (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )


@pytest.mark.parametrize("directory", PRIVATE_DIRECTORIES)
def test_private_and_generated_directories_are_excluded_recursively(directory):
    assert f"**/{directory}" in rules()


@pytest.mark.parametrize("pattern", (*MODEL_DIRECTORIES, *MODEL_PATTERNS, *TEMP_PATTERNS))
def test_model_and_temporary_artifact_patterns(pattern):
    assert pattern in rules()


def test_git_private_directory_contract_is_covered():
    git_rules = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    known = {
        "local-corpus",
        "local-evaluation",
        "evaluation-output",
        "eda-output",
        ".eda-output",
        "reports/eda",
    }
    assert known <= {line.rstrip("/") for line in git_rules}
    assert {"**/" + directory for directory in known} <= set(rules())


def test_required_copy_roots_and_business_models_are_not_excluded():
    policy = set(rules())
    # Guard against broad denial rules; actual matching is tested by BuildKit below, not fnmatch.
    for name in ("src", "alembic", "pyproject.toml", "README.md", "alembic.ini"):
        assert not {name, name + "/", name + "/**", "**/" + name} & policy
    assert (
        not {
            "*",
            "**",
            "**/*",
            "**/models",
            "**/models/**",
            "**/*.py",
            "**/*.json",
            "**/*.txt",
            "**/*.bin",
        }
        & policy
    )
    assert "!.env.example" in policy
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    for instruction in (
        "COPY pyproject.toml README.md alembic.ini ./",
        "COPY src ./src",
        "COPY alembic ./alembic",
    ):
        assert instruction in dockerfile


def test_no_later_negation_can_reinclude_private_artifacts():
    assert tuple(rule for rule in rules() if rule.startswith("!")) == ("!.env.example",)


def test_model_mounts_are_independent_read_only_runtime_inputs():
    for name in ("compose.yaml", "compose.search.yaml"):
        compose = (ROOT / name).read_text(encoding="utf-8")
        assert "source: ${DOCLENS_E5_MODEL_DIR:-./evaluation-output/dense-v1-model}" in compose
        assert "target: /models/e5" in compose
        assert "read_only: true" in compose
        assert "create_host_path: false" in compose


def verify_buildkit_context():
    """Export COPY . from a disposable scratch build, checking only synthetic sentinels.

    Never build this probe against ROOT; no repository/private file is copied into its context.
    Only current .dockerignore text and generated marker files are used. No image/dependency pull.
    TemporaryDirectory cleans up its own unique context and exported synthetic files.
    """
    with tempfile.TemporaryDirectory(prefix="doclens-dockerignore-") as temporary:
        task_root = Path(temporary).resolve()
        context, output = task_root / "context", task_root / "export"
        context.mkdir()
        (context / ".dockerignore").write_text(
            (ROOT / ".dockerignore").read_text(encoding="utf-8"), encoding="utf-8"
        )
        for name in (*REQUIRED_SENTINELS, *PRIVATE_SENTINELS):
            target = context / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("synthetic-sentinel-only\n", encoding="utf-8")
        subprocess.run(
            [
                "docker",
                "buildx",
                "build",
                "--progress=plain",
                "--no-cache",
                "--output",
                f"type=local,dest={output}",
                "--file",
                "-",
                str(context),
            ],
            input="FROM scratch\nCOPY . /context/\n",
            text=True,
            check=True,
        )
        copied = output / "context"
        leaked = [name for name in PRIVATE_SENTINELS if (copied / name).exists()]
        missing = [name for name in REQUIRED_SENTINELS if not (copied / name).is_file()]
        result = {
            "private_sentinel_count": len(PRIVATE_SENTINELS),
            "required_sentinel_count": len(REQUIRED_SENTINELS),
            "leaked": leaked,
            "missing_required": missing,
            "passed": not leaked and not missing,
        }
        print(json.dumps(result, sort_keys=True))
        return result["passed"]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-buildkit", action="store_true", required=True)
    parser.parse_args()
    raise SystemExit(0 if verify_buildkit_context() else 1)
