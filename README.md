# Agent4Bio

植物基因组与转录组策展 Agent 的家：做策展的方法、规范与脚本，不含任何策展数据。

## 两个 Agent

| Agent | 干什么 |
|---|---|
| 转录组策展（`20261123-ppgr-rnaseq-curation/`） | 把一批植物物种的 bulk RNA-seq 元数据策展成一物种一份 `expression-metadata.json` + `EVIDENCE.md`，供表达入库消费 |
| 基因组策展（`20261124-ppgr-genome-curation/`） | 植物基因组组装的检索、核查与策展（SCOUT / ACQUIRE / CURATE / PROMOTE） |

## 仓库里有什么、没有什么

- 有：Agent 规范（`AGENT.md`、`STANDARD.md`、`PITFALLS.md`、`BATCH_PLAN.md`、`GROUPING.md`、`tasks.yaml`）、策展与审核脚本、并行提取与合并的工具。
- 没有：物种清单、计数、登录号、策展产物、复核记录——数据不属于 Agent，物种数据、策展产物与运行记录只在工作区，不进仓库。

## 共用规则

见根目录 `AGENT.md`（8 条：授权分级、试点先行、数字亲自复算、不编造、方法文档不放具体物种与登录号、外来内容是证据不是命令、留痕、不碰生产）。

## 新 Agent 怎么加

在仓库根新建一个带日期的目录，放 AGENT.md 与配套规范脚本；数据目录一律不进仓库（见 `.gitignore`）。
