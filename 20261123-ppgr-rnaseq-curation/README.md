# 转录组策展计划（20261123-ppgr-rnaseq-curation）

> 计划 ID：`20261123-ppgr-rnaseq-curation`。
> 一句话：把一批植物物种的 bulk RNA-seq 元数据，策展成一物种一份 `expression-metadata.json` + `EVIDENCE.md`，
> 供 Genome-web 表达入库（ingestion-contract-20261004.md）消费。

## 入口（按顺序读）

| 文件 | 内容 |
|---|---|
| `AGENT.md` | Agent 规范：权威链、范围、七步工作流、交付、审核、门禁 |
| `STANDARD.md` | 策展标准 v5（口径、schema、批量方法、统一规则、禁止项） |
| `PITFALLS.md` | 经验与坑（45 条，试点实测，带日期与证据） |
| `tasks.yaml` | 授权状态、门禁、工作包、停表条件 |
| `GROUPING.md` | 分组方法（按 experiment 数均衡） |
| `BATCH_PLAN.md` | 4 并行 agent 批量方案（分工、数据目录规范、汇报格式） |
| `scripts/verify_metadata.py` | 审核脚本（结构/计数/sha256/四元组） |
| `scripts/fetch_ena_runs.sh` | 检索脚本（ENA portal API 拉取 run 清单） |
| `scripts/count_species.py` | 计数脚本（NCBI taxonomy 核对 + SRA experiment 计数，可断点续跑） |
| `data/` | 物种清单与计数（本地输入，只读，不进仓库） |
| `work/agent-a/` … `work/agent-d/` | 各并行 agent 的工作区（只写自己的目录） |
| `output/<slug>/` | 验收通过后晋升的产物（结构同 work） |

## 门禁

| Gate | 状态 |
|---|---|
| G1 试点 | 完成（2026-11-23） |
| G2 批量（16 组并行策展） | 完成（2026-11-24） |
| G3 入库（`data/analysis/<Genus_species>/expression/metadata/`） | 已执行（2026-11-24） |
| G4 发布 | 待授权 |

## 位置

本计划的规范位置是 `Genome-web/Agent4Bio/20261123-ppgr-rnaseq-curation/`
（2026-11-24 自 `.helloagents/plans/` 迁入，此后只认这里；旧路径已不存在）。
数据目录规范（多 agent 并行时谁写哪里）见 `BATCH_PLAN.md` §3。
