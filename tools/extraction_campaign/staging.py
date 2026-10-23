"""Public model snapshots only: revision-bound, bounded downloads and file verification."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
import urllib.request
from pathlib import Path, PurePosixPath
from urllib.parse import quote

from tools.extraction_campaign.protocol import ROOT, sha, write_new


def safe_relative(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    if not name or "\\" in name or path.is_absolute() or any(p in {".", ".."} for p in path.parts):
        raise ValueError("model_path_rejected")
    if any(":" in p for p in path.parts):
        raise ValueError("model_path_rejected")
    return path


def metadata(url: str):
    with urllib.request.urlopen(url, timeout=30) as response:
        data = response.read(4 * 1024**2 + 1)
    if len(data) > 4 * 1024**2:
        raise ValueError("metadata_limit")
    return json.loads(data)


def get_file(
    url: str,
    output: Path,
    *,
    expected_size: int,
    expected_sha256: str | None,
    blob_id: str | None = None,
) -> dict:
    if output.exists():
        if output.stat().st_size != expected_size or (
            expected_sha256 and sha(output) != expected_sha256
        ):
            raise ValueError("existing_model_file_changed")
        if blob_id and not expected_sha256:
            existing_blob = hashlib.sha1(usedforsecurity=False)
            existing_blob.update(f"blob {expected_size}\0".encode())
            with output.open("rb") as stream:
                for block in iter(lambda: stream.read(1024**2), b""):
                    existing_blob.update(block)
            if existing_blob.hexdigest() != blob_id:
                raise ValueError("existing_git_blob_identity_mismatch")
        return {"sha256": sha(output), "size_bytes": expected_size, "reused": True}
    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_name(output.name + ".partial")
    if partial.exists():
        raise ValueError("partial_download_requires_new_explicit_attempt")
    started, count = time.monotonic(), 0
    h = hashlib.sha256()
    with urllib.request.urlopen(url, timeout=120) as response, partial.open("xb") as stream:
        while block := response.read(1024**2):
            count += len(block)
            if count > expected_size or time.monotonic() - started > 1200:
                raise ValueError("download_budget")
            h.update(block)
            stream.write(block)
    if count != expected_size or (expected_sha256 and h.hexdigest() != expected_sha256):
        raise ValueError("download_identity_mismatch")
    if blob_id and not expected_sha256:
        git_hash = hashlib.sha1(usedforsecurity=False)
        git_hash.update(f"blob {count}\0".encode())
        with partial.open("rb") as stream:
            for block in iter(lambda: stream.read(1024**2), b""):
                git_hash.update(block)
        if git_hash.hexdigest() != blob_id:
            raise ValueError("git_blob_identity_mismatch")
    partial.rename(output)
    return {
        "sha256": h.hexdigest(),
        "size_bytes": count,
        "download_seconds": time.monotonic() - started,
        "reused": False,
    }


def snapshot(
    repo: str,
    output: Path,
    *,
    revision: str | None = None,
    max_bytes: int = 4 * 1024**3,
    subfolder: str | None = None,
) -> dict:
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", repo):
        raise ValueError("public_model_repository_required")
    if revision and not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("exact_revision_required")
    if not output.resolve().is_relative_to(ROOT / "evaluation-output") or output.is_symlink():
        raise ValueError("private_model_staging_required")
    endpoint = "https://huggingface.co/api/models/" + repo
    if revision:
        endpoint += "/revision/" + revision
    data = metadata(endpoint + "?blobs=true")
    actual_revision = data["sha"]
    if revision and actual_revision != revision:
        raise ValueError("revision_mismatch")
    allowed = {
        ".json",
        ".safetensors",
        ".pdiparams",
        ".pdmodel",
        ".yml",
        ".yaml",
        ".pth",
        ".txt",
        ".model",
        ".jinja",
        ".py",
    }
    files = []
    for record in data["siblings"]:
        name = record["rfilename"]
        path = safe_relative(name)
        if subfolder and not name.startswith(subfolder.rstrip("/") + "/"):
            continue
        if path.suffix not in allowed and path.name != "LICENSE":
            continue
        if any(part.startswith(".") for part in path.parts):
            continue
        files.append(record)
    total = sum(f["size"] for f in files)
    if not files or total > max_bytes:
        raise ValueError("model_download_budget")
    registration = {
        "repo": repo,
        "revision": actual_revision,
        "license": data.get("cardData", {}).get("license"),
        "files": files,
        "total_bytes": total,
    }
    output.mkdir(parents=True, exist_ok=True)
    registered = output / ".registration.json"
    if registered.exists():
        if json.loads(registered.read_text()) != registration:
            raise ValueError("staging_registration_changed")
    else:
        write_new(registered, registration)
    results = {}
    for item in files:
        name = item["rfilename"]
        print(json.dumps({"staging_repo": repo, "file": name, "bytes": item["size"]}), flush=True)
        relative = name[len(subfolder) + 1 :] if subfolder else name
        results[relative] = get_file(
            "https://huggingface.co/" + repo + "/resolve/" + actual_revision + "/" + quote(name),
            output / relative,
            expected_size=item["size"],
            expected_sha256=(item.get("lfs") or {}).get("sha256"),
            blob_id=item.get("blobId"),
        )
    complete = output / ".complete.json"
    if not complete.exists():
        write_new(complete, {"repo": repo, "revision": actual_revision, "files": results})
    return {
        "repo": repo,
        "revision": actual_revision,
        "license": registration["license"],
        "files": len(results),
        "bytes": total,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--revision")
    parser.add_argument("--subfolder")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            snapshot(args.repo, args.output, revision=args.revision, subfolder=args.subfolder)
        )
    )


if __name__ == "__main__":
    main()
