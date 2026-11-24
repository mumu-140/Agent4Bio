# 批量策展方案：4 并行 agent（dp4.1flash，经 cc）

> 计划：`20261123-ppgr-rnaseq-curation`；门禁 G2 **已授权**（用户 2026-11-24）。
> 目标：批量物种的 bulk RNA-seq 元数据策展，一物种一份 `expression-metadata.json` + `EVIDENCE.md`。
> 并行 4 个 agent；每个 agent 只做自己分到的组，严格按 `AGENT.md` 办事。

## 1. 前置阅读（每个 agent 动手前按顺序读完）

1. `AGENT.md`——权威链、范围、七步工作流、交付、审核、门禁。
2. `STANDARD.md`——策展标准 v5（口径、schema、批量方法、统一规则；分类提取见 §3.14–3.17）。
3. `PITFALLS.md`——45 条实测坑（先读再动手，踩到新坑按同样格式追加）。
4. `GROUPING.md`——分组方法与自己的分组。
5. 本文件 §3 数据目录规范——**先记住谁写哪里，再动手**。

读不懂、与 AGENT.md 冲突、或遇到本文件没写的情况：停下来写进自己组的 EVIDENCE.md
并上报，不自己发明规则。

## 2. 分工（16 组 → 4 agent，按 experiment 数均衡）

| Agent | 组 |
|---|---|
| agent-a | G01、G07、G08 |
| agent-b | G02、G03、G09、G10 |
| agent-c | G04、G05、G06、G11、G12 |
| agent-d | G13、G14、G15、G16 |

- 各 agent 的 experiment 总量均衡；工作量按 experiment 数算，不按物种数算。
- 计数是 **experiment 数、未剔单细胞的上界**；策展时按 STANDARD.md §3.8 剔单细胞，行数以策展结果为准。
- 组是分工单位，不可跨 agent 拆组；组内物种按分组清单做。
- 分组按 experiment 数与物种数双维均衡：物种数过多的一组，即使 experiment 数均衡，逐物种抓属性、建缓存的开销也会倾斜——两维同时看，单组物种数异常时拆分。

## 3. 数据目录规范（多 agent 并行，谁写哪里）

```
Agent4Bio/20261123-ppgr-rnaseq-curation/      ← agent_home
  AGENT.md / STANDARD.md / PITFALLS.md / README.md / tasks.yaml / GROUPING.md / BATCH_PLAN.md
      ← 根文档，只读。任何 agent 不得修改；要改先上报，由主 agent 改。
  scripts/                                        ← 只读
      verify_metadata.py / fetch_ena_runs.sh / count_species.py
      要改脚本：先复制到自己 work/ 下改，改完上报，不直接动这里。
  data/                                           ← 只读，绝不写
      物种清单与计数（本地输入，不进仓库）
  work/agent-a/ / work/agent-b/ / work/agent-c/ / work/agent-d/
      ← 各 agent 的工作区。只写自己的目录，不读不写别人的目录。
      每物种一个子目录，结构固定：
        work/agent-x/<slug>/
          expression-metadata.json
          EVIDENCE.md
          source/<slug>.tsv          ← 基线源 TSV（ENA/NCBI 拉取原样）
          tmp/                       ← 临时文件（用完清掉，不进交付）
  output/<slug>/                                  ← 验收通过后晋升的产物
      output/<slug>/expression-metadata.json
      output/<slug>/EVIDENCE.md
      output/<slug>/source/<slug>.tsv
      晋升规则：本物种 verify PASS + 抽查通过后，由验收步骤 mv（原子移动），
      agent 自己不直接写 output/。
```

**铁律：**

- 只写自己的 `work/agent-x/`；不碰别人的 `work/`、不写 `data/`、`scripts/`、根文档。
- 不在计划外新建目录；不把中间文件散放到计划外位置；`tmp/` 用完清掉。
- 共享文件（`data/`、`scripts/`、根文档）只读；需要改先上报。
- 输出文件名固定：`<slug>/expression-metadata.json`、`EVIDENCE.md`、`source/<slug>.tsv`；
  slug 规则见 AGENT.md §3（拉丁名小写下划线，杂交种用 `x` 连接）。
- 每个文件写完即算 sha256 记在 EVIDENCE.md；源 TSV 的 sha256 进 JSON 的 `source_sha256`。

## 4. 每 agent 工作流（AGENT.md §3 的执行版）

1. 从 `data/grouping_plan.json` 取自己组的物种清单，按 experiment 数从大到小做。
2. 每物种走 AGENT.md 七步：定名 → 计数 → 检索 → 策展 → 补源 → 审核 → 落盘。
3. 每做完一物种：跑 `python3 scripts/verify_metadata.py <slug> --dir work/agent-x`，
   PASS 才算完；FAIL 就地修，修不好记 EVIDENCE.md 并上报。
