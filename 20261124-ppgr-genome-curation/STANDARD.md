# 策展标准与验收合同

## 1. 工作单位与证据
主键为目标物种记录 + requested assembly/version + 材料/单倍型（若适用）；同一 taxonomic alias 指向同一实体时单独报告，不增加独立基因组数。原始目标版本不能被 alternate candidate 偷换。用户未指定版本时优先推荐来源可追溯且同版完整的参考，报告候选比较（物种、材料、assembly level、发布日期、注释来源与版本、BUSCO 若有原始来源），不可单凭 T2T/最新/大小排名。核、质体、线粒体、污染/未定位序列分别报告。保留目标 CSV 的原始字段和值；字段拼写依实际表头解析。

### 发现与下载
保存 paper DOI/PMID（仅真实核实）、data availability 原文位置、数据库 record URL/ID、版本与发布日期、文件清单/URL/size/checksum、获取 UTC、状态码、来源与许可。记录 searched query/异名、分页、找到何种数据（assembly、raw reads、transcriptome、organelle、annotation），没有证据填 null；不能将下载文件名推测为官方记录。使用 NCBI Datasets v2 genome taxon/accession report 和 FTP assembly_report + md5checksums；GWH Assembly API 实际字段及版本；Figshare article/version 和 file ID，Zenodo record/version（concept DOI 不是固定版）。专库下载表及作者补充文件交叉核对。若登录受限，提供合法访问链接或请求作者。
下载前核实可用磁盘（压缩、解压、缓存、候选、传输峰值），使用任务级日志、每目标文件唯一目的路径、有限并发、Range/ETag 或明确内容身份；HTTP 429 尊重 Retry-After。临时文件 .part/.aria2 不晋升。续传来源变化先核验身份和 Range 响应，否则另存候选。下载成功后独立复算官方 MD5/SHA（若提供）及本地 SHA-256、全量 gzip CRC/ZIP CRC/TAR 可读性和格式魔数；没有官方校验值须如实记录，自己的 SHA 不等同官方验证。压缩包逐成员分类，防止绝对路径、..、软链接/硬链接与覆盖；禁止执行成员。跨机传输验证源/目标 SHA-256 一致；中转只清理自己明确获准清理的临时文件。

## 2. 技术验收（必须检查全部相关记录）
- FASTA：真正 genomic DNA（不是 CDS、pep、RNA、HTML）、完整解析，首个空白分隔 token 为 seqid，唯一且非空，非空序列，IUPAC DNA，记录每条长度、总 bp、序列数、N/掩蔽说明；与发布组装统计、AGP/sequence report 交叉核对。官方来源兼容对无需跨库全基因组逐碱基重比，但应确认同发行包。跨库配对比较逐序列 hash（大写序列消除 soft-mask 差异，同时保留原始文件 SHA，显式记录 N/掩蔽差异）、方向、一对一映射及覆盖范围；长度/前缀/BUSCO 不是同一性证明。
- GFF3：解析 9 个 tab 列，合法 SO 类型、1-based 闭区间、strand 与 CDS phase 0/1/2，属性 URL 转义、ID/Parent、多 Parent、父子层级、同一特征分段重复 ID（合法的 discontinuous feature 非一律重复错误）、环/跨 seqid/边界异常；处理 ##sequence-region 和 ##FASTA，圆形跨原点按规范单独审查，不静默裁切。GTF/GFF2 另解析；不能换扩展名伪装 GFF3。GFF seqid 集合应为 FASTA 子集；FASTA 有未注释 scaffold 并不自动失败。记录基因、mRNA/transcript、CDS、exon、organelle 分别计数；无 gene 行时 gene_count=null，不拿 mRNA 数填。不能用 >1000 基因或任意文件大小代替格式验证。可用 seqkit、GenomeTools/gffread、AGAT 等经版本确认的工具辅助；脚本仅做结构 QC，需独立 reviewer 检查来源、复杂模型和坐标语义。
- CDS/PEP：有源 CDS/PEP 时按 transcript 层逐段核对，负链以转录方向逆序并反向互补；根据 CDS phase、遗传密码、partial、stop、transl_except 等规范处理，不能对每段盲切 phase 或把内部 stop 全认成错配。记录核/细胞器遗传密码差异和作者源异常。派生 CDS/PEP 标明工具、版本、规则、哈希和来源；不能以再注释替代原作者 GFF。
- 映射：只有一对一官方 alias 或独立核酸等价证据才改 seqid；同步 ##sequence-region 和相关引用；线性完整反向互补长度 L：start'=L-end+1，end'=L-start+1，strand 翻转；保持生物学转录方向、phase/Parent 语义并验证转换前后 CDS。存在插缺/局部重排或 N 差异时先定位差异、验证每个受影响特征和序列；一般 liftover 另列派生坐标，不能标原版 exact。避免全局字符串替换 ID、前缀模糊匹配、长度猜测、截断超界、无依据重算 phase。
- 过滤：仅当原始来源矛盾有明确证据且用户接受覆盖损失；保存排除的序列 ID、每条原始 feature/理由/父子闭包，按 gene、transcript、CDS、总特征分别报告分子/分母，独立确认全部保留记录。不可用固定百分比自动批准。全套源文件仍保留。
- 独立 QC：另一 reviewer 使用独立读取方式检查实际输出哈希、全量 seqid/bounds、ID/Parent 和适用的 CDS 序列同一性，不复用未绑定源 SHA 的缓存；正式报告列明未做的检查。脚本退出 0、gzip 正常、源论文声称有注释均不足以晋升。

