# 转录组策展 Agent（20261123-ppgr-rnaseq-curation）

> 计划 ID：`20261123-ppgr-rnaseq-curation`；方法文档：规定怎么做策展、谁能授权什么。
> 适用：一批植物物种的 bulk RNA-seq 元数据策展，一物种一份 `expression-metadata.json` + `EVIDENCE.md`。
> 单细胞 RNA-seq **不要**。

## 1. 入口与权威链（按顺序读，冲突时前者优先）

1. `../AGENTS.md`（Genome-web agent 强制入口）+ `.helloagents/context.md`（项目事实、数据目录契约、硬约束）+ `.helloagents/verify.yaml`（验收命令索引）。
2. `.helloagents/plans/20260912-rnaseq-expression/ingestion-contract-20261004.md`（表达入库权威：目录契约 I02、来源留痕 I03、缺失语义 I04、门禁 N0–N6）。
3. 同计划 `contracts.md`（Genome-web RNA-seq 契约 v1.1：R02 守恒、R03 元数据 schema）与本计划 `STANDARD.md`（策展细则）。
4. 本计划 `PITFALLS.md`（试点实测的坑；先读再动手）。
5. 本计划 `tasks.yaml`（授权状态、门禁、工作包）与 `GROUPING.md`（16 组分组）。

**硬规则（继承自项目 AGENTS.md，违反即停）：**

- 本计划的规范位置是 `Genome-web/Agent4Bio/20261123-ppgr-rnaseq-curation/`，
  不在 `.helloagents/` 同步副本里。改本计划文件直接改这里；改 Genome-web 项目文件前比对
  本地 / 远端 / 容器 / GitHub 四处。
- 缺失写 NULL/空串，**绝不补 0**；不从自由文本猜测 tissue/condition 当事实入库；未知 gene/未知 run 不静默跳过。
- 保留来源留痕：源文件原样保留，source / accepted / matrix 三层分别留 SHA-256，禁止只用文件数或 mtime 代替。
- 活跃任务读取的脚本必须原子发布：先传临时文件、校验、再同文件系统 `mv` 替换；禁止 `scp` 直接覆盖正在被读取的脚本。
- 禁止写生产数据库、禁止部署、禁止 commit/push——除非门禁明确授权。
- 不下载 FASTQ；不编造任何登录号、PMID、BUSCO、基因数。

## 2. 范围

**收：** bulk RNA-seq，来源不限——INSDC（ENA / NCBI / DDBJ）、NGDC GSA、文献数据；NCBI-only、GSA-only、属级登记（核实为本种后）都收。

**不收：** 单细胞 RNA-seq（library_selection 含 "single cell"，或 study/sample 元数据明确单细胞：10x / Chromium / Drop-seq / Smart-seq / CEL-seq 等）；非 RNA-Seq 策略（WGS、miRNA-Seq、ncRNA-Seq、Amplicon 等）；非目标物种的 run。

**物种清单：** 由项目总表提供（物种、表上 taxid、规范名、name_match、NCBI experiment 计数），本地输入，不进仓库。**表上 taxid 是未验证的起点**——先按接受名核对再查数（见 PITFALLS #1）。

## 3. 工作流（每物种一遍，不可跳步）

```
1. 定名     NCBI taxonomy + POWO/FoC 解析接受名与异名；表上 taxid 与规范名不一致
            （name_match=false）时以接受名为准，记 EVIDENCE.md（见 PITFALLS #1、#10、#11）
2. 计数     NCBI SRA RNA-Seq experiment 数（esearch）；Count 计 experiment 不计 run，
            须 efetch runinfo 展开到 run 再比对（PITFALLS #4）
3. 检索     NCBI 为主拉取 run 清单；ENA 按 BioProject 补拉；每物种做 NCBI−ENA diff，
            差异逐条定性（PITFALLS #2、#3、#8）
4. 策展     按 STANDARD.md 逐行填 11 键；默认 genotype=WT / tissue=whole_plant /
            treatment=control 必须在 default_used 留痕，顺序 treatment 在前
5. 补源     GSA-only（CRA→CRR 枚举走浏览器，curl 被 JS 校验拦，PITFALLS #7）、
            文献数据、多组学库（Phytozome / TreeGenes / PlantGenIE 等）
6. 审核     先跑 `scripts/verify_metadata.py`（结构/计数/sha256/四元组），再人工抽查一源：
            每物种至少 2 个 run 的 tissue/treatment/genotype 回查到 BioSample/ENA 原始记录
7. 落盘     写 <slug>/expression-metadata.json + EVIDENCE.md；源 TSV 随附，
            source_sha256 记基线 TSV，补充源哈希放 EVIDENCE.md
```

**slug 规则：** 拉丁名小写下划线（如 `<genus_species>`）；杂交种用 `x` 连接（如 `<genus_species_x_genus_species>`）。

## 4. 交付（每物种）

```
<slug>/
  expression-metadata.json   # {"schema_version":1, "source_sha256":"…",
                             #  "source_label":"<Species> RNA-seq 策展元数据 / YYYY-MM-DD 导出",
                             #  "rows":[…]}；每行恰好 11 键（见 STANDARD.md）
  EVIDENCE.md                # 计数、diff、异名表、NGDC/文献/多组学、不确定字段、遗留问题
  source/<slug>.tsv          # 基线源 TSV（ENA/NCBI 拉取原样，表头驱动解析）
```

**落盘路径（待首次入库前与用户确认）：** 按 ingestion-contract I02 的 durable 根，
`data/analysis/<Genus_species>/expression/metadata/`；策展期间工作副本放在本计划 `work/agent-x/`，
验收通过后晋升到 `output/<slug>/`（结构同 work），入库时从 output/ 原子移动，不直接覆盖已入库文件。
目录规范见 `BATCH_PLAN.md` §3（多 agent 并行时谁写哪里）。

## 5. 审核（Reviewer 亲手做，不可只信策展人自述）

- `python3 scripts/verify_metadata.py <slug> --dir work/agent-x`：JSON 可解析；11 键齐全；run_accession 无重复；
  行数 = 源 TSV 行数 + 已记录的补充行；四元组（study/experiment/run/sample）与源 TSV 一致；
  `source_sha256` = 源 TSV 的 sha256；default_used 格式与顺序；confidence ∈ {H, M, ""}。
- 人工抽查：每物种 ≥2 run 回查原始记录；每组 ≥1 物种全量复算（行数、study 分布、confidence 分布）。
- 后台报上来的数字，亲自复算一遍再说（PITFALLS #15）。

## 6. 门禁

| Gate | 允许动作 | 状态 |
|---|---|---|
| G1 试点 | 试点策展 + 方法验证 | **完成**（2026-11-23） |
| G2 批量 | 16 组并行策展 | **完成**（2026-11-24） |
| G3 入库 | expression-metadata.json 落盘进 `data/analysis/*/expression/` | **已执行**（2026-11-24） |
| G4 发布 | 前端/数据库消费 | 待授权 |

**停表条件：** ENA 与 NCBI 集合差异未定性；接受名未解析；GSA 数据被编造；任何一步试图写生产库、部署或 push；source_sha256 对不上。