4. 命名陷阱（GROUPING.md 列的 13 个）与 0 计数物种：按 STANDARD.md 重查接受名、
   走 ENA/GSA/文献三源；查不到的记 0 行 + EVIDENCE.md 写明查过，不编造。
5. GSA-only 行：CRR 枚举走浏览器（STANDARD.md §3.7）；取不到 CRR 的记 CRA 级并标注
   “CRR 未枚举”，不编 CRR 号。
6. 单细胞剔除（STANDARD.md §3.8）：剔除数记 EVIDENCE.md。
7. 默认矛盾扫描与缓存落盘（STANDARD.md §3.11–3.12）：全部物种做完后、汇报前，对全部带默认值的行跑一次关键词扫描并逐 study 裁定，裁定记录进 EVIDENCE.md；样本属性缓存随 JSON 一并落盘。
8. 全部做完：按 §5 汇报。
9. 分类提取（STANDARD.md §3.14–3.17，参考实现 `pilot/`）：每物种在策展后跑分类提取——先拉三层证据（样本属性、样本库记录、实验标题），再跑提取产出拟用 JSON 与逐行 trace；拟用文件不直接覆盖现行 JSON，复核（机械校验 + 逐行抽查 + 有参考表时对照验证）通过后才晋升；抽查发现的新模式缺口先修提取器、再重跑，不要手工改拟用文件。并行提取时：规范提取器 `pilot/extract_classified.py` 只读，各 agent 各复制一份到自己 `pilot/_dispatch/agent-x/` 目录改，改动记 `EXTRACTOR_CHANGES.md`（症状→旧行为→新规则→影响物种数）；协调人合并成统一提取器后用 `pilot/_dispatch/run_final_extract.py` 全量重跑收敛；派发清单、基线核对、合并队列分别见 `pilot/_dispatch/species_agent-x.txt`、`BASELINE_20261124.md`、`MERGE_QUEUE_20261124.md`；复核扫描用 `pilot/_dispatch/postfix_scan.py`（新值与沿用旧值分开计数）；复核证据集中到 `review/classified-20261124/`。0 行物种不跑证据拉取（拟用文件照抄现行，trace 为空）。

## 5. 汇报格式（每 agent 完成时返回）

```
agent-x 完成：N 种 / 总行数 R 行
- 每物种一行：slug | 行数 | study 数 | confidence H/M/空 | 补充行（NCBI-only/GSA-only 各几行）
- NCBI−ENA diff 汇总：差异总数，逐条已定性的结论（有几条未定性，列出来）
- 命名陷阱处理：13 个陷阱中本组有几个，各自结论
- GSA：已并入几行；CRR 未枚举的 CRA 清单
- 单细胞剔除：总数，分物种
- 默认矛盾扫描：扫描行数、裁定行数、留空行数
- 分类提取：改动行数（分字段）、trace 已留/未留、逐行抽查结果（抽查行数/通过数）、有参考表时的对照验证结果
- 合并版提取器：版本与 sha256，合并队列位置
- 复核扫描：新值/沿用旧值分开计数（停用词、对照+因子、组织尾号等）
- 样本属性缓存：已留/未留
- 失败/遗留：做不下去的物种 + 原因 + 已查到的证据（不编造）
- verify 结果：N 种 PASS，FAIL 的种 + 原因
```

## 6. 停表与上报

出现以下任一情况，停下该物种、记 EVIDENCE.md、上报，不自行决定：

- ENA 与 NCBI 集合差异定性不了；接受名解析不了；GSA 数据无来源。
- 单细胞判断不确定；study/sample 元数据自相矛盾。
- 任何一步需要写生产库、部署、commit、push，或需要下载 FASTQ。
- 发现 STANDARD.md / PITFALLS.md 没覆盖的新坑：记下来追加到 PITFALLS.md（只追加自己
  work/ 外的共享 PITFALLS.md 须上报后由主 agent 合并——并行期间各 agent 把新坑写进自己组
  的汇报里，不直接改共享文件）。

## 7. 给 cc 的启动指令（粘贴用）

> 在工作节点的 `Genome-web/Agent4Bio/20261123-ppgr-rnaseq-curation/`
> 下，按 `BATCH_PLAN.md` 并行 4 个 agent：
> agent-a 做 G01、G07、G08；agent-b 做 G02、G03、G09、G10；
> agent-c 做 G04、G05、G06、G11、G12；agent-d 做 G13、G14、G15、G16。
> 每个 agent 动手前先读 AGENT.md、STANDARD.md、PITFALLS.md，产物与汇报按 BATCH_PLAN.md
> §3 目录规范与 §5 格式来；只写自己的 work/agent-x/，不碰共享只读文件。
