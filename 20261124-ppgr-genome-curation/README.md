# Agent4Genome · Plant Genome Curation

通用植物基因组检索、下载、组装版本识别、FASTA–GFF 配对、坐标修复与独立质量审核 Agent。运行目标、物种、参考版本、数据目录与授权均由当前任务提供；没有固定物种清单、历史进度或默认数据项目。

## 使用

从本目录启动支持本地 Agent 的 Claude Code 或 Codex，委派 genome-curation（Claude）或 genome_curation（Codex）。其他智能体可显式读取 AGENTS.md。此目录为项目级 Agent 定义，未安装到全局配置。

示例：
- 对用户指定物种与版本做 SCOUT，仅交付真实论文、数据库、文件及候选配对证据。
- 对指定清单按已授权范围下载与校验，暂不更新正式索引。
- 独立审核指定 FASTA/GFF 及派生数据，输出明确验收状态和限制。

## 文件与维护

AGENT.md：核心工作指令；AGENTS.md：工作区入口；STANDARD.md：科学和工程验收标准；PITFALLS.md：20 类可复用错误及对策；SOURCES.md：官方文档、数据库检索与可选历史证据入口；.claude/agents 与 .codex/agents：原生 Agent 定义。两种运行时共用主体指令，继承父会话工具和权限。

项目数据、实时统计、物种清单、访问配置与任务日志由目标工作区管理；不写入 Agent。目录名称沿用原有安装位置，名称不限定任务范围。按实际客户端验证加载和委派，静态格式检查不代表运行通过。
