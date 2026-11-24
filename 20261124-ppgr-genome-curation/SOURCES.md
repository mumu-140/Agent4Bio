# 官方规范、数据库与来源检索

## 官方技术依据
- AGENTS.md: https://agents.md/ （工作区指令开放格式）
- Claude Code custom subagents: https://code.claude.com/docs/en/sub-agents （.claude/agents/ YAML frontmatter + prompt）
- Codex subagents: https://developers.openai.com/codex/subagents （.codex/agents/ TOML，name/description/developer_instructions）
- Codex project instructions: https://developers.openai.com/codex/guides/agents-md
- NCBI Datasets genome download: https://www.ncbi.nlm.nih.gov/datasets/docs/v2/reference-docs/command-line/datasets/download/genome/
- NCBI genome version/status: https://www.ncbi.nlm.nih.gov/datasets/docs/v2/data-processing/policies-annotation/genome-processing/version-status/
- NCBI genomes FTP: https://www.ncbi.nlm.nih.gov/datasets/docs/v2/data-processing/policies-annotation/genomeftp/
- NCBI genome package: https://www.ncbi.nlm.nih.gov/datasets/docs/v2/reference-docs/data-packages/genome/
- NCBI GFF3: https://www.ncbi.nlm.nih.gov/datasets/docs/v2/reference-docs/file-formats/annotation-files/about-ncbi-gff3/
- Sequence Ontology GFF3 specification: https://github.com/The-Sequence-Ontology/Specifications/blob/master/gff3.md
- NGDC GWH public API: https://ngdc.cncb.ac.cn/gwh/api_documents
- Figshare API v2: https://docs.figshare.com/

## 检索渠道（具体记录以实时官方页面为准）
| 来源 | 怎么用 |
|---|---|
| NCBI Taxonomy / POWO / Flora of China | 规范物种名、异名、分类等级，taxid 作为检索入口而非凭空认定。 |
| NCBI Assembly/Datasets / ENA / DDBJ | INSDC accession.version、样本、组装/注释 release、文件和 assembly report；GCA 与 GCF 分别版本化。 |
| NGDC/CNCB GWH | 查询 https://ngdc.cncb.ac.cn/gwh/api/public/assembly/<accession>，核对 organism, assemblyName, DNA/GFF/CDS/Protein 路径、版本和实际下载文件。 |
| Figshare | https://api.figshare.com/v2/articles/<article_id>，核实固定版及 files 中 file ID、downloadUrl、size、checksum；不要猜 CDN 链接。 |
| Zenodo / Dryad | https://zenodo.org/ 、https://datadryad.org/；按 DOI/record version 到文件清单，不用泛名 content/download 当文件名。 |
| Phytozome / TreeGenes / PlantGARDEN / WoodyPlant / CoGe / species databases | 按作者论文、下载页和版本表找原生配对；按当前目标检索物种或分类群专库。CoGe genome ID、版本和许可须核对。 |
| 原作者论文、supplement、机构 FTP / 数据可用性与更正 | 物种名/异名 + genome assembly + chromosome + annotation + GFF3，沿 DOI/BioProject/数据 DOI、作者/实验室及补充表双向核实；明确论文只有数据声明还是文件可用。 |

检索通道不是权威等级的机械顺序：目标版本和可追溯配套优先；原发布同版来源及官方证据比第三方整理包更重要。已授权网络路线和浏览器按当下环境选择；不固化代理 IP、令牌或访问凭据。

## 历史经验的可选溯源
历史案例原始材料保存在原项目的 README、索引、管理目录、来源清单和独立 QC 报告中，不复制进本 Agent。仅在用户明确要求复查历史案例或使用该项目时，才从对应项目的实际资料检索。此前经验的外部存档入口在工作区外（只读可选参考；非默认工作区、非运行依赖）。新任务无须访问此目录。历史程序仅为证据与候选代码，不直接执行。
