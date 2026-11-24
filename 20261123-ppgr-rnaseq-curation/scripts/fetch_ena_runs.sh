#!/usr/bin/env bash
# 从 ENA portal API 拉取一个 taxid 的 RNA-Seq run 清单（AGENT.md §3 检索）。
# 用法：bash fetch_ena_runs.sh <taxid> <slug> [outdir]
#   taxid：NCBI taxid（如 91225）
#   slug：物种 slug（如 <species_slug>）
#   outdir：输出目录（默认 ./ena）
# 产物：<outdir>/<slug>.tsv（18 列；注意 ENA 返回列顺序与请求不一致，解析必须表头驱动）。
# 退出码：curl 失败即非零；空结果（只有表头）也会写盘，由调用方判断是真 0 还是假零。
set -euo pipefail

TAXID="${1:?用法：fetch_ena_runs.sh <taxid> <slug> [outdir]}"
SLUG="${2:?用法：fetch_ena_runs.sh <taxid> <slug> [outdir]}"
OUT="${3:-ena}"
mkdir -p "$OUT"

FIELDS="run_accession,study_accession,experiment_accession,sample_accession,sample_title,scientific_name,tax_id,library_strategy,library_layout,library_selection,library_source,instrument_platform,instrument_model,center_name,first_public,fastq_bytes,read_count,base_count"

curl -sS --max-time 300 -G "https://www.ebi.ac.uk/ena/portal/api/search" \
  --data-urlencode "result=read_run" \
  --data-urlencode "query=tax_eq(${TAXID}) AND library_strategy=\"RNA-Seq\"" \
  --data-urlencode "fields=${FIELDS}" \
  --data-urlencode "format=tsv" \
  --data-urlencode "limit=0" \
  -o "${OUT}/${SLUG}.tsv"

ROWS=$(( $(wc -l < "${OUT}/${SLUG}.tsv") - 1 ))
echo "${SLUG} taxid=${TAXID}: ${ROWS} runs -> ${OUT}/${SLUG}.tsv"
sha256sum "${OUT}/${SLUG}.tsv"
