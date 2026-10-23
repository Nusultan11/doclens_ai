"""Standalone, synthetic-only extraction R0. Each submission selects one candidate.

Only this reviewed script is uploaded. Models/packages come from public registries.
No production imports, original documents, or Gold are accessible remotely.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import platform
import signal
import subprocess
import sys
import time
import traceback
from datetime import UTC, datetime
from fnmatch import fnmatchcase
from pathlib import Path

CONFIG = {}  # Replaced exactly once by the local explicit staging builder.


def sha(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=True) + "\n")


def synthetic_pdf(lines):
    """Deterministic born-digital PDF, no labels inferred from model output."""
    content = "BT /F1 14 Tf\n"
    for index, line in enumerate(lines):
        escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        content += f"1 0 0 1 50 {750 - index * 32} Tm ({escaped}) Tj\n"
    content += "ET\n"
    stream = content.encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"endstream",
    ]
    data = b"%PDF-1.4\n"
    offsets = [0]
    for i, item in enumerate(objects, 1):
        offsets.append(len(data))
        data += f"{i} 0 obj\n".encode() + item + b"\nendobj\n"
    start = len(data)
    data += f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode()
    data += b"".join(f"{n:010d} 00000 n \n".encode() for n in offsets[1:])
    return (
        data
        + f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n".encode()
    )


CASES = {
    "synthetic-prose": [
        "Synthetic extraction control",
        "Orion research note.",
        "Batch ID: ORION-2048",
    ],
    "synthetic-numbers": [
        "Synthetic numeric control",
        "Quantity: 17",
        "Balance: -12.50",
        "Code: 0042",
    ],
    "synthetic-rows": [
        "Synthetic aligned rows",
        "Item               Count               Cost",
        "Alpha              3                   12.50",
        "Beta               7                   21.00",
    ],
}


def public_snapshot(repo, revision, destination, patterns):
    from huggingface_hub import snapshot_download

    snapshot_download(
        repo_id=repo,
        revision=revision,
        local_dir=destination,
        allow_patterns=patterns,
        max_workers=2,
    )
    files = {
        p.relative_to(destination).as_posix(): sha(p)
        for p in Path(destination).rglob("*")
        if p.is_file() and ".cache" not in p.parts
    }
    if not files:
        raise RuntimeError("empty_public_snapshot")
    return {"directory": str(destination), "repo": repo, "revision": revision, "files": files}


def docling_prepare(root):
    models = Path("/tmp/extraction-models")
    inventory = []
    inventory.append(
        public_snapshot(
            "ds4sd/docling-layout-heron",
            "8f39ad3c0b4c58e9c2d2c84a38465abf757272d8",
            models / "ds4sd--docling-layout-heron",
            ["config.json", "preprocessor_config.json", "model.safetensors"],
        )
    )
    inventory.append(
        public_snapshot(
            "ds4sd/docling-models",
            "fc0f2d45e2218ea24bce5045f58a389aed16dc23",
            models / "ds4sd--docling-models",
            ["model_artifacts/tableformer/fast/*"],
        )
    )
    return inventory


def docling_extract(root, source, destination):
    import torch
    from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
    from docling.document_converter import DocumentConverter, PdfFormatOption

    torch.manual_seed(0)
    options = PdfPipelineOptions(
        artifacts_path=Path("/tmp/extraction-models"),
        do_ocr=False,
        do_table_structure=True,
        enable_remote_services=False,
        allow_external_plugins=False,
        do_code_enrichment=False,
        do_formula_enrichment=False,
        do_picture_description=False,
        do_picture_classification=False,
        document_timeout=600,
        accelerator_options=AcceleratorOptions(device=AcceleratorDevice.CPU, num_threads=2),
    )
    options.table_structure_options.mode = TableFormerMode.FAST
    options.table_structure_options.do_cell_matching = True
    write(destination / "effective-options.json", options.model_dump(mode="json"))
    start = time.monotonic()
    converter = DocumentConverter(
        allowed_formats=[InputFormat.PDF],
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)},
    )
    initialized = time.monotonic()
    result = converter.convert(source)
    elapsed = time.monotonic() - initialized
    write(destination / "native.json", result.document.export_to_dict())
    write(destination / "pages.json", [p.model_dump(mode="json") for p in result.pages])
    write(
        destination / "conversion.json",
        result.model_dump(mode="json", exclude={"input", "pages", "document"}),
    )
    return {
        "native_status": result.status.value,
        "constructor_seconds": initialized - start,
        "conversion_seconds_including_lazy_load": elapsed,
        "device": "cpu",
    }


def pinned_prepare(root):
    inventory = []
    for asset in CONFIG["assets"]:
        destination = Path("/tmp/extraction-models") / asset["name"]
        record = public_snapshot(asset["repo"], asset["revision"], destination, asset["patterns"])
        for name, expected in asset["sha256"].items():
            if not any(fnmatchcase(name, pattern) for pattern in asset["patterns"]):
                continue
            if name not in record["files"]:
                raise RuntimeError("missing_pinned_public_weight")
            if record["files"][name] != expected:
                raise RuntimeError("public_weight_checksum_mismatch")
        inventory.append(record)
    return inventory


def marker_prepare(root):
    import tarfile

    import requests

    inventory = pinned_prepare(root)
    folder = Path("/tmp/extraction-models/ocr-error")
    folder.mkdir(parents=True)
    base = "https://models.datalab.to/ocr_error_detection/2025_02_18/"
    # Match the vendor's requests-based downloader. The same public endpoint
    # returned 403 to urllib but 200 to requests in the reproduced acquisition bug.
    with requests.get(base + "manifest.json", timeout=30) as response:
        response.raise_for_status()
        manifest = response.json()
    for name in manifest["files"]:
        if Path(name).name != name:
            raise ValueError("unsafe_vendor_asset_name")
        with (
            requests.get(base + name, timeout=120, stream=True) as response,
            (folder / name).open("wb") as out,
        ):
            response.raise_for_status()
            total = 0
            for chunk in response.iter_content(1024**2):
                total += len(chunk)
                if total > 512 * 1024**2:
                    raise ValueError("public_asset_limit")
                out.write(chunk)
    inventory.append(
        {
            "directory": str(folder),
            "dated_source": base,
            "files": {p.name: sha(p) for p in folder.iterdir()},
        }
    )
    # BaseConverter downloads this font even for PDF-only JSON output. Stage it
    # explicitly before inference, with the verified public artifact identity.
    font_folder = Path("/tmp/extraction-models/render-font")
    font_folder.mkdir()
    font = font_folder / "GoNotoCurrent-Regular.ttf"
    with (
        requests.get(
            "https://models.datalab.to/artifacts/" + font.name, timeout=120, stream=True
        ) as response,
        font.open("wb") as out,
    ):
        response.raise_for_status()
        total = 0
        for chunk in response.iter_content(1024**2):
            total += len(chunk)
            if total > 100 * 1024**2:
                raise ValueError("font_size_limit")
            out.write(chunk)
    if sha(font) != CONFIG["font_sha256"]:
        raise ValueError("font_checksum_mismatch")
    if {p.name: sha(p) for p in folder.iterdir()} != CONFIG["ocr_error_sha256"]:
        raise ValueError("ocr_error_checksum_mismatch")
    inventory.append({"directory": str(font_folder), "files": {font.name: sha(font)}})
    archive = Path("/tmp/llama-runtime.tar.gz")
    url = "https://github.com/ggml-org/llama.cpp/releases/download/b11617/llama-b11617-bin-ubuntu-cuda-12.8-x64.tar.gz"
    with requests.get(url, timeout=120, stream=True) as response, archive.open("wb") as out:
        response.raise_for_status()
        total = 0
        for chunk in response.iter_content(1024**2):
            total += len(chunk)
            if total > 171623026:
                raise ValueError("runtime_size_limit")
            out.write(chunk)
    if sha(archive) != "1c5024dfa587a3f23ef8fc066cb2578fb43d661910d4111a8941184773c237d1":
        raise ValueError("runtime_checksum_mismatch")
    with tarfile.open(archive) as package:
        package.extractall("/tmp/llama-runtime", filter="data")
    runtime = Path("/tmp/llama-runtime")
    inventory.append(
        {
            "directory": str(runtime),
            "runtime": "llama.cpp-b11617",
            "sha256": sha(archive),
            "files": {
                p.relative_to(runtime).as_posix(): sha(p) for p in runtime.rglob("*") if p.is_file()
            },
        }
    )
    return inventory


def marker_extract(root, source, destination):
    import shutil

    profile = Path("/tmp/extraction-profiles") / destination.name
    profile.mkdir(parents=True)
    os.environ.update(
        HOME=str(profile),
        SURYA_INFERENCE_BACKEND="llamacpp",
        SURYA_INFERENCE_PARALLEL="1",
        SURYA_INFERENCE_KEEP_ALIVE="false",
        SURYA_INFERENCE_STARTUP_TIMEOUT="120",
        TORCH_DEVICE="cpu",
        FAST_DETECTOR_DEVICE="cpu",
        FAST_LAYOUT_NUM_THREADS="2",
        LLAMA_CPP_BINARY="/tmp/llama-runtime/llama-b11617/llama-server",
        LLAMA_CPP_EXTRA_ARGS="--seed 0 -lv 5",
        SURYA_GGUF_LOCAL_MODEL_PATH="/tmp/extraction-models/surya-ocr-2-gguf/surya-2.gguf",
        SURYA_GGUF_LOCAL_MMPROJ_PATH="/tmp/extraction-models/surya-ocr-2-gguf/surya-2-mmproj.gguf",
        OCR_ERROR_MODEL_CHECKPOINT="/tmp/extraction-models/ocr-error",
        FONT_PATH="/tmp/extraction-models/render-font/GoNotoCurrent-Regular.ttf",
        FAST_LAYOUT_MODEL_CHECKPOINT="/tmp/extraction-models/surya_layout2",
        FAST_ORDER_MODEL_CHECKPOINT="/tmp/extraction-models/surya_layout2/order",
    )
    libraries = list(Path("/usr/local/lib/python3.13/dist-packages/nvidia").glob("*/lib"))
    os.environ["LD_LIBRARY_PATH"] = ":".join(
        [
            os.environ.get("LD_LIBRARY_PATH", ""),
            "/usr/local/nvidia/lib64",
            "/tmp/llama-runtime/llama-b11617",
            *map(str, libraries),
        ]
    )
    from marker.converters.pdf import PdfConverter
    from marker.models import create_model_dict, shutdown_models

    config = {"mode": "balanced", "use_llm": False, "disable_ocr": False}
    write(destination / "effective-options.json", config)
    models = create_model_dict(inference_backend="llamacpp")
    start = time.monotonic()
    try:
        converter = PdfConverter(
            artifact_dict=models, renderer="marker.renderers.json.JSONRenderer", config=config
        )
        result = converter(str(source))
        write(destination / "native.json", result.model_dump(mode="json"))
        elapsed = time.monotonic() - start
    finally:
        shutdown_models(models)
        for log in profile.rglob("*.log"):
            shutil.copyfile(log, destination / log.name)
    import re

    server_log = (destination / "llamacpp_server.log").read_text(errors="replace")
    offload = re.search(r"offloaded\s+([1-9][0-9]*)/[0-9]+\s+layers to GPU", server_log)
    if not offload or "CUDA0" not in server_log:
        raise RuntimeError("marker_cuda_offload_unverified")
    return {
        "native_status": "completed",
        "conversion_seconds": elapsed,
        "device": "llama.cpp CUDA0",
        "offloaded_layers": int(offload.group(1)),
    }


def paddle_extract(root, source, destination):
    os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
    import paddle
    import paddlex
    import yaml
    from paddleocr import PaddleOCRVL, PPStructureV3

    paddle.seed(0)
    pipeline = "PP-StructureV3" if CONFIG["candidate"] == "ppstructure" else "PaddleOCR-VL-1.6"
    path = Path(paddlex.__file__).parent / "configs/pipelines" / (pipeline + ".yaml")
    config = yaml.safe_load(path.read_text())
    names = {a["name"] for a in CONFIG["assets"]}

    def bind(node):
        if isinstance(node, dict):
            if node.get("model_name") in names:
                node["model_dir"] = "/tmp/extraction-models/" + node["model_name"]
            if node.get("model_name") == "PaddleOCR-VL-1.6-0.9B":
                node["model_dir"] = "/tmp/extraction-models/PaddleOCR-VL-1.6"
            if "batch_size" in node:
                node["batch_size"] = 1
            for item in node.values():
                bind(item)
        elif isinstance(node, list):
            for item in node:
                bind(item)

    bind(config)
    config["use_queues"] = False
    write(destination / "effective-options.json", config)
    common_options = {
        "device": "cpu",
        "cpu_threads": 2,
        "enable_mkldnn": CONFIG.get("enable_mkldnn", True),
    }
    write(destination / "engine-options.json", common_options)
    start = time.monotonic()
    if CONFIG["candidate"] == "ppstructure":
        engine = PPStructureV3(
            paddlex_config=config,
            **common_options,
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
        )
    else:
        engine = PaddleOCRVL(
            paddlex_config=config,
            pipeline_version="v1.6",
            **common_options,
            use_queues=False,
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
        )
    initialized = time.monotonic()
    pages = 0
    for result in engine.predict(str(source)):
        result.save_to_json(str(destination / f"page-{pages}.json"))
        pages += 1
    return {
        "native_status": "completed",
        "pages": pages,
        "device": paddle.device.get_device(),
        "constructor_seconds": initialized - start,
        "conversion_seconds": time.monotonic() - initialized,
    }


def initialize_cuda(torch):
    if not torch.cuda.is_available():
        raise RuntimeError("required_cuda_unavailable")
    # reset_peak_memory_stats does not initialize a CUDA context in Torch 2.8.
    torch.cuda.init()
    torch.cuda.set_device(0)
    torch.cuda.reset_peak_memory_stats(0)


def mineru_extract(root, source, destination):
    """Official full-PDF workflow, with the exact requested checkpoint."""
    os.environ.update(MINERU_DEVICE_MODE="cuda", MINERU_MODEL_SOURCE="local")
    import torch
    from mineru.cli.common import do_parse
    from mineru_vl_utils import MinerUClient
    from transformers import AutoProcessor, Qwen2VLForConditionalGeneration

    torch.manual_seed(0)
    initialize_cuda(torch)
    write(
        destination / "cuda-initialization.json",
        {
            "torch": str(torch.__version__),
            "cuda": torch.version.cuda,
            "device": 0,
            "name": torch.cuda.get_device_name(0),
            "vram_bytes": torch.cuda.get_device_properties(0).total_memory,
            "bf16_supported": torch.cuda.is_bf16_supported(including_emulation=False),
        },
    )
    config = {
        "backend": "vlm-transformers",
        "batch_size": 1,
        "model_path": "/tmp/extraction-models/MinerU2.5-Pro-2604-1.2B",
        "formula_enable": True,
        "table_enable": True,
        "dtype": "float16",
    }
    write(destination / "effective-options.json", config)
    started = time.monotonic()
    # T4 (CC 7.5) has no native BF16. Use the supported predictor injection point
    # of the full PDF workflow, retaining the exact checkpoint bytes and processor.
    model = Qwen2VLForConditionalGeneration.from_pretrained(
        config["model_path"], dtype=torch.float16, device_map={"": "cuda:0"}, local_files_only=True
    )
    processor = AutoProcessor.from_pretrained(
        config["model_path"], use_fast=True, local_files_only=True
    )
    predictor = MinerUClient("transformers", model=model, processor=processor, batch_size=1)
    initialized = time.monotonic()
    # Version-verified MinerUClient -> TransformersVlmClient -> actual loaded model.
    modules = [predictor.client.model]
    if not all(isinstance(module, torch.nn.Module) for module in modules):
        raise RuntimeError("unexpected_mineru_client_model")
    proof = {"cuda_forward_calls": 0, "parameters": []}
    hooks = []

    def observe(_module, _arguments, result):
        def has_cuda(value):
            if isinstance(value, torch.Tensor):
                return value.is_cuda
            if isinstance(value, dict):
                return any(has_cuda(v) for v in value.values())
            if isinstance(value, (list, tuple)):
                return any(has_cuda(v) for v in value)
            return False

        if has_cuda(result):
            proof["cuda_forward_calls"] += 1

    for module in modules:
        proof["parameters"].append(
            sorted({str(p.device) + ":" + str(p.dtype) for p in module.parameters()})
        )
        hooks.append(module.register_forward_hook(observe))
    try:
        do_parse(
            str(destination),
            [source.stem],
            [source.read_bytes()],
            ["en"],
            backend="vlm-transformers",
            model_path=config["model_path"],
            batch_size=1,
            predictor=predictor,
            f_dump_model_output=True,
            f_dump_middle_json=True,
            f_dump_content_list=True,
            f_draw_layout_bbox=False,
            f_draw_span_bbox=False,
            f_dump_orig_pdf=False,
        )
    finally:
        for hook in hooks:
            hook.remove()
        proof["peak_cuda_allocated_bytes"] = torch.cuda.max_memory_allocated(0)
        write(destination / "cuda-proof.json", proof)
    if proof["cuda_forward_calls"] == 0:
        raise RuntimeError("actual_cuda_model_computation_unverified")
    return {
        "native_status": "completed",
        "device": "cuda:0",
        "constructor_seconds": initialized - started,
        "conversion_seconds": time.monotonic() - initialized,
        **proof,
    }


def child(root, phase, case=None):
    root = Path(root)
    if phase == "prepare":
        write(
            root / "environment.json",
            {
                "python": platform.python_version(),
                "packages": {
                    d.metadata["Name"]: d.version for d in importlib.metadata.distributions()
                },
            },
        )
        inventory = {
            "docling": docling_prepare,
            "marker": marker_prepare,
            "mineru": pinned_prepare,
            "ppstructure": pinned_prepare,
            "paddlevl": pinned_prepare,
        }[CONFIG["candidate"]](root)
        write(root / "model-inventory.json", inventory)
        return
    import socket

    # Public acquisition is finished. No inference service or model downloads allowed.
    original = socket.socket.connect

    def connect(sock, address):
        if not isinstance(address, tuple) or address[0] not in {"127.0.0.1", "::1", "localhost"}:
            raise RuntimeError("external_inference_network_denied")
        return original(sock, address)

    socket.socket.connect = connect
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
    expected = json.loads((root / "environment.json").read_text())["packages"]
    actual = {d.metadata["Name"]: d.version for d in importlib.metadata.distributions()}
    if expected != actual:
        raise RuntimeError("environment_pin_changed")
    for record in json.loads((root / "model-inventory.json").read_text()):
        if "directory" in record:
            for name, expected_hash in record["files"].items():
                if sha(Path(record["directory"]) / name) != expected_hash:
                    raise RuntimeError("staged_model_changed")
    destination = root / "results" / case
    destination.mkdir(parents=True, exist_ok=True)
    result = {
        "docling": docling_extract,
        "marker": marker_extract,
        "mineru": mineru_extract,
        "ppstructure": paddle_extract,
        "paddlevl": paddle_extract,
    }[CONFIG["candidate"]](root, root / "inputs" / (case + ".pdf"), destination)
    write(destination / "result.json", result)


def bounded(command, logfile, seconds, *, ram_limit=24 * 1024**3):
    import psutil

    start, peak, samples = time.monotonic(), 0, 0
    reason = None
    observed = {}
    gpu_peak, gpu_samples = None, 0
    with Path(logfile).open("wb") as log:
        p = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        while p.poll() is None:
            try:
                parent = psutil.Process(p.pid)
                for owned in [parent, *parent.children(recursive=True)]:
                    observed[owned.pid] = owned.create_time()
                rss = sum(
                    c.memory_info().rss
                    for c in [parent, *parent.children(recursive=True)]
                    if c.is_running()
                )
                peak = max(peak, rss)
                samples += 1
            except psutil.Error:
                pass
            if samples % 5 == 0 and CONFIG.get("device") == "cuda:0":
                try:
                    value = subprocess.check_output(
                        [
                            "nvidia-smi",
                            "--id=0",
                            "--query-gpu=memory.used",
                            "--format=csv,noheader,nounits",
                        ],
                        timeout=3,
                        text=True,
                    )
                    gpu_peak = max(gpu_peak or 0, int(value.strip()) * 1024**2)
                    gpu_samples += 1
                except (OSError, ValueError, subprocess.SubprocessError):
                    pass
            if peak > ram_limit:
                reason = "memory_limit"
            elif time.monotonic() - start > seconds:
                reason = "timeout"
            elif samples % 5 == 0:
                output_bytes = sum(
                    f.stat().st_size for f in Path(logfile).parent.rglob("*") if f.is_file()
                )
                if output_bytes > 256 * 1024**2:
                    reason = "output_limit"
            if reason:
                os.killpg(p.pid, signal.SIGKILL)
                break
            time.sleep(0.2)
        code = p.wait()
        # Clean only this owned process group, including auxiliary servers.
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        for pid, created in observed.items():
            try:
                owned = psutil.Process(pid)
                if owned.create_time() == created and owned.is_running():
                    owned.kill()
            except psutil.Error:
                pass
    return {
        "status": reason or ("completed" if code == 0 else "failed"),
        "exit_code": code,
        "wall_seconds": time.monotonic() - start,
        "peak_tree_rss_bytes": peak,
        "rss_sample_count": samples,
        "rss_sample_interval_seconds": 0.2,
        "gpu_device_0_used_peak_bytes": gpu_peak,
        "gpu_samples": gpu_samples,
        "gpu_scope": "Device total including baseline; approximately 1 second samples.",
    }


def main():
    import psutil

    root = Path("/kaggle/working/extraction")
    root.mkdir()
    started = datetime.now(UTC).isoformat()
    report = {
        "run_id": CONFIG["run_id"],
        "source_sha256": sha(__file__),
        "configuration": CONFIG,
        "started_utc": started,
        "ram": dict(psutil.virtual_memory()._asdict()),
        "cpu_count": os.cpu_count(),
        "quality": "NOT_EVALUATED",
        "rows": [],
    }
    try:
        report["gpu_inventory_csv"] = (
            subprocess.check_output(
                [
                    "nvidia-smi",
                    "--query-gpu=index,name,driver_version,memory.total,memory.free",
                    "--format=csv,noheader,nounits",
                ],
                text=True,
                timeout=10,
            )
            .strip()
            .splitlines()
        )
        report["gpu_inventory_memory_unit"] = "MiB"
    except (OSError, subprocess.SubprocessError):
        report["gpu_inventory_csv"] = None
    os.environ.update(
        OMP_NUM_THREADS="2",
        MKL_NUM_THREADS="2",
        OPENBLAS_NUM_THREADS="2",
        TOKENIZERS_PARALLELISM="false",
        HF_HUB_DISABLE_TELEMETRY="1",
        DO_NOT_TRACK="1",
        CUDA_VISIBLE_DEVICES="0" if CONFIG.get("device") == "cuda:0" else "",
        HF_HOME="/tmp/extraction-hf",
        PIP_CACHE_DIR="/tmp/extraction-pip",
    )
    try:
        inputs = root / "inputs"
        inputs.mkdir()
        for case, lines in CASES.items():
            (inputs / (case + ".pdf")).write_bytes(synthetic_pdf(lines))
        write(root / "inputs.json", {p.name: sha(p) for p in inputs.iterdir()})
        env = Path("/tmp/extraction-env")
        # Kaggle's Debian Python omits ensurepip. Existing pip targets only this venv.
        subprocess.run(
            [sys.executable, "-m", "venv", "--without-pip", str(env)], check=True, timeout=60
        )
        python = str(env / "bin/python")
        report["setup"] = bounded(
            [
                sys.executable,
                "-m",
                "pip",
                "--python",
                python,
                "install",
                "--disable-pip-version-check",
                *CONFIG["packages"],
            ],
            root / "setup.log",
            1200,
        )
        if report["setup"]["status"] != "completed":
            raise RuntimeError("isolated_package_setup_failed")
        report["prepare"] = bounded(
            [python, __file__, "--child", str(root), "prepare"], root / "prepare.log", 900
        )
        if report["prepare"]["status"] != "completed":
            raise RuntimeError("model_preparation_failed")
        for case in CASES:
            receipt = bounded(
                [python, __file__, "--child", str(root), "extract", case],
                root / (case + ".log"),
                600,
            )
            report["rows"].append({"case": case, **receipt})
        report["status"] = (
            "completed" if all(r["status"] == "completed" for r in report["rows"]) else "failed"
        )
    except Exception as exc:
        report["status"] = "blocked"
        report["error"] = f"{type(exc).__name__}: {exc}"
        write(root / "exception.json", {"traceback": traceback.format_exc()})
    # Keep every planned case in the population, including setup failures.
    for case in CASES:
        if not any(r["case"] == case for r in report["rows"]):
            report["rows"].append(
                {"case": case, "status": "not_started", "reason": report.get("error")}
            )
    report["finished_utc"] = datetime.now(UTC).isoformat()
    write(root / "report.json", report)
    # Weights are ephemeral /tmp in later adapters; exclude large model assets from export.
    files = {
        p.relative_to(root).as_posix(): sha(p)
        for p in root.rglob("*")
        if p.is_file() and "models" not in p.relative_to(root).parts
    }
    write(root / "checksums.json", files)
    print(json.dumps(report), flush=True)
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--child":
        child(*sys.argv[2:])
    else:
        raise SystemExit(main())
