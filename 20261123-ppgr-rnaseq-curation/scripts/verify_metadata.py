#!/usr/bin/env python3
"""审核一份 PPGR 物种的 expression-metadata.json（AGENT.md §5）。

用法：python3 verify_metadata.py <slug> [--dir DIR]
  <slug>：物种 slug（如 <species_slug>）
  --dir：物种目录的父目录（默认当前目录）；目录内应有 expression-metadata.json，
         有基线源 TSV 时放在 source/<slug>.tsv（可选，但有则必校验 sha256 与四元组）

检查项：
  1. JSON 可解析；顶层四键齐全（schema_version / source_sha256 / source_label / rows）
  2. 每行恰好 11 键；run_accession 无重复；四元组 ID 非空
  3. confidence ∈ {H, M, ""}；default_used 形如 k=v（; 拼接），treatment 在 genotype 之前
  4. 有源 TSV 时：source_sha256 == sha256(TSV)；行数 >= TSV 行数；
     TSV 内的四元组必须全在 JSON 内（缺失即 FAIL）；JSON 多出的行列为“补充行”并计数
退出码：0 通过；1 失败（任一 FAIL）；2 用法错误。
"""
import hashlib
import json
import sys
from pathlib import Path

KEYS = ["study_accession", "experiment_accession", "run_accession", "sample_accession",
        "tissue", "treatment", "genotype", "growth_time", "default_used",
        "confidence", "assay"]
TOP_KEYS = {"schema_version", "source_sha256", "source_label", "rows"}


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def check_default_used(v: str, run: str, problems: list) -> None:
    if not v:
        return
    parts = v.split(";")
    seen = []
    for part in parts:
        if "=" not in part:
            problems.append(f"FAIL {run}: default_used 格式错：{v!r}")
            return
        k, _ = part.split("=", 1)
        if k not in ("treatment", "genotype", "tissue"):
            problems.append(f"FAIL {run}: default_used 未知键 {k!r}（{v!r}）")
        seen.append(k)
    if "treatment" in seen and "genotype" in seen and seen.index("treatment") > seen.index("genotype"):
        problems.append(f"FAIL {run}: default_used 顺序错，treatment 须在 genotype 之前（{v!r}）")


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    slug = sys.argv[1]
    parent = Path(sys.argv[sys.argv.index("--dir") + 1]) if "--dir" in sys.argv else Path(".")
    sp_dir = parent / slug
    problems: list[str] = []
    notes: list[str] = []

    jf = sp_dir / "expression-metadata.json"
    if not jf.exists():
        print(f"FAIL: 缺 {jf}")
        return 1
    try:
        d = json.loads(jf.read_text())
    except json.JSONDecodeError as e:
        print(f"FAIL: JSON 解析失败：{e}")
        return 1
    if set(d.keys()) != TOP_KEYS:
        problems.append(f"FAIL: 顶层键错误：{sorted(d.keys())}（应为 {sorted(TOP_KEYS)}）")
    if d.get("schema_version") != 1:
        problems.append(f"FAIL: schema_version={d.get('schema_version')}（应为 1）")
    rows = d.get("rows", [])
    if not isinstance(rows, list):
        problems.append("FAIL: rows 不是数组")
        rows = []
    seen_runs: set[str] = set()
    for i, r in enumerate(rows):
        tag = r.get("run_accession", f"行#{i}")
        if sorted(r.keys()) != sorted(KEYS):
            problems.append(f"FAIL {tag}: 键错误：{sorted(r.keys())}")
        if r.get("run_accession") in seen_runs:
            problems.append(f"FAIL {tag}: run_accession 重复")
        seen_runs.add(r.get("run_accession", ""))
        for k in ("study_accession", "experiment_accession", "run_accession", "sample_accession"):
            if not r.get(k):
                problems.append(f"FAIL {tag}: {k} 为空")
        if r.get("confidence") not in ("H", "M", ""):
            problems.append(f"FAIL {tag}: confidence={r.get('confidence')!r}（只允许 H/M/空）")
        if r.get("assay") != "unreviewed":
            problems.append(f"FAIL {tag}: assay={r.get('assay')!r}（应为 unreviewed）")
        check_default_used(r.get("default_used", ""), tag, problems)

    tsv = sp_dir / "source" / f"{slug}.tsv"
    if tsv.exists():
        if d.get("source_sha256") != sha256_file(tsv):
            problems.append("FAIL: source_sha256 与源 TSV 的 sha256 不一致")
        lines = tsv.read_text().splitlines()
        header = lines[0].split("\t")
        idx = {name: header.index(name) for name in
               ("study_accession", "experiment_accession", "run_accession", "sample_accession")
               if name in header}
        tsv_tuples = set()
        for line in lines[1:]:
            if not line.strip():
                continue
            cols = line.split("\t")
            tsv_tuples.add(tuple(cols[idx[k]] for k in
                                 ("study_accession", "experiment_accession", "run_accession", "sample_accession")))
        json_tuples = {(r["study_accession"], r["experiment_accession"], r["run_accession"], r["sample_accession"])
                       for r in rows}
        missing = tsv_tuples - json_tuples
        extra = json_tuples - tsv_tuples
        if missing:
            problems.append(f"FAIL: {len(missing)} 个源 TSV 四元组不在 JSON 内，如 {sorted(missing)[:3]}")
        notes.append(f"源 TSV {len(tsv_tuples)} 行；JSON {len(rows)} 行；补充行 {len(extra)}（NCBI-only/GSA-only）")
        if len(rows) < len(tsv_tuples):
            problems.append(f"FAIL: JSON 行数 {len(rows)} < 源 TSV 行数 {len(tsv_tuples)}")
    else:
        notes.append("无源 TSV（source/<slug>.tsv），跳过 sha256/四元组校验")

    print(f"{slug}: {len(rows)} 行，{len(seen_runs)} 个唯一 run")
    for n in notes:
        print("  " + n)
    if problems:
        for p in problems:
            print("  " + p)
        print(f"结果：FAIL（{len(problems)} 项）")
        return 1
    print("结果：PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
