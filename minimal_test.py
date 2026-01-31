import subprocess
import tempfile
from pathlib import Path
import os

GENOME_FASTA = (
    "/home/hpj/fenyiliu/cas-offinder/ncbi_dataset/data/GCF_000001405.40/"
    "GCF_000001405.40_GRCh38.p14_genomic.fna"
)

# Minimal smoke test; scanning the full human genome can take time.
# Uses the local cas-offinder binary directly to avoid MCP tool wrappers.
pattern = "NNNNNNNNNNNNNNNNNNNNNNN"
target = "TTTACGTTTTGAGTCCGAGCAGA"
max_mismatch = 0
device = os.environ.get("CAS_OFFINDER_DEVICE", "C")

cas_bin = Path(__file__).resolve().parent / "cas-offinder"
if not cas_bin.exists():
    cas_bin = "cas-offinder"

with tempfile.TemporaryDirectory(prefix="cas_offinder_test_") as td:
    input_path = Path(td) / "input.txt"
    input_path.write_text(
        f"{GENOME_FASTA}\n{pattern}\n{target} {max_mismatch}\n"
    )

    env = os.environ.copy()
    conda_prefix = env.get("CONDA_PREFIX")
    vendors = []
    if conda_prefix:
        vendors.append(f"{conda_prefix}/etc/OpenCL/vendors")
    if Path("/etc/OpenCL/vendors/nvidia.icd").exists():
        vendors.append("/etc/OpenCL/vendors")
    if vendors:
        env["OCL_ICD_VENDORS"] = ":".join(vendors)

    lib_paths = []
    if conda_prefix:
        lib_paths.append(f"{conda_prefix}/lib")
    if Path("/usr/lib/x86_64-linux-gnu/libnvidia-opencl.so.1").exists():
        lib_paths.append("/usr/lib/x86_64-linux-gnu")
    if lib_paths:
        env["LD_LIBRARY_PATH"] = ":".join(lib_paths + ([env["LD_LIBRARY_PATH"]] if env.get("LD_LIBRARY_PATH") else []))

    # CPU fallback for POCL if GPU isn't used.
    env.setdefault("POCL_DEVICES", "basic")

    proc = subprocess.run(
        [str(cas_bin), str(input_path), device, "-"],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
        env=env,
    )

    if proc.returncode != 0:
        raise SystemExit(
            "cas-offinder failed\n"
            f"returncode={proc.returncode}\n"
            f"stdout_tail:\n{proc.stdout[-2000:]}\n"
            f"stderr_tail:\n{proc.stderr[-2000:]}\n"
        )

    lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    print("hit_count=", len(lines))
    print("hits_preview=", lines[:3])