## 3. 状态（建议的通用状态；候选与正式索引分离）
| 状态 | 语义 |
|---|---|
| READY_EXACT_SEQIDS | 经来源、同版及结构 QC 验收；原始坐标系兼容。 |
| READY_COORDINATES_NORMALIZED | 有充分坐标等价证据的派生 GFF，原始路径与映射齐全。 |
| READY_ANNOTATION_FILTERED | 经授权的有损兼容 GFF；排除计数与用途限制齐全。 |
| REVIEW_COORDINATES | 有文件但 seqid/坐标/身份或基因模型存在待解问题，不给可消费 GFF 路径。 |
| GENOME_ONLY_NO_GFF | 已有目标基因组，无可验收的同版 GFF。 |
| MISSING_GENOME_AND_GFF | 目标配对尚未取得；核对实际文件，不能由旧状态断言两个文件物理缺失。 |
| READY_ALTERNATE_ASSEMBLY / READY_EXTRA_ASSEMBLY | 备选/额外组装，单列；不计目标 READY。 |
| CANDIDATE_SOURCE / DOWNLOAD_BLOCKED / PARTIAL / PREDICTED_GFF_NOT_SOURCE / USER_HOLD | 工作队列说明，非主索引 READY；HOLD 独立记录。 |

目标项目已定义状态 schema 时保留其契约，显式映射本标准的状态语义；不能擅自迁移字段或状态值。现有索引 state 是历史批准的使用合同；新验收需达到本标准。不得重写过去状态来夸大质量，也不得因未做当前新增检查就无授权改写旧索引。

## 4. 每目标交付
保存在现有管理目录对应任务区（沿用项目规范）：一行候选/修复表 + 证据 JSON/TSV 或等价结构化记录；仅有必要时保留独立日志，正式数据仅在许可后按目标项目既有目录契约入库；没有既有约定时可建议 <Genus_species>/<assembly_version>/。推荐字段：
- identity：query_name, accepted_name, taxid, synonyms, requested_version, candidate_version, assembly_accession, sample, haplotype, annotation_release, molecule_scope
- source：publication_doi, repository, record_url, dataset_version, retrieved_utc, file_role, file_id, download_url, expected_size, expected_checksum, license, source_match_evidence
- artifact：local_path, bytes, sha256, original_path, derived_path, transfer_sha256, archive_integrity
- QC：fasta_seqids, total_bp, gff_seqids, gene_count, transcript_count, feature_counts, unmatched_seqids, out_of_bounds, malformed_rows, parent_errors, sequence_identity_scope, exclusions, qc_report, independent_review, limitations
- decision：state, target_or_alternate, hold, reason, next_action, reviewer, verified_utc
未知字段 null（TSV 空白），不填 0；0 仅为实际计算的零。来源表、原始与派生哈希分别保留。人工补下载清单含物种/版本、file role、页面与文件 URL、预期大小/校验、目标路径、失败原因。

## 5. 批量与晋升
批次按目标身份及阻塞类型分组：已有可配对文件→同版源明确→仅有一类文件→来源未确定；用户 HOLD 不调度。先试点（至少涵盖一种原始同版、一种派生/冲突、一种受阻），复审后才扩展；每 worker 独占明确物种/版本和候选路径，锁避免同目标并发，禁止共享写索引。限制并发/磁盘/网络，按已授权的范围持续处理，不因完成首个物种结束。独立 reviewer 与下载/修复 worker 分离；owner 对新索引按 schema、状态总数、唯一主键、实际文件路径、备选/alias、保留其他条目复算差异，发布前确认权限与旧索引可恢复；同文件系统临时文件校验后原子替换，记录变更；若数据库/共享存储写入超出授权则仅交接。禁止直接运行旧的硬编码索引重建脚本（可能丢失后续补丁）。
