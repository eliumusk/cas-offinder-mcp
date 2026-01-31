import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any
import os

from fastmcp import FastMCP

mcp = FastMCP("cas-offinder-mcp")


DEFAULT_GENOME = (
    "/home/hpj/fenyiliu/cas-offinder/ncbi_dataset/data/GCF_000001405.40/"
    "GCF_000001405.40_GRCh38.p14_genomic.fna"
)


def _find_cas_offinder_bin() -> str:
    here = Path(__file__).resolve().parent
    cand = here / "cas-offinder"
    if cand.exists():
        return str(cand)
    return "cas-offinder"


def _run_cas_offinder(
    cas_bin: str,
    genome_path: str,
    pattern: str,
    targets: list[dict[str, Any]],
    device: str,
    timeout_sec: int,
    max_hits: int,
) -> list[dict[str, Any]]:
    with tempfile.TemporaryDirectory(prefix="cas_offinder_") as td:
        td_path = Path(td)
        input_path = td_path / "input.txt"

        lines: list[str] = [genome_path, pattern]
        for t in targets:
            seq = str(t["sequence"]).strip()
            mm = int(t.get("max_mismatch", 0))
            lines.append(f"{seq} {mm}")

        input_path.write_text("\n".join(lines) + "\n")

        cmd = [cas_bin, str(input_path), device, "-"]

        env = os.environ.copy()
        env.setdefault("OCL_ICD_VENDORS", "/etc/OpenCL/vendors")
        if Path("/usr/lib/x86_64-linux-gnu/libnvidia-opencl.so.1").exists():
            env["LD_LIBRARY_PATH"] = "/usr/lib/x86_64-linux-gnu" + (
                f":{env['LD_LIBRARY_PATH']}" if env.get("LD_LIBRARY_PATH") else ""
            )

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            check=False,
            env=env,
        )

        if proc.returncode != 0:
            out_tail = proc.stdout[-2000:]
            err_tail = proc.stderr[-2000:]
            raise RuntimeError(
                "cas-offinder failed\n"
                f"returncode={proc.returncode}\n"
                f"stdout_tail:\n{out_tail}\n"
                f"stderr_tail:\n{err_tail}\n"
            )

        results: list[dict[str, Any]] = []
        for line in proc.stdout.splitlines():
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) != 6:
                continue
            query, chrom, pos_s, aligned, strand, mm_s = parts
            if strand not in {"+", "-"}:
                continue
            try:
                pos = int(pos_s)
                mm = int(mm_s)
            except ValueError:
                continue

            results.append(
                {
                    "query": query,
                    "chrom": chrom,
                    "pos": pos,
                    "strand": strand,
                    "mismatches": mm,
                    "alignment_view": aligned,
                }
            )
            if max_hits > 0 and len(results) >= max_hits:
                break

        return results


@mcp.tool()
def cas_offinder_search(
    pattern: str,
    targets: list[dict[str, Any]],
    timeout_sec: int = 120,
    max_hits: int = 2000,
) -> dict[str, Any]:
    """
    Run Cas-OFFinder against the pinned human reference genome.

    Expected input (JSON):
      {
        "pattern": "NNNNNNNNNNNNNNNNNNNNNNN",
        "targets": [{"sequence": "ATCG...AGC", "max_mismatch": 0}],
        "device": "G",
        "timeout_sec": 120,
        "max_hits": 2000
      }
    """
    genome_path = DEFAULT_GENOME
    cas_bin = _find_cas_offinder_bin()

    if not isinstance(pattern, str):
        raise ValueError(
            "pattern must be a string. Example: "
            '{"pattern":"NNNN...","targets":[{"sequence":"ATCG...","max_mismatch":0}]}'
        )
    if not isinstance(targets, list):
        raise ValueError(
            "targets must be a list of objects. Example: "
            '"targets":[{"sequence":"ATCG...","max_mismatch":0}]'
        )

    pattern_clean = re.sub(r"\s+", "", pattern).upper()
    if not pattern_clean:
        raise ValueError("pattern is empty")

    cleaned_targets: list[dict[str, Any]] = []
    for idx, t in enumerate(targets):
        if not isinstance(t, dict):
            raise ValueError(
                f"targets[{idx}] must be an object like "
                '{"sequence":"ATCG...","max_mismatch":0}'
            )
        if "sequence" not in t:
            raise ValueError(f"targets[{idx}] missing required field 'sequence'")
        seq = re.sub(r"\s+", "", str(t["sequence"])).upper()
        if not seq:
            raise ValueError(f"targets[{idx}] has empty sequence")
        try:
            mm = int(t.get("max_mismatch", 0))
        except (TypeError, ValueError):
            raise ValueError(
                f"targets[{idx}].max_mismatch must be an integer, got {t.get('max_mismatch')!r}"
            )
        cleaned_targets.append({"sequence": seq, "max_mismatch": mm})

    if not cleaned_targets:
        raise ValueError(
            "targets must contain at least one sequence. Example: "
            '"targets":[{"sequence":"ATCG...","max_mismatch":0}]'
        )

    device = "G"

    hits = _run_cas_offinder(
        cas_bin=cas_bin,
        genome_path=genome_path,
        pattern=pattern_clean,
        targets=cleaned_targets,
        device=device,
        timeout_sec=int(timeout_sec),
        max_hits=int(max_hits),
    )

    return {
        "cas_offinder_bin": cas_bin,
        "device": device,
        "genome_fasta": genome_path,
        "pattern": pattern_clean,
        "target_count": len(cleaned_targets),
        "hit_count": len(hits),
        "hits": hits,
    }


if __name__ == "__main__":
    mcp.run()
